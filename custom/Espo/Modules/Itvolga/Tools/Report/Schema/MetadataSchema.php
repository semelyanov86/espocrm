<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Schema;

use Espo\Core\Acl;
use Espo\Core\Acl\Table;
use Espo\Core\Utils\FieldUtil;
use Espo\Core\Utils\Metadata;
use Espo\Entities\User;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\DefinitionError;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\FieldForbidden;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\FieldInfo;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\FieldRef;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\Schema;
use Espo\ORM\Defs;
use Espo\ORM\Defs\RelationDefs;
use Espo\ORM\Type\RelationType;

/**
 * The model as one user may use it in reports (D-99): entities of `scopes.*.entity && object` or flagged
 * `itvolgaReports: true` (`"admin"` — administrators only, `false` — never), readable by the user's ACL; fields of the
 * main entity and of an entity one link away (belongsTo, hasMany, hasChildren, manyMany), without technical fields
 * (disabled, utility, not stored — except values the ORM selects itself on the main entity —, passwords, JSON). A field,
 * link or foreign entity closed by ACL is FieldForbidden (403), never dropped silently.
 */
final class MetadataSchema implements Schema
{
    /** Field types never used in reports. */
    private const EXCLUDED_TYPES = ['password', 'jsonArray', 'jsonObject', 'map', 'attachmentMultiple', 'address',
        'currencyConverted', 'foreign', 'linkOne', 'file', 'image', 'barcode', 'wysiwyg'];

    /** @var array<string, string> */
    private array $entityStatus = [];

    public function __construct(
        private readonly User $user,
        private readonly Acl $acl,
        private readonly Metadata $metadata,
        private readonly Defs $defs,
        private readonly FieldUtil $fieldUtil,
    ) {}

    /**
     * Entity types the user may build reports on.
     *
     * @return list<string>
     */
    public function entityList(): array
    {
        $list = [];

        foreach (array_keys($this->metadata->get(['scopes']) ?? []) as $entityType) {
            if ($this->status($entityType) === 'ok') {
                $list[] = $entityType;
            }
        }

        sort($list);

        return $list;
    }

    public function assertEntity(string $entityType): void
    {
        $status = $this->status($entityType);

        if ($status === 'unknown') {
            throw new DefinitionError('badEntityType', 'entityType');
        }

        if ($status !== 'ok') {
            throw new FieldForbidden('entityForbidden', 'entityType', ['entityType' => $entityType]);
        }
    }

    public function field(string $entityType, FieldRef $ref): ?FieldInfo
    {
        $owner = $entityType;
        $kind = FieldInfo::LINK_NONE;

        if ($ref->link !== null) {
            $resolved = $this->link($entityType, $ref->link);

            if ($resolved === null) {
                return null;
            }

            [$owner, $kind] = $resolved;
        }

        $defs = $this->metadata->get(['entityDefs', $owner, 'fields', $ref->field]);

        if (!is_array($defs) || !$this->isUsable($owner, $ref->field, $defs, $kind === FieldInfo::LINK_NONE)) {
            return null;
        }

        if (!$this->acl->checkField($owner, $ref->field) ||
            array_intersect($this->fieldUtil->getAttributeList($owner, $ref->field),
                $this->acl->getScopeForbiddenAttributeList($owner)) !== []) {
            throw new FieldForbidden('fieldForbidden', '', ['field' => $ref->toString()]);
        }

        $type = (string) $defs['type'];
        $foreign = null;

        if (in_array($type, ['link', 'linkMultiple'], true)) {
            $foreign = $this->metadata->get(['entityDefs', $owner, 'links', $ref->field, 'entity']);

            if (!is_string($foreign)) {
                return null;
            }
        }

        $attributes = match ($type) {
            'link' => [$ref->field . 'Id'],
            'linkMultiple' => [$ref->field],
            'linkParent' => [$ref->field . 'Id', $ref->field . 'Type'],
            default => [$ref->field],
        };

        return new FieldInfo($ref, $type, $owner, $kind, $foreign, $attributes,
            array_values(array_map('strval', $defs['options'] ?? [])));
    }

