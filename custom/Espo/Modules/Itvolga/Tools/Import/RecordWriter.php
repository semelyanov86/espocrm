<?php

namespace Espo\Modules\Itvolga\Tools\Import;

use Espo\Core\ORM\Entity as CoreEntity;
use Espo\Core\ORM\Repository\Option\SaveOption;
use Espo\Core\Utils\Metadata;
use Espo\Core\Utils\PasswordHash;
use Espo\ORM\EntityManager;
use Espo\ORM\Query\SelectBuilder;
use Espo\ORM\Util;
use stdClass;
use Throwable;

/**
 * Writer of the Vtiger import (stages 06.2–06.3, docs/migration/import.md). One operation = the desired state of one
 * record found by its source key — `vtigerId` (soft-deleted rows included, D-41), or the natural key of the legal
 * entity and of the knowledge base category (KeyResolver::NATURAL_KEYS). Writes only what differs; an unchanged record
 * is not touched (no modifiedAt, no version). After a save, values a hook rewrote (modifiedAt of an insert, a default
 * probability, the contact a task derives from its parent, …) are put back by one direct UPDATE of the record's own
 * row — on finance records only the provenance (FinanceRules: their hooks own the derived values).
 *
 * Saves are silent (`IMPORT` + `SILENT`, no link-multiple hooks); comments (`Note`) skip hooks entirely, since their
 * notification, websocket and stream-time hooks ignore `SILENT`. Reminders the core creates for imported historical
 * events from attendees' preferences are removed. Finance records deleted in EspoCRM are not restored and documents
 * recalculated in EspoCRM keep their calculation data (FinanceRules); files are written by AttachmentWriter.
 */
class RecordWriter
{
    public const ENTITY_TYPES = ['User', 'Account', 'Contact', 'ContactAccess', 'Lead', 'Opportunity', 'Project',
        'ProjectTask', 'Case', 'Task', 'Call', 'Meeting', 'Note', 'Vendor', 'Product', 'LegalEntity', 'Quote',
        'QuoteItem', 'SalesOrder', 'SalesOrderItem', 'Act', 'ActItem', 'Invoice', 'InvoiceItem', 'Payment',
        'PaymentAllocation', 'VtigerArchive', 'KnowledgeBaseCategory', 'KnowledgeBaseArticle', 'DocumentFolder',
        'Document', 'Email', 'Attachment'];
    private const EVENT_TYPES = ['Task', 'Call', 'Meeting'];
    /**
     * Link-multiple fields the core's primary-link hooks unlink when the primary is cleared (Opportunity\Contacts,
     * CaseObj\Contacts, Contact\Accounts): items are added only (owner's rule), so what the save removes is put back.
     */
    private const KEPT_LINKS = ['Opportunity' => ['contacts', 'contactId'], 'Case' => ['contacts', 'contactId'],
        'Contact' => ['accounts', 'accountId']];
    /**
     * Entity types whose enum defaults are not applied to imported records (D-38: empty stays empty). Finance records
     * keep them: their operations own every source enum, the other ones are derived by the finance hooks.
     */
    private const NO_DEFAULTS = ['Account', 'Contact', 'Lead', 'Opportunity', 'Project', 'ProjectTask', 'Case', 'Task',
        'Call', 'Meeting', 'Vendor', 'Product', 'VtigerArchive', 'KnowledgeBaseArticle', 'Document', 'Email'];

    public function __construct(
        private EntityManager $entityManager,
        private Metadata $metadata,
        private DesiredState $desired,
        private KeyResolver $keys,
        private PasswordHash $passwordHash,
        private FinanceRules $finance,
        private FinanceCheck $financeCheck,
        private AttachmentWriter $attachments,
    ) {}

    /**
     * @return array<string, mixed>
     */
    public function handle(stdClass $op, bool $check, ?string $adoptUserName, ?Blob $blob = null): array
    {
        $type = $op->entityType ?? null;

        if (!in_array($type, self::ENTITY_TYPES, true) || !$this->validKey($op)) {
            throw new ImportError('bad_operation');
        }

        if ($type === 'Attachment') {
            if ($check) {
                return $this->attachments->check($op);
            }

            try {
                return $this->entityManager->getTransactionManager()->run(fn () => $this->attachments->write($op, $blob));
            } catch (Throwable $e) {
                $this->attachments->discardUncommitted(); // the transaction is over: its record decides the file

                throw $e;
            }
        }

        if ($check) {
            return $this->check($op);
        }

        $result = $this->entityManager->getTransactionManager()->run(fn () => $this->write($op, $adoptUserName));

        if (isset($result['id']) && in_array($result['status'], ['created', 'restored', 'adopted', 'updated'], true)) {
            $this->keys->remember($type, $this->key($op), $result['id']); // only once the transaction committed
        }

        return $result;
    }

