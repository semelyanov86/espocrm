<?php

namespace Espo\Modules\Itvolga\Tools\Import;

use Espo\Core\ORM\Entity as CoreEntity;
use Espo\Core\ORM\Repository\Option\SaveOption;
use Espo\Core\Utils\Metadata;
use Espo\Modules\Itvolga\Tools\Acl\HierarchyTeams;
use Espo\Modules\Itvolga\Tools\ContactAccess\PasswordCipher;
use Espo\ORM\EntityManager;
use Espo\Repositories\EmailAddress as EmailAddressRepository;
use Espo\Repositories\PhoneNumber as PhoneNumberRepository;
use stdClass;

/**
 * Puts the desired state of an import operation (docs/migration/import.md, «Операция») on an entity and tells what
 * differs from the stored state — the same code for writing and for the check pass, so «unchanged» and «equal» mean
 * the same thing. Values are validated against the merged metadata (ORM writes are not validated by the core).
 *
 * Difference names: attribute names, `<link>Id`, `<link>` (link-multiple), `emailAddressData`, `phoneNumberData`,
 * `secret.<attribute>`, `vtigerData.<key>`.
 */
class DesiredState
{
    /** Attributes an operation may never set (identity, deletion, credentials). */
    /** Address fields of an Email, compared as sets (DesiredState::applyEmailAddresses). */
    private const EMAIL_ADDRESS_FIELDS = ['from', 'to', 'cc', 'bcc'];
    private const FORBIDDEN = ['id', 'deleted', 'deleteId', 'password', 'passwordVersion', 'apiKey', 'secretKey',
        'authMethod', 'authLogRecordId', 'hasAnydeskPassword', 'anydeskPassword'];

    public function __construct(
        private EntityManager $entityManager,
        private Metadata $metadata,
        private KeyResolver $keys,
        private HierarchyTeams $hierarchyTeams,
        private PasswordCipher $cipher,
    ) {}

    /**
     * @return array{changed: string[], unresolved: string[], deletedTargets: string[]}
     * @throws ImportError invalid values (codes and attribute names only)
     */
    public function apply(CoreEntity $entity, stdClass $op, bool $isNew): array
    {
        $type = $entity->getEntityType();
        $changed = [];
        $unresolved = [];
        $deletedTargets = [];
        $invalid = [];

        foreach (get_object_vars($op->attributes ?? new stdClass()) as $attribute => $value) {
            $code = $this->validate($type, $attribute, $value);

            if ($code) {
                $invalid[] = "$attribute:$code";

                continue;
            }

            if ($attribute === 'vtigerData') {
                if ($this->vtigerDataDiffers($entity->get('vtigerData'), $value)) {
                    $entity->set('vtigerData', $value);
                    $changed = array_merge($changed, $this->vtigerDataKeys($entity->getFetched('vtigerData'), $value));
                }

                continue;
            }

            if ($this->isJsonObject($type, $attribute)) { // VtigerArchive.data: key order is not a difference
                if ($isNew || $this->vtigerDataDiffers($entity->get($attribute), $value)) {
                    $entity->set($attribute, $value);
                    $changed[] = $attribute;
                }

                continue;
            }

            if ($type === 'Email' && in_array($attribute, self::EMAIL_ADDRESS_FIELDS, true)) {
                $this->applyEmailAddresses($entity, $attribute, $value, $isNew, $changed);

                continue;
            }

            $entity->set($attribute, $value);

            if ($isNew || $entity->isAttributeChanged($attribute)) {
                $changed[] = $attribute;
            }
        }

        if ($invalid) {
            throw new ImportError('invalid', $invalid);
        }

        foreach (get_object_vars($op->links ?? new stdClass()) as $link => $ref) {
            $this->applyLink($entity, $link, $ref, $isNew, $changed, $unresolved, $deletedTargets);
        }

        foreach (get_object_vars($op->linkMultiple ?? new stdClass()) as $link => $spec) {
            $this->applyLinkMultiple($entity, $link, $spec, $isNew, $changed, $unresolved, $deletedTargets);
        }

        if ($entity->hasLinkMultipleField('teams') && $this->hierarchyTeams->getRules($type) &&
            isset($op->linkMultiple->teams)) {
            $before = $entity->getLinkMultipleIdList('teams');
            $this->hierarchyTeams->applyToRecord($entity);

            if (!$this->sameSet($before, $entity->getLinkMultipleIdList('teams')) && !in_array('teams', $changed)) {
                $changed[] = 'teams';
            }
        }

        if (property_exists($op, 'emails')) {
            $this->applyEmails($entity, $op->emails, $isNew, $changed);
        }

        if (property_exists($op, 'phones')) {
            $this->applyPhones($entity, $op->phones, $isNew, $changed);
        }

        foreach (get_object_vars($op->secret ?? new stdClass()) as $attribute => $plain) {
            $this->applySecret($entity, $attribute, $plain, $changed);
        }

        return ['changed' => array_values(array_unique($changed)), 'unresolved' => array_values(array_unique($unresolved)),
            'deletedTargets' => array_values(array_unique($deletedTargets))];
    }

