<?php

namespace Espo\Modules\Itvolga\Tools\Import;

use Espo\Core\ORM\Entity as CoreEntity;
use Espo\Core\ORM\Repository\Option\SaveOption;
use Espo\Core\Utils\Id\RecordIdGenerator;
use Espo\ORM\EntityManager;
use stdClass;

/**
 * Imported files (stage 06.3, import.md «Файлы»): one operation per file — the Attachment record, its owner and its
 * bytes. Identity: the Vtiger attachment id (`vtigerId`); a file without one (the logo of the legal entity) is the
 * attachment its owner field points to. The attachment owns its relation explicitly, so it holds under the hookless
 * save of comments: a file or image field (`Document.file`, `Contact.cPhoto`, `User.avatar`, `LegalEntity.logo`) —
 * `related` + `field` on the attachment and the owner's `<field>Id`; an attachment list (`Note.attachments`,
 * `Email.attachments`) — `parent` + `field`. A replaced attachment of an owner field is left as it is.
 *
 * Bytes land in the core upload storage (`data/upload/<id>`) only after their size and sha256 were checked against
 * the source and only after the record's transaction committed (stage 06.4): an interrupted or failed write never
 * leaves a stored file without its record — at worst a committed record without its bytes, which the check pass sees
 * and the next run writes. A stored file with the source sha256 is not written again, so a re-run touches nothing.
 */
class AttachmentWriter
{
    /** Owner entity type => field => kind. */
    public const OWNERS = [
        'Document' => ['file' => 'single'],
        'Contact' => ['cPhoto' => 'single'],
        'User' => ['avatar' => 'single'],
        'LegalEntity' => ['logo' => 'single'],
        'Note' => ['attachments' => 'multiple'],
        'Email' => ['attachments' => 'multiple'],
    ];
    private const STORAGE = 'EspoUploadDir';

    /** @var ?array{Blob, string} received bytes and their storage path, placed once the record committed */
    private ?array $pending = null;

    public function __construct(
        private EntityManager $entityManager,
        private KeyResolver $keys,
        private DesiredState $desired,
        private BlobReceiver $blobs,
        private RecordIdGenerator $idGenerator,
    ) {}

    /**
     * @return array<string, mixed>
     */
    public function check(stdClass $op): array
    {
        try {
            [$owner, $field, $kind] = $this->owner($op);
        } catch (ImportError $e) {
            if ($e->reason !== 'owner_missing') {
                throw $e;
            }

            return ['status' => 'missing']; // the check pass before the owner is imported
        }

        $attachment = $this->locate($op, $owner, $field);

        if (!$attachment) {
            return ['status' => 'missing'];
        }

        if ($attachment->get('deleted')) {
            return ['status' => 'deleted', 'id' => $attachment->getId()];
        }

        $differs = $this->desired->apply($attachment, $this->desiredOp($op, $owner, $field, $kind), false)['changed'];
        $file = BlobReceiver::state($this->path($attachment), $op->file->size, $op->file->sha256);

        if ($file !== 'equal') {
            $differs[] = "file.$file";
        }

        if ($kind === 'single' && $owner->get($field . 'Id') !== $attachment->getId()) {
            $differs[] = "owner.{$field}Id";
        }

        return ['status' => $differs ? 'differs' : 'equal', 'id' => $attachment->getId(), 'differs' => $differs,
            'file' => $file];
    }

    /**
     * @return array<string, mixed>
     */
    public function write(stdClass $op, ?Blob $blob): array
    {
        $this->pending = null;

        if (!$blob) {
            throw new ImportError('file_bytes_missing');
        }

        [$owner, $field, $kind] = $this->owner($op);
        $attachment = $this->locate($op, $owner, $field);
        $status = 'updated';

        if (!$attachment) {
            /** @var CoreEntity $attachment */
            $attachment = $this->entityManager->getRDBRepository('Attachment')->getNew();
            $attachment->set('id', $this->idGenerator->generate());
            $status = 'created';
        } elseif ($attachment->get('deleted')) {
            $this->entityManager->getRDBRepository('Attachment')->restoreDeleted($attachment->getId());
            /** @var CoreEntity $attachment */
            $attachment = $this->entityManager->getRDBRepository('Attachment')->getById($attachment->getId());
            $status = 'restored';
        }

        $isNew = $attachment->isNew();

        if ($isNew && isset($op->vtigerId)) {
            $attachment->set('vtigerId', $op->vtigerId);
        }

        $diff = $this->desired->apply($attachment, $this->desiredOp($op, $owner, $field, $kind), $isNew);
        $path = $this->path($attachment);
        $file = $isNew ? 'missing' : BlobReceiver::state($path, $blob->size, $blob->sha256);
        $placed = false;

        if ($file === 'equal') {
            $this->blobs->discard($blob->path);
        } else {
            $this->pending = [$blob, $path]; // placed by placeCommitted() after the COMMIT
            $placed = true;
        }

        $pointer = $kind === 'single' && $owner->get($field . 'Id') !== $attachment->getId();

        if ($isNew || $diff['changed']) {
            $this->entityManager->saveEntity($attachment, [SaveOption::IMPORT => true, SaveOption::SILENT => true,
                SaveOption::NO_NOTIFICATIONS => true]);
        }

        if ($pointer) { // a direct update: the core file saver would remove the attachment it replaces
            $this->entityManager->getQueryExecutor()->execute($this->entityManager->getQueryBuilder()->update()
                ->in($owner->getEntityType())->set([$field . 'Id' => $attachment->getId()])
                ->where(['id' => $owner->getId()])->build());
        }

        $changed = array_merge($diff['changed'], $placed ? ['file'] : [], $pointer ? ["owner.{$field}Id"] : []);

        if (!$changed && $status === 'updated') {
            $status = 'unchanged';
        }

        return ['status' => $status, 'id' => $attachment->getId(), 'changed' => $changed,
            'file' => $placed ? 'written' : 'equal', 'unresolved' => []];
    }