    /**
     * @return array{inventory: string, live: int[], deleted: int[]}
     */
    public function inventory(string $entityType): array
    {
        if (!in_array($entityType, self::ENTITY_TYPES, true) || isset(KeyResolver::NATURAL_KEYS[$entityType])) {
            throw new ImportError('bad_operation');
        }

        $query = SelectBuilder::create()
            ->from($entityType)
            ->select(['vtigerId', 'deleted'])
            ->where(['vtigerId!=' => null])
            ->withDeleted()
            ->build();

        $live = $deleted = [];

        foreach ($this->entityManager->getQueryExecutor()->execute($query) as $row) {
            if ($row['deleted']) {
                $deleted[] = (int) $row['vtigerId'];
            } else {
                $live[] = (int) $row['vtigerId'];
            }
        }

        return ['inventory' => $entityType, 'live' => $live, 'deleted' => $deleted];
    }

    /**
     * @return array<string, mixed>
     */
    private function check(stdClass $op): array
    {
        $entity = $this->keys->findWithDeleted($op->entityType, $this->key($op));

        if ($guarded = $this->finance->guard($op, $entity, true)) {
            return $guarded; // a finance record deleted in EspoCRM, an item of a recalculated document: findings
        }

        if (!$entity instanceof CoreEntity) {
            return ['status' => ($op->onlyIfExists ?? false) ? 'absent' : 'missing'];
        }

        if ($entity->get('deleted')) {
            return ['status' => 'deleted', 'id' => $entity->getId()];
        }

        $protected = $this->finance->protect($op, $entity);
        $diff = $this->desired->apply($entity, $op, false);
        $related = $this->desired->relate($entity, $op, false);
        $differs = array_merge($diff['changed'], $related['changed'], $this->unreadEmail($entity) ? ['users.isRead'] : []);

        if ($op->entityType === 'User') {
            $differs = array_merge($differs, $this->desired->preferencesDiff($entity->getId(), $op->preferences ?? null));
        }

        $result = ['status' => $differs ? 'differs' : 'equal', 'id' => $entity->getId(), 'differs' => $differs,
            'unresolved' => array_merge($diff['unresolved'], $related['unresolved']),
            'deletedTargets' => array_merge($diff['deletedTargets'], $related['deletedTargets'])];

        if ($protected) {
            $result['protected'] = $protected;
        }

        if ($verification = $this->financeCheck->document($entity)) {
            $result['verification'] = $verification;
        }

        if ($legalEntity = $this->financeCheck->legalEntity($entity)) {
            $result['legalEntity'] = $legalEntity;
        }

        return $result;
    }