    /**
     * Add-only relation items of links without a link-multiple field (stage 06.3: a Document and the records it is
     * attached to, `vtiger_senotesrel`): `{"<link>": [[entityType, key], …]}`. Rows made in EspoCRM stay; rows are
     * written without hooks (no stream notes, no notifications).
     *
     * @return array{changed: string[], unresolved: string[], deletedTargets: string[]}
     */
    public function relate(CoreEntity $entity, stdClass $op, bool $write): array
    {
        $changed = $unresolved = $deleted = [];
        $defs = $this->entityManager->getDefs()->getEntity($entity->getEntityType());
        $repository = $this->entityManager->getRDBRepository($entity->getEntityType());

        foreach (get_object_vars($op->relate ?? new stdClass()) as $link => $items) {
            $relationDefs = $defs->tryGetRelation($link);

            if (!$relationDefs || !$relationDefs->isManyToMany() || !is_array($items)) {
                throw new ImportError('invalid', ["$link:unknown_link"]);
            }

            $relation = $repository->getRelation($entity, $link);

            foreach ($items as $item) {
                [$foreignType, $key] = $item;

                if ($relationDefs->getForeignEntityType() !== $foreignType) {
                    throw new ImportError('invalid', ["$link:entity_type"]);
                }

                $id = $this->keys->id($foreignType, $key);

                if (!$id) {
                    if ($this->keys->isDeleted($foreignType, $key)) {
                        $deleted[] = $link;
                    } else {
                        $unresolved[] = $link;
                    }

                    continue;
                }

                if ($relation->isRelatedById($id)) {
                    continue;
                }

                if ($write) {
                    $relation->relateById($id, null, [SaveOption::SILENT => true, SaveOption::SKIP_HOOKS => true]);
                }

                $changed[] = "relate.$link";
            }
        }

        return ['changed' => array_values(array_unique($changed)), 'unresolved' => array_values(array_unique($unresolved)),
            'deletedTargets' => array_values(array_unique($deleted))];
    }

    /**
     * @return string[] Preferences keys that differ.
     */
    public function preferencesDiff(string $userId, ?stdClass $preferences): array
    {
        if (!$preferences) {
            return [];
        }

        $stored = $this->entityManager->getEntityById('Preferences', $userId);
        $out = [];

        foreach (get_object_vars($preferences) as $key => $value) {
            $code = $this->validate('Preferences', $key, $value);

            if ($code) {
                throw new ImportError('invalid', ["preferences.$key:$code"]);
            }

            if ($stored?->get($key) !== $value) {
                $out[] = "preferences.$key";
            }
        }

        return $out;
    }

    public function savePreferences(string $userId, stdClass $preferences): void
    {
        $stored = $this->entityManager->getEntityById('Preferences', $userId);

        if (!$stored) {
            return;
        }

        $stored->set(get_object_vars($preferences));
        $this->entityManager->saveEntity($stored);
    }

    private function applyLink(CoreEntity $entity, string $link, mixed $ref, bool $isNew, array &$changed,
        array &$unresolved, array &$deletedTargets): void
    {
        $isParent = (bool) $this->entityManager->getDefs()->getEntity($entity->getEntityType())
            ->tryGetRelation($link)?->isBelongsToParent();

        if (!$entity->hasAttribute($link . 'Id')) {
            throw new ImportError('invalid', ["$link:unknown_link"]);
        }

        $id = null;
        $foreignType = null;

        if ($ref !== null) {
            [$foreignType, $key] = $ref;
            $id = $this->keys->id($foreignType, $key);

            if (!$id) {
                // never cleared by an unresolved reference; a target deleted in EspoCRM is a finding (06.3: finance
                // records deleted in EspoCRM are not restored), anything else unresolved is a problem
                if ($this->keys->isDeleted($foreignType, $key)) {
                    $deletedTargets[] = $link;
                } else {
                    $unresolved[] = $link;
                }

                return;
            }

            if ($isParent) {
                $allowed = $this->metadata->get(['entityDefs', $entity->getEntityType(), 'fields', $link, 'entityList']);

                if (is_array($allowed) && !in_array($foreignType, $allowed, true)) {
                    throw new ImportError('invalid', ["$link:entity_list"]);
                }
            } elseif ($this->entityManager->getDefs()->getEntity($entity->getEntityType())->getRelation($link)
                    ->tryGetForeignEntityType() !== $foreignType) {
                throw new ImportError('invalid', ["$link:entity_type"]); // never an id of another entity type
            }
        }

        $entity->set($link . 'Id', $id);

        if ($isParent) {
            $entity->set($link . 'Type', $foreignType);
        }

        if ($isNew ? $id !== null : ($entity->isAttributeChanged($link . 'Id') ||
            ($isParent && $entity->isAttributeChanged($link . 'Type')))) {
            $changed[] = $link . 'Id';
        }
    }

