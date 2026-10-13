<?php

namespace Espo\Modules\Itvolga\Tools\Import;

use Espo\Core\ORM\Entity as CoreEntity;
use Espo\Core\ORM\Repository\Option\SaveOption;
use Espo\Modules\Itvolga\Hooks\Common\FinanceDeltaMark;
use Espo\ORM\EntityManager;
use stdClass;

/**
 * Records gone from the source (stage 06.4, docs/migration/import.md «Дельта», owner's answers 2026-10-12): Python
 * decides which keys left the source, this class decides how a record of each type leaves EspoCRM —
 *
 * - User: deactivated, never deleted (its records keep their owner); an administrator is kept;
 * - finance records: under the payment-side locks, a document recalculated in EspoCRM and its items are kept, so is a
 *   document an imported allocation still points to (its allocation is not part of the run, or held: the finance hook
 *   would remove it unmarked); anything else is removed through the finance hooks with the delta's option — the hook
 *   FinanceDeltaMark marks it `vtigerData.deletedInSource` (allocations go, settlement is recalculated); Python sends
 *   children before their owners, so each row carries its own mark;
 * - Attachment: the owner's file or image field is cleared when it still points to it, the core hook removes the bytes
 *   (unless another attachment shares them);
 * - anything else: a silent soft delete (`IMPORT` + `SILENT` + `NO_NOTIFICATIONS`, comments without hooks, as saves).
 *
 * Natural-key types (the legal entity, the knowledge base category) are never removed. Answers carry ids, counts and
 * closed codes only; the check pass answers the same policy read-only.
 */
class RemovalWriter
{
    private const EVENT_TYPES = ['Task', 'Call', 'Meeting'];

    public function __construct(
        private EntityManager $entityManager,
        private KeyResolver $keys,
        private FinanceRules $finance,
    ) {}

    /**
     * Inside the writer's transaction (apply).
     *
     * @return array<string, mixed>
     */
    public function remove(stdClass $op, RunContext $run): array
    {
        [$type, $key] = $this->validated($op, $run);

        if ($this->finance->isFinance($type)) {
            $this->finance->lockLedger($type); // before the first plain read: the transaction's snapshot
        }

        $entity = $this->keys->findWithDeleted($type, $key);

        if (!$entity instanceof CoreEntity) {
            return ['status' => 'absent'];
        }

        if ($this->finance->isFinance($type) && !$entity->get('deleted')) {
            $this->finance->lockForRemoval($type, $entity);
            $entity = $this->keys->findWithDeleted($type, $key); // after the locks: what a concurrent write left
        }

        if (!$entity instanceof CoreEntity) {
            return ['status' => 'absent'];
        }

        $id = $entity->getId();

        if ($entity->get('deleted')) {
            return ['status' => 'unchanged', 'id' => $id, 'state' => 'deleted'];
        }

        if ($kept = $this->kept($type, $entity, $run)) {
            return ['status' => 'kept', 'id' => $id, 'reason' => $kept];
        }

        if ($type === 'User') {
            if (!$entity->get('isActive')) {
                return ['status' => 'unchanged', 'id' => $id, 'state' => 'inactive'];
            }

            $entity->set('isActive', false);
            $this->entityManager->saveEntity($entity, $this->options('User') + ['skipLinkMultipleHooks' => true]);

            return ['status' => 'deactivated', 'id' => $id];
        }

        $reminders = in_array($type, self::EVENT_TYPES, true) ? $this->reminderCount($type, $id) : 0;

        if ($type === 'Attachment') {
            $this->releaseOwner($entity);
        }

        // finance: the hook FinanceDeltaMark marks the record (vtigerData.deletedInSource) with deleted = 1
        $this->entityManager->removeEntity($entity, $this->options($type) + [FinanceDeltaMark::OPTION => true]);

        return ['status' => 'removed', 'id' => $id] + ($reminders ? ['effects' => ['reminder' => -$reminders]] : []);
    }

    /**
     * The same policy read-only (check pass): `removed` (a tombstone, an inactive user, no row), `kept` or `live`.
     *
     * @return array<string, mixed>
     */
    public function state(stdClass $op, RunContext $run): array
    {
        [$type, $key] = $this->validated($op, $run);
        $entity = $this->keys->findWithDeleted($type, $key);

        if (!$entity instanceof CoreEntity) {
            return ['status' => 'removed', 'state' => 'absent'];
        }

        $id = $entity->getId();

        if ($entity->get('deleted')) {
            return ['status' => 'removed', 'id' => $id, 'state' => 'deleted'];
        }

        if ($kept = $this->kept($type, $entity, $run)) {
            return ['status' => 'kept', 'id' => $id, 'reason' => $kept];
        }

        if ($type === 'User' && !$entity->get('isActive')) {
            return ['status' => 'removed', 'id' => $id, 'state' => 'inactive'];
        }

        return ['status' => 'live', 'id' => $id];
    }

    /**
     * @return array{string, int}
     */
    private function validated(stdClass $op, RunContext $run): array
    {
        $type = $op->entityType ?? null;
        $key = $op->vtigerId ?? null;

        if (!$run->removalsEnabled() || !is_string($type) || !in_array($type, RecordWriter::ENTITY_TYPES, true) ||
            !$run->ownsType($type) || !$run->inRange($key)) {
            throw new ImportError('bad_operation');
        }

        return [$type, $key];
    }

    private function kept(string $type, CoreEntity $entity, RunContext $run): ?string
    {
        if ($type === 'User') {
            return in_array($entity->get('type'), ['admin', 'super-admin'], true) ? 'administrator' : null;
        }

        return $this->finance->isFinance($type) ? $this->finance->keptOnRemoval($type, $entity, $run) : null;
    }

    /**
     * @return array<string, bool>
     */
    private function options(string $type): array
    {
        return [SaveOption::IMPORT => true, SaveOption::SILENT => true, SaveOption::NO_NOTIFICATIONS => true] +
            ($type === 'Note' ? [SaveOption::SKIP_HOOKS => true] : []);
    }

    /**
     * Reminders of an event: the core's event repository deletes them physically with the record (an expected effect
     * of the removal for the silence check).
     */
    private function reminderCount(string $type, string $id): int
    {
        return $this->entityManager->getRDBRepository('Reminder')->where(['entityType' => $type, 'entityId' => $id])
            ->count();
    }

    /**
     * A file or image field that still points to the removed attachment is cleared by a direct update (the core file
     * saver would act on its own); attachment lists follow the attachment's parent and need nothing.
     */
    private function releaseOwner(CoreEntity $attachment): void
    {
        $type = $attachment->get('relatedType');
        $ownerId = $attachment->get('relatedId');
        $field = $attachment->get('field');

        if (!$type || !$ownerId || (AttachmentWriter::OWNERS[$type][$field] ?? null) !== 'single') {
            return;
        }

        $this->entityManager->getQueryExecutor()->execute($this->entityManager->getQueryBuilder()->update()
            ->in($type)->set([$field . 'Id' => null])
            ->where(['id' => $ownerId, $field . 'Id' => $attachment->getId()])->build());
    }
}