    /**
     * @return array<string, mixed>
     */
    private function write(stdClass $op, ?string $adoptUserName): array
    {
        $type = $op->entityType;
        $this->finance->lock($op); // first: the reads below see a recalculation committed before the lock

        foreach ($op->keyAlsoIn ?? [] as $other) {
            if (in_array($other, self::EVENT_TYPES, true) && $this->keys->findWithDeleted($other, $op->vtigerId)) {
                throw new ImportError('type_changed'); // a source activity changed its type: delta policy (06.4)
            }
        }

        $entity = $this->keys->findWithDeleted($type, $this->key($op));

        if ($guarded = $this->finance->guard($op, $entity)) {
            return $guarded; // owner's answers 2026-10-11: not restored, not recalculated back
        }

        $status = 'updated';

        if (!$entity) {
            if ($op->onlyIfExists ?? false) {
                return ['status' => 'skipped'];
            }

            if ($type === 'LegalEntity') {
                throw new ImportError('legal_entity_missing'); // the singleton comes from itvolga-setup-finance
            }

            [$entity, $status] = $type === 'User' ? $this->newUser($op, $adoptUserName) : [$this->newRecord($type), 'created'];
        } elseif ($entity->get('deleted')) {
            $entity = $this->restore($type, $entity->getId(), $op);
            $status = 'restored';
        }

        assert($entity instanceof CoreEntity);
        $isNew = $entity->isNew();

        if ($isNew) {
            $entity->set($this->keys->keyAttribute($type), $this->key($op));
        }

        $protected = $isNew ? [] : $this->finance->protect($op, $entity);
        $diff = $this->desired->apply($entity, $op, $isNew);

        if ($isNew && $diff['unresolved'] && $this->finance->isFinance($type)) {
            throw new ImportError('unresolved_links', $diff['unresolved']); // never a finance row without its owner
        }

        $related = $isNew ? null : $this->desired->relate($entity, $op, false);
        $preferences = $type === 'User' && !$isNew ?
            $this->desired->preferencesDiff($entity->getId(), $op->preferences ?? null) : [];
        $save = $isNew || $diff['changed'] || $preferences || $status !== 'updated';
        $unread = !$isNew && $this->unreadEmail($entity);

        if (!$save && !$related['changed'] && !$unread) {
            return ['status' => 'unchanged', 'id' => $entity->getId(), 'unresolved' => $diff['unresolved'],
                'deletedTargets' => array_merge($diff['deletedTargets'], $related['deletedTargets'])] +
                ($protected ? ['protected' => $protected] : []);
        }

        $forced = [];

        if ($save) {
            $reminders = in_array($type, self::EVENT_TYPES, true) && !$isNew ? $this->reminders($type, $entity->getId()) : [];
            $kept = $this->linkedIds($entity, $isNew);
            $untouched = $this->untouchedLinks($entity, $op, $isNew);

            $this->entityManager->saveEntity($entity, $this->saveOptions($type));
            $forced = $this->force($entity, $op, $untouched);
            $this->relinkRemoved($entity, $kept);

            if (in_array($type, self::EVENT_TYPES, true)) {
                $this->keepReminders($type, $entity->getId(), $reminders);
            }

            if ($type === 'User' && isset($op->preferences)) {
                if ($isNew) {
                    $preferences = $this->desired->preferencesDiff($entity->getId(), $op->preferences);
                }

                if ($preferences) {
                    $this->desired->savePreferences($entity->getId(), $op->preferences);
                }
            }
        }

        $related = $this->desired->relate($entity, $op, true);

        if ($type === 'Email') {
            $this->markEmailRead($entity->getId()); // owner's answer 2026-10-11: archived mail is not «new»
        }

        return ['status' => $status, 'id' => $entity->getId(),
            'changed' => array_merge($diff['changed'], $preferences, $related['changed'], $unread ? ['users.isRead'] : []),
            'forced' => $forced, 'unresolved' => array_merge($diff['unresolved'], $related['unresolved']),
            'deletedTargets' => array_merge($diff['deletedTargets'], $related['deletedTargets'])] +
            ($protected ? ['protected' => $protected] : []);
    }

    private function validKey(stdClass $op): bool
    {
        if (isset(KeyResolver::NATURAL_KEYS[$op->entityType])) {
            return is_string($op->naturalKey ?? null) && $op->naturalKey !== '';
        }

        if ($op->entityType === 'Attachment' && !property_exists($op, 'vtigerId')) {
            return true; // a file without a Vtiger attachment id: located through its owner field (the logo)
        }

        return is_int($op->vtigerId ?? null) && $op->vtigerId >= 1;
    }

    private function key(stdClass $op): int|string
    {
        return isset(KeyResolver::NATURAL_KEYS[$op->entityType]) ? $op->naturalKey : $op->vtigerId;
    }

    /**
     * Users the core links to an imported email by its addresses see it as read (owner's answer 2026-10-11).
     */
    private function markEmailRead(string $emailId): void
    {
        $this->entityManager->getQueryExecutor()->execute($this->entityManager->getQueryBuilder()->update()
            ->in('EmailUser')->set(['isRead' => true])
            ->where(['emailId' => $emailId, 'isRead' => false, 'deleted' => false])->build());
    }

    private function unreadEmail(CoreEntity $entity): bool
    {
        if ($entity->getEntityType() !== 'Email') {
            return false;
        }

        return (bool) $this->entityManager->getRDBRepository('EmailUser')
            ->where(['emailId' => $entity->getId(), 'isRead' => false])->count();
    }

    /**
     * @return array<string, mixed>
     */
    private function saveOptions(string $type): array
    {
        $options = [
            SaveOption::IMPORT => true,
            SaveOption::SILENT => true,
            SaveOption::NO_NOTIFICATIONS => true,
            'skipLinkMultipleHooks' => true,
        ];

        if ($type === 'Note') {
            $options[SaveOption::SKIP_HOOKS] = true;
        }

        return $options;
    }

    private function newRecord(string $type): CoreEntity
    {
        /** @var CoreEntity $entity */
        $entity = $this->entityManager->getRDBRepository($type)->getNew();

        if (in_array($type, self::NO_DEFAULTS, true)) {
            foreach ($this->metadata->get(['entityDefs', $type, 'fields']) ?? [] as $field => $defs) {
                if (($defs['type'] ?? null) === 'enum' && array_key_exists('default', $defs) && $entity->hasAttribute($field)) {
                    $entity->set($field, null);
                }
            }
        }

        return $entity;
    }