    /**
     * Items are added (links made in EspoCRM stay); a `domain` is owned: its members not in the items are removed.
     */
    private function applyLinkMultiple(CoreEntity $entity, string $link, stdClass $spec, bool $isNew, array &$changed,
        array &$unresolved, array &$deletedTargets): void
    {
        if (!$entity->hasLinkMultipleField($link)) {
            throw new ImportError('invalid', ["$link:unknown_link"]);
        }

        if (!$isNew) {
            $entity->loadLinkMultipleField($link);
        }

        $current = $isNew ? [] : $entity->getLinkMultipleIdList($link);
        $desired = [];
        $columns = [];

        foreach ($spec->items ?? [] as $item) {
            $id = $this->keys->id($item[0], $item[1]);

            if (!$id) {
                if ($this->keys->isDeleted($item[0], $item[1])) {
                    $deletedTargets[] = $link;
                } else {
                    $unresolved[] = $link;
                }

                continue;
            }

            $desired[] = $id;

            if (isset($item[2])) {
                $columns[$id] = $item[2];
            }
        }

        $domain = [];

        foreach ($spec->domain ?? [] as $item) {
            $id = $this->keys->id($item[0], $item[1]);

            if ($id) {
                $domain[] = $id;
            }
        }

        $final = array_values(array_unique(array_merge(array_diff($current, array_diff($domain, $desired)), $desired)));

        if (!$isNew && $this->sameSet($current, $final)) {
            return;
        }

        if ($isNew && !$final) {
            return;
        }

        $entity->setLinkMultipleIdList($link, $final);

        if ($columns) {
            $data = $entity->get($link . 'Columns') ?? new stdClass();

            foreach ($columns as $id => $value) {
                if (!in_array($id, $current, true)) {
                    $data->$id = $value;
                }
            }

            $entity->set($link . 'Columns', $data);
        }

        $changed[] = $link;
    }

    /**
     * @param stdClass[] $emails
     */
    private function applyEmails(CoreEntity $entity, array $emails, bool $isNew, array &$changed): void
    {
        /** @var EmailAddressRepository $repository */
        $repository = $this->entityManager->getRepository('EmailAddress');
        $current = $isNew ? [] : $repository->getEmailAddressData($entity);
        $flags = [];

        foreach ($current as $row) {
            $flags[strtolower($row->emailAddress)] = $row;
        }

        $key = fn ($row) => strtolower($row->emailAddress) . '|' . (int) !empty($row->primary);

        if (!$isNew && $this->sameSet(array_map($key, $current), array_map($key, $emails))) {
            return;
        }

        if ($isNew && !$emails) {
            return;
        }

        $data = [];

        foreach ($emails as $row) {
            // optOut/invalid live on the shared address row (other records use it too): always kept as they are
            $kept = $flags[strtolower($row->emailAddress)] ?? $repository->getByAddress($row->emailAddress);
            $data[] = (object) ['emailAddress' => $row->emailAddress, 'primary' => !empty($row->primary),
                'optOut' => $this->flag($kept, 'optOut'), 'invalid' => $this->flag($kept, 'invalid')];
        }

        $entity->set('emailAddressData', $data);
        $entity->set('emailAddress', $emails[0]->emailAddress ?? null);
        $this->primaryFlags($entity, 'emailAddress', $data[0] ?? null); // the core takes them for the primary row
        $changed[] = 'emailAddressData';
    }