    /**
     * @return ?array{string, string} foreign entity type and link kind
     */
    private function link(string $entityType, string $link): ?array
    {
        $entityDefs = $this->defs->getEntity($entityType);

        if (!$entityDefs->hasRelation($link)) {
            return null;
        }

        $relation = $entityDefs->getRelation($link);
        $kind = self::linkKind($relation);
        $foreign = $relation->tryGetForeignEntityType();
        $linkDefs = $this->metadata->get(['entityDefs', $entityType, 'links', $link]);

        if ($kind === null || $foreign === null || !is_array($linkDefs) || !empty($linkDefs['disabled']) ||
            !empty($linkDefs['utility'])) {
            return null;
        }

        $status = $this->status($foreign);

        if ($status === 'unknown') {
            return null;
        }

        $linkField = $this->metadata->get(['entityDefs', $entityType, 'fields', $link]);

        // An admin-only main entity (User, Team) is still a readable link target for whoever reads its scope.
        if (in_array($link, $this->acl->getScopeForbiddenLinkList($entityType), true) ||
            (is_array($linkField) && !$this->acl->checkField($entityType, $link)) ||
            $status === 'forbidden' || !$this->acl->checkScope($foreign, Table::ACTION_READ)) {
            throw new FieldForbidden('linkForbidden', '', ['link' => $link]);
        }

        return [$foreign, $kind];
    }

    public static function linkKind(RelationDefs $relation): ?string
    {
        return match ($relation->getType()) {
            RelationType::BELONGS_TO => FieldInfo::LINK_ONE,
            RelationType::HAS_MANY, RelationType::MANY_MANY, RelationType::HAS_CHILDREN => FieldInfo::LINK_MANY,
            default => null,
        };
    }

    /**
     * @param array<string, mixed> $defs
     */
    private function isUsable(string $entityType, string $field, array $defs, bool $isMain): bool
    {
        $type = $defs['type'] ?? null;

        if (!is_string($type) || in_array($type, self::EXCLUDED_TYPES, true) || !empty($defs['disabled']) ||
            !empty($defs['utility']) || !empty($defs['directAccessDisabled']) ||
            (!$isMain && in_array($type, ['personName', 'email', 'phone', 'linkMultiple', 'linkParent'], true)) ||
            ($defs['view'] ?? null) === 'views/fields/currency-list') {
            // The currency code of a money field is shown with its amount, not as a field of its own.
            return false;
        }

        $entityDefs = $this->defs->getEntity($entityType);

        // E-mail and phone carry extra non-stored attributes (data, opt-out flags); a report shows the primary value.
        $attributes = in_array($type, ['email', 'phone'], true) ? [$field] :
            $this->fieldUtil->getActualAttributeList($entityType, $field);

        foreach ($attributes as $attribute) {
            if (!$entityDefs->hasAttribute($attribute)) {
                return false;
            }

            $attributeDefs = $entityDefs->getAttribute($attribute);

            if ($type === 'linkMultiple') {
                continue;
            }

            // A value the ORM computes (person name, primary e-mail) is selectable on the main entity only: a joined
            // related entity offers plain columns.
            if ($attributeDefs->isNotStorable() && ($isMain ? $attributeDefs->getParam('select') === null : true)) {
                return false;
            }
        }

        return true;
    }

    /**
     * ok | adminOnly | forbidden | unknown
     */
    private function status(string $entityType): string
    {
        if (isset($this->entityStatus[$entityType])) {
            return $this->entityStatus[$entityType];
        }

        $scope = $this->metadata->get(['scopes', $entityType]);
        $flag = is_array($scope) ? ($scope['itvolgaReports'] ?? null) : null;
        $status = 'ok';

        if (!is_array($scope) || empty($scope['entity']) || !empty($scope['disabled']) || $flag === false ||
            (empty($scope['object']) && $flag === null) || !$this->defs->hasEntity($entityType)) {
            $status = 'unknown';
        } elseif ($flag === 'admin' && !$this->user->isAdmin()) {
            $status = 'adminOnly';
        } elseif (!$this->acl->checkScope($entityType, Table::ACTION_READ)) {
            $status = 'forbidden';
        }

        return $this->entityStatus[$entityType] = $status;
    }
}