    /**
     * Vtiger's effective administrator may take over the existing administrator of the installation with the same
     * login (owner's answer 2026-10-11; its password is never touched); any other login already in use is an error.
     *
     * @return array{CoreEntity, string}
     */
    private function newUser(stdClass $op, ?string $adoptUserName): array
    {
        $userName = $op->attributes->userName ?? null;

        if (!is_string($userName) || $userName === '') {
            throw new ImportError('invalid', ['userName:empty']);
        }

        $existing = $this->entityManager->getRDBRepository('User')->where(['userName' => $userName])->findOne();

        if ($existing) {
            $adoptable = ($op->user->adopt ?? false) && $adoptUserName !== null && $userName === $adoptUserName &&
                $existing->get('type') === 'admin' && $existing->get('vtigerId') === null;

            if (!$adoptable) {
                throw new ImportError('username_clash');
            }

            $existing->set('vtigerId', $op->vtigerId);

            /** @var CoreEntity $existing */
            return [$existing, 'adopted'];
        }

        /** @var CoreEntity $user */
        $user = $this->entityManager->getRDBRepository('User')->getNew();
        // An unusable password (nobody knows it); the administrator sets one before the first login.
        $user->set('password', $this->passwordHash->hash(bin2hex(random_bytes(32))));

        return [$user, 'created'];
    }

    private function restore(string $type, string $id, stdClass $op): CoreEntity
    {
        $values = [];

        if ($type === 'User') {
            $userName = $op->attributes->userName ?? null;

            if (!is_string($userName) || $userName === '' ||
                $this->entityManager->getRDBRepository('User')->where(['userName' => $userName])->findOne()) {
                throw new ImportError('username_clash');
            }

            $values['userName'] = $userName; // with deleteId at once: the old login may be taken by now
        }

        $repository = $this->entityManager->getRDBRepository($type);
        $repository->restoreDeleted($id);

        if ($this->entityManager->getDefs()->getEntity($type)->hasAttribute('deleteId')) {
            $this->update($type, $id, $values + ['deleteId' => '0']);
        }

        $entity = $repository->getById($id);

        if (!$entity instanceof CoreEntity) {
            throw new ImportError('restore_failed');
        }

        return $entity;
    }

    /**
     * Puts back what hooks rewrote: every stored scalar the operation owns, plus the ids of its resolved links.
     *
     * @return string[] Attributes rewritten.
     */
    private function force(CoreEntity $entity, stdClass $op, array $untouched = []): array
    {
        $type = $entity->getEntityType();
        $defs = $this->entityManager->getDefs()->getEntity($type);
        $fresh = $this->entityManager->getRDBRepository($type)->getById($entity->getId());

        if (!$fresh) {
            throw new ImportError('not_saved');
        }

        $want = [];

        foreach (get_object_vars($op->attributes ?? new stdClass()) as $attribute => $value) {
            if (!$defs->hasAttribute($attribute) || $defs->getAttribute($attribute)->isNotStorable() ||
                in_array($defs->getAttribute($attribute)->getType(), ['jsonObject', 'jsonArray'], true)) {
                continue;
            }

            $want[$attribute] = $value;
        }

        foreach (get_object_vars($op->links ?? new stdClass()) as $link => $ref) {
            $id = $ref === null ? null : $this->keys->id($ref[0], $ref[1]);

            if ($ref !== null && !$id) {
                continue;
            }

            $want[$link . 'Id'] = $id;

            if ($defs->tryGetRelation($link)?->isBelongsToParent()) {
                $want[$link . 'Type'] = $ref[0] ?? null;
            }
        }

        $want = $untouched + $this->finance->forceable($type, $want); // keep: hooks must not change them either
        $scratch = $this->entityManager->getRDBRepository($type)->getNew();
        $fix = [];

        foreach ($want as $attribute => $value) {
            $scratch->set($attribute, $value);
            $expected = $scratch->get($attribute);

            if (!Util::areValuesEqual($defs->getAttribute($attribute)->getType(), $fresh->get($attribute), $expected)) {
                $fix[$attribute] = $expected;
            }
        }

        if ($fix) {
            $this->update($type, $entity->getId(), $fix);
        }

        return array_keys($fix);
    }