    /**
     * After the transaction of write() committed: the received bytes move to their storage path (atomic within the
     * upload directory). A failure leaves the committed record without its file — reported, written by the next run.
     *
     * @throws ImportError file_storage
     */
    public function placeCommitted(): void
    {
        [$blob, $path] = $this->pending ?? [null, null];
        $this->pending = null;

        if ($blob !== null) {
            $this->blobs->place($blob, $path);
        }
    }

    /**
     * After the transaction of write() failed — a save or the COMMIT itself: nothing was placed, the received bytes
     * are dropped (a COMMIT that succeeded on the way leaves its record without the file: the next run writes it).
     */
    public function discardUncommitted(): void
    {
        [$blob] = $this->pending ?? [null];
        $this->pending = null;

        if ($blob !== null) {
            $this->blobs->discard($blob->path);
        }
    }

    /**
     * @return array{CoreEntity, string, string} the live owner, its field and the field's kind
     */
    private function owner(stdClass $op): array
    {
        $type = $op->owner->entityType ?? null;
        $field = $op->owner->field ?? null;
        $kind = self::OWNERS[$type][$field] ?? null;

        if (!$kind || !isset($op->owner->key) || !isset($op->file->size, $op->file->sha256)) {
            throw new ImportError('bad_operation');
        }

        $id = $this->keys->id($type, $op->owner->key);
        $owner = $id ? $this->entityManager->getEntityById($type, $id) : null;

        if (!$owner instanceof CoreEntity) {
            throw new ImportError($this->keys->isDeleted($type, $op->owner->key) ? 'owner_deleted' : 'owner_missing');
        }

        return [$owner, $field, $kind];
    }

    private function locate(stdClass $op, CoreEntity $owner, string $field): ?CoreEntity
    {
        if (isset($op->vtigerId)) {
            /** @var ?CoreEntity */
            return $this->keys->findWithDeleted('Attachment', $op->vtigerId);
        }

        // no Vtiger attachment id (the logo): the attachment the owner field points to, when this import made it
        // (vtigerData.source names the source column); a logo uploaded in EspoCRM is replaced, never overwritten
        $id = $owner->get($field . 'Id');
        $attachment = $id ? $this->entityManager->getRDBRepository('Attachment')->getById($id) : null;
        $source = $op->attributes->vtigerData->source ?? null;
        $data = $attachment?->get('vtigerData');

        /** @var ?CoreEntity $attachment */
        return $attachment && $source !== null && $data instanceof stdClass && ($data->source ?? null) === $source ?
            $attachment : null;
    }

    private function desiredOp(stdClass $op, CoreEntity $owner, string $field, string $kind): stdClass
    {
        $attributes = clone ($op->attributes ?? new stdClass());
        $single = $kind === 'single';
        $attributes->field = $field;
        $attributes->storage = self::STORAGE;
        $attributes->size = $op->file->size;
        $attributes->relatedType = $single ? $owner->getEntityType() : null;
        $attributes->relatedId = $single ? $owner->getId() : null;
        $attributes->parentType = $single ? null : $owner->getEntityType();
        $attributes->parentId = $single ? null : $owner->getId();

        return (object) ['attributes' => $attributes];
    }

    private function path(CoreEntity $attachment): string
    {
        $sourceId = $attachment->get('sourceId');

        if ($sourceId && $sourceId !== $attachment->getId()) {
            throw new ImportError('file_shared'); // another attachment shares the stored file: never overwritten
        }

        return BlobReceiver::DIR . basename($attachment->getId());
    }
}