    /**
     * @param stdClass[] $phones
     */
    private function applyPhones(CoreEntity $entity, array $phones, bool $isNew, array &$changed): void
    {
        /** @var PhoneNumberRepository $repository */
        $repository = $this->entityManager->getRepository('PhoneNumber');
        $current = $isNew ? [] : $repository->getPhoneNumberData($entity);
        $flags = [];

        foreach ($current as $row) {
            $flags[$row->phoneNumber] = $row;
        }

        $key = fn ($row) => $row->phoneNumber . '|' . $row->type . '|' . (int) !empty($row->primary);

        if (!$isNew && $this->sameSet(array_map($key, $current), array_map($key, $phones))) {
            return;
        }

        if ($isNew && !$phones) {
            return;
        }

        $data = [];

        foreach ($phones as $row) {
            $kept = $flags[$row->phoneNumber] ?? $repository->getByNumber($row->phoneNumber);
            $data[] = (object) ['phoneNumber' => $row->phoneNumber, 'type' => $row->type,
                'primary' => !empty($row->primary), 'optOut' => $this->flag($kept, 'optOut'),
                'invalid' => $this->flag($kept, 'invalid')];
        }

        $entity->set('phoneNumberData', $data);
        $entity->set('phoneNumber', $phones[0]->phoneNumber ?? null);
        $this->primaryFlags($entity, 'phoneNumber', $data[0] ?? null);
        $changed[] = 'phoneNumberData';
    }

    /**
     * A secret is compared decrypted and set as plain text only when it differs (the entity's hook encrypts it;
     * setting the same value again would re-encrypt and write).
     */
    private function applySecret(CoreEntity $entity, string $attribute, ?string $plain, array &$changed): void
    {
        if (!$entity->hasAttribute($attribute)) {
            throw new ImportError('invalid', ["secret.$attribute:unknown_attribute"]);
        }

        $stored = $entity->get($attribute);
        $current = ($stored === null || $stored === '') ? null : $this->cipher->decrypt($stored);

        if ($current === $plain) {
            return;
        }

        $entity->set($attribute, $plain);
        $changed[] = "secret.$attribute";
    }

    /**
     * The core's savers take the flags of the primary address/number from `<field>IsOptedOut`/`<field>IsInvalid`
     * (defaults of a new record are false): they must carry the kept flags of the shared row too.
     */
    private function primaryFlags(CoreEntity $entity, string $field, ?stdClass $primary): void
    {
        foreach (['IsOptedOut' => 'optOut', 'IsInvalid' => 'invalid'] as $suffix => $flag) {
            if ($primary && $entity->hasAttribute($field . $suffix)) {
                $entity->set($field . $suffix, $primary->$flag);
            }
        }
    }

    /**
     * A flag of a shared address/number: from this record's data row (stdClass) or the shared entity itself.
     */
    private function flag(mixed $kept, string $name): bool
    {
        if ($kept instanceof \Espo\ORM\Entity) {
            return (bool) $kept->get($name);
        }

        return (bool) ($kept->$name ?? false);
    }

    /**
     * Address fields of an Email (not stored: the repository keeps them as EmailAddress links). The stored list is
     * loaded first; an address list is compared as a set of lower-case addresses, so a re-run does not fight the
     * repository's own order and spelling.
     */
    private function applyEmailAddresses(CoreEntity $entity, string $field, mixed $value, bool $isNew,
        array &$changed): void
    {
        if (!$isNew && !$entity->has($field)) {
            /** @var \Espo\Repositories\Email $repository */
            $repository = $this->entityManager->getRepository('Email');
            /** @var \Espo\Entities\Email $entity */
            match ($field) {
                'from' => $repository->loadFromField($entity),
                'to' => $repository->loadToField($entity),
                'cc' => $repository->loadCcField($entity),
                'bcc' => $repository->loadBccField($entity),
            };
        }

        $normal = static function (mixed $list): array {
            $out = array_filter(array_map(fn ($a) => strtolower(trim($a)), explode(';', (string) $list)));
            sort($out);

            return array_values(array_unique($out));
        };

        if (!$isNew && $normal($entity->get($field)) === $normal($value)) {
            return;
        }

        if ($isNew && $normal($value) === []) {
            return;
        }

        $entity->set($field, $value);
        $changed[] = $field;
    }

    private function isJsonObject(string $entityType, string $attribute): bool
    {
        $defs = $this->entityManager->getDefs()->getEntity($entityType);

        return $defs->hasAttribute($attribute) && $defs->getAttribute($attribute)->getType() === 'jsonObject';
    }

    private function vtigerDataDiffers(mixed $stored, mixed $desired): bool
    {
        return $this->canonical($stored) !== $this->canonical($desired);
    }