    /**
     * Stored values of the single links an operation leaves untouched (`keep`: their target is imported by a later
     * stage or not in this run). A hook of the save (Task ParentLink…) must not change them.
     *
     * @return array<string, mixed>
     */
    private function untouchedLinks(CoreEntity $entity, stdClass $op, bool $isNew): array
    {
        $out = [];

        if ($isNew) {
            return $out;
        }

        $defs = $this->entityManager->getDefs()->getEntity($entity->getEntityType());

        foreach ($op->keep ?? [] as $link) {
            if (!is_string($link) || !$defs->hasAttribute($link . 'Id')) {
                continue;
            }

            $out[$link . 'Id'] = $entity->getFetched($link . 'Id');

            if ($defs->tryGetRelation($link)?->isBelongsToParent()) {
                $out[$link . 'Type'] = $entity->getFetched($link . 'Type');
            }
        }

        return $out;
    }

    /**
     * Items of the kept link-multiple field before the save (current ones plus those being added) with their columns.
     *
     * @return array<string, array<string, mixed>> id → columns
     */
    private function linkedIds(CoreEntity $entity, bool $isNew): array
    {
        [$link] = self::KEPT_LINKS[$entity->getEntityType()] ?? [null];

        if (!$link || $isNew) {
            return [];
        }

        if (!$entity->has($link . 'Ids')) {
            $entity->loadLinkMultipleField($link);
        }

        $columns = $entity->get($link . 'Columns');
        $out = [];

        foreach ($entity->getLinkMultipleIdList($link) as $id) {
            $out[$id] = $columns && isset($columns->$id) ? get_object_vars($columns->$id) : [];
        }

        return $out;
    }

    /**
     * Puts back what the core's primary-link hooks removed or rewrote (a manual link and its role), except on the
     * record the operation makes the primary one (its role comes from the source).
     *
     * @param array<string, array<string, mixed>> $before
     */
    private function relinkRemoved(CoreEntity $entity, array $before): void
    {
        [$link, $primaryAttribute] = self::KEPT_LINKS[$entity->getEntityType()] ?? [null, null];

        if (!$link || !$before) {
            return;
        }

        $relation = $this->entityManager->getRDBRepository($entity->getEntityType())->getRelation($entity, $link);
        $fresh = $this->entityManager->getRDBRepository($entity->getEntityType())->getById($entity->getId());

        if (!$fresh instanceof CoreEntity) {
            return;
        }

        $primary = $fresh->get($primaryAttribute);
        $fresh->loadLinkMultipleField($link);
        $now = $fresh->get($link . 'Columns');

        foreach ($before as $id => $columns) {
            $options = [SaveOption::SILENT => true, SaveOption::SKIP_HOOKS => true];

            if (!$relation->isRelatedById($id)) {
                $relation->relateById($id, $columns ?: null, $options); // the junction row is restored
            } elseif ($columns && $id !== $primary && $now && isset($now->$id) && get_object_vars($now->$id) != $columns) {
                $relation->updateColumnsById($id, $columns);
            }
        }
    }

    /**
     * @param array<string, mixed> $values
     */
    private function update(string $type, string $id, array $values): void
    {
        $query = $this->entityManager->getQueryBuilder()->update()->in($type)->set($values)
            ->where(['id' => $id])->build();

        $this->entityManager->getQueryExecutor()->execute($query);
    }

    /**
     * Reminders are not the import's business: the core's reminder saver deletes and re-creates them from the
     * attendees' preferences when dates or attendees change, even on a silent save. The rows an event had before the
     * save are put back exactly, the ones the save created are removed.
     *
     * @return array<string, array<string, mixed>> id → stored values
     */
    private function reminders(string $type, string $id): array
    {
        $defs = $this->entityManager->getDefs()->getEntity('Reminder');
        $out = [];

        foreach ($this->entityManager->getRDBRepository('Reminder')->where(['entityType' => $type, 'entityId' => $id])
                     ->find() as $reminder) {
            $values = [];

            foreach ($defs->getAttributeNameList() as $attribute) {
                if (!$defs->getAttribute($attribute)->isNotStorable()) {
                    $values[$attribute] = $reminder->get($attribute);
                }
            }

            $out[$reminder->getId()] = $values;
        }

        return $out;
    }

    /**
     * @param array<string, array<string, mixed>> $before
     */
    private function keepReminders(string $type, string $id, array $before): void
    {
        $after = $this->reminders($type, $id);
        $new = array_diff(array_keys($after), array_keys($before));

        if ($new) {
            $this->entityManager->getQueryExecutor()->execute($this->entityManager->getQueryBuilder()->delete()
                ->from('Reminder')->where(['id' => array_values($new)])->build());
        }

        foreach (array_diff_key($before, $after) as $values) {
            $this->entityManager->getQueryExecutor()->execute($this->entityManager->getQueryBuilder()->insert()
                ->into('Reminder')->columns(array_keys($values))->values($values)->build());
        }
    }
}
