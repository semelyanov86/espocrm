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

/**
 * Writer of the Vtiger import (stage 06.2, docs/migration/import.md). One operation = the desired state of one record
 * found by `vtigerId` (soft-deleted rows included, D-41). Writes only what differs; an unchanged record is not touched
 * (no modifiedAt, no version). After a save, values a hook rewrote (modifiedAt of an insert, a default probability,
 * the contact a task derives from its parent, …) are put back by one direct UPDATE of the record's own row.
 *
 * Saves are silent (`IMPORT` + `SILENT`, no link-multiple hooks); comments (`Note`) skip hooks entirely, since their
 * notification, websocket and stream-time hooks ignore `SILENT`. Reminders the core creates for imported historical
 * events from attendees' preferences are removed.
 */
class RecordWriter
{
    public const ENTITY_TYPES = ['User', 'Account', 'Contact', 'ContactAccess', 'Lead', 'Opportunity', 'Project',
        'ProjectTask', 'Case', 'Task', 'Call', 'Meeting', 'Note'];
    private const EVENT_TYPES = ['Task', 'Call', 'Meeting'];
    /**
     * Link-multiple fields the core's primary-link hooks unlink when the primary is cleared (Opportunity\Contacts,
     * CaseObj\Contacts, Contact\Accounts): items are added only (owner's rule), so what the save removes is put back.
     */
    private const KEPT_LINKS = ['Opportunity' => ['contacts', 'contactId'], 'Case' => ['contacts', 'contactId'],
        'Contact' => ['accounts', 'accountId']];
    /** Entity types whose enum defaults are not applied to imported records (D-38: empty stays empty). */
    private const NO_DEFAULTS = ['Account', 'Contact', 'Lead', 'Opportunity', 'Project', 'ProjectTask', 'Case', 'Task',
        'Call', 'Meeting'];

    public function __construct(
        private EntityManager $entityManager,
        private Metadata $metadata,
        private DesiredState $desired,
        private KeyResolver $keys,
        private PasswordHash $passwordHash,
    ) {}

    /**
     * @return array<string, mixed>
     */
    public function handle(stdClass $op, bool $check, ?string $adoptUserName): array
    {
        $type = $op->entityType ?? null;

        if (!in_array($type, self::ENTITY_TYPES, true) || !is_int($op->vtigerId ?? null) || $op->vtigerId < 1) {
            throw new ImportError('bad_operation');
        }

        if ($check) {
            return $this->check($op);
        }

        return $this->entityManager->getTransactionManager()->run(fn () => $this->write($op, $adoptUserName));
    }

    /**
     * @return array{inventory: string, live: int[], deleted: int[]}
     */
    public function inventory(string $entityType): array
    {
        if (!in_array($entityType, self::ENTITY_TYPES, true)) {
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
        $entity = $this->keys->findWithDeleted($op->entityType, $op->vtigerId);

        if (!$entity instanceof CoreEntity) {
            return ['status' => ($op->onlyIfExists ?? false) ? 'absent' : 'missing'];
        }

        if ($entity->get('deleted')) {
            return ['status' => 'deleted', 'id' => $entity->getId()];
        }

        $diff = $this->desired->apply($entity, $op, false);
        $differs = $diff['changed'];

        if ($op->entityType === 'User') {
            $differs = array_merge($differs, $this->desired->preferencesDiff($entity->getId(), $op->preferences ?? null));
        }

        return ['status' => $differs ? 'differs' : 'equal', 'id' => $entity->getId(), 'differs' => $differs,
            'unresolved' => $diff['unresolved']];
    }

    /**
     * @return array<string, mixed>
     */
    private function write(stdClass $op, ?string $adoptUserName): array
    {
        $type = $op->entityType;
        $repository = $this->entityManager->getRDBRepository($type);

        foreach ($op->keyAlsoIn ?? [] as $other) {
            if (in_array($other, self::EVENT_TYPES, true) && $this->keys->findWithDeleted($other, $op->vtigerId)) {
                throw new ImportError('type_changed'); // a source activity changed its type: delta policy (06.4)
            }
        }

        $entity = $this->keys->findWithDeleted($type, $op->vtigerId);
        $status = 'updated';

        if (!$entity) {
            if ($op->onlyIfExists ?? false) {
                return ['status' => 'skipped'];
            }

            [$entity, $status] = $type === 'User' ? $this->newUser($op, $adoptUserName) : [$this->newRecord($type), 'created'];
        } elseif ($entity->get('deleted')) {
            $entity = $this->restore($type, $entity->getId(), $op);
            $status = 'restored';
        }

        assert($entity instanceof CoreEntity);
        $isNew = $entity->isNew();

        if ($isNew) {
            $entity->set('vtigerId', $op->vtigerId);
        }

        $diff = $this->desired->apply($entity, $op, $isNew);
        $preferences = $type === 'User' && !$isNew ?
            $this->desired->preferencesDiff($entity->getId(), $op->preferences ?? null) : [];

        if (!$isNew && !$diff['changed'] && !$preferences && $status === 'updated') {
            return ['status' => 'unchanged', 'id' => $entity->getId(), 'unresolved' => $diff['unresolved']];
        }

        $reminders = in_array($type, self::EVENT_TYPES, true) && !$isNew ? $this->reminders($type, $entity->getId()) : [];
        $kept = $this->linkedIds($entity, $isNew);
        $untouched = $this->untouchedLinks($entity, $op, $isNew);

        $this->entityManager->saveEntity($entity, $this->saveOptions($type));
        $this->keys->remember($type, $op->vtigerId, $entity->getId());
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

        return ['status' => $status, 'id' => $entity->getId(), 'changed' => array_merge($diff['changed'], $preferences),
            'forced' => $forced, 'unresolved' => $diff['unresolved']];
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

        $want = $untouched + $want; // links the operation leaves as they are: hooks must not change them either
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