    /**
     * @return string[]
     */
    private function vtigerDataKeys(mixed $stored, mixed $desired): array
    {
        $a = is_object($stored) ? get_object_vars($stored) : [];
        $b = is_object($desired) ? get_object_vars($desired) : [];
        $keys = [];

        foreach (array_unique(array_merge(array_keys($a), array_keys($b))) as $key) {
            if ($this->canonical($a[$key] ?? null) !== $this->canonical($b[$key] ?? null)) {
                $keys[] = "vtigerData.$key";
            }
        }

        return $keys ?: ['vtigerData'];
    }

    private function canonical(mixed $value): string
    {
        $sort = function ($v) use (&$sort) {
            if ($v instanceof stdClass || (is_array($v) && !array_is_list($v))) {
                $v = (array) $v;
                ksort($v);

                return array_map($sort, $v);
            }

            return is_array($v) ? array_map($sort, $v) : $v;
        };

        $value = $sort($value);

        return json_encode($value === [] ? null : $value, JSON_UNESCAPED_UNICODE | JSON_PRESERVE_ZERO_FRACTION);
    }

    /**
     * @param string[] $a
     * @param string[] $b
     */
    private function sameSet(array $a, array $b): bool
    {
        sort($a);
        sort($b);

        return array_values(array_unique($a)) === array_values(array_unique($b));
    }

    /**
     * Code of the first problem of a value, or null. Checks existence, writability, types, lengths, enum options
     * (with `optionsReference`), decimal scale and date formats.
     */
    private function validate(string $entityType, string $attribute, mixed $value): ?string
    {
        $defs = $this->entityManager->getDefs()->getEntity($entityType);

        if (in_array($attribute, self::FORBIDDEN, true)) {
            return 'forbidden';
        }

        if (!$defs->hasAttribute($attribute)) {
            return 'unknown_attribute';
        }

        if ($value === null) {
            return null;
        }

        $attr = $defs->getAttribute($attribute);
        $field = $this->metadata->get(['entityDefs', $entityType, 'fields', $attribute]) ?? [];
        $fieldType = $field['type'] ?? null;

        if ($attr->getParam('dbType') === 'decimal') {
            return $this->validDecimal($value, (int) $attr->getParam('scale')) ? null : 'decimal';
        }

        switch ($attr->getType()) {
            case 'varchar':
            case 'text':
                if (!is_string($value)) {
                    return 'type';
                }

                $length = $attr->getLength();

                if ($attr->getType() === 'varchar' && $length && mb_strlen($value) > $length) {
                    return 'max_length';
                }

                break;
            case 'int':
                if (!is_int($value)) {
                    return 'type';
                }

                break;
            case 'bool':
                if (!is_bool($value)) {
                    return 'type';
                }

                break;
            case 'date':
                if (!is_string($value) || !preg_match('/^\d{4}-\d{2}-\d{2}$/', $value)) {
                    return 'date';
                }

                break;
            case 'datetime':
                if (!is_string($value) || !preg_match('/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/', $value)) {
                    return 'datetime';
                }

                break;
            case 'jsonObject':
                if (!$value instanceof stdClass) {
                    return 'type';
                }

                break;
            case 'jsonArray':
                if (!is_array($value)) {
                    return 'type';
                }

                break;
        }

        if (in_array($fieldType, ['enum', 'multiEnum'], true) && !($field['allowCustomOptions'] ?? false)) {
            $options = $this->options($entityType, $attribute);

            foreach ($fieldType === 'enum' ? [$value] : $value as $item) {
                if ($options !== null && !in_array((string) $item, $options, true)) {
                    return 'enum_option';
                }
            }
        }

        return null;
    }

    /**
     * @return ?string[]
     */
    private function options(string $entityType, string $field): ?array
    {
        $defs = $this->metadata->get(['entityDefs', $entityType, 'fields', $field]) ?? [];

        if (!empty($defs['optionsReference'])) {
            [$e, $f] = explode('.', $defs['optionsReference']);

            return $this->options($e, $f);
        }

        if ($entityType === 'Preferences' && $field === 'timeZone') {
            return null; // the list comes from the installation, not the metadata
        }

        return isset($defs['options']) ? array_map('strval', $defs['options']) : null;
    }

    private function validDecimal(mixed $value, int $scale): bool
    {
        if (!is_string($value) || !preg_match('/^-?\d+(\.\d+)?$/', $value)) {
            return false;
        }

        $fraction = explode('.', $value)[1] ?? '';

        return strlen(rtrim($fraction, '0')) <= $scale;
    }
}
