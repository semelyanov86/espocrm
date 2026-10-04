<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Classes\Select\Where;

use Espo\Core\AclManager;
use Espo\Core\Exceptions\BadRequest;
use Espo\Core\Exceptions\Forbidden;
use Espo\Core\Select\Where\Item;
use Espo\Core\Select\Where\ItemConverter;
use Espo\Core\Utils\Metadata;
use Espo\Entities\User;
use Espo\ORM\Query\Part\Condition as Cond;
use Espo\ORM\Query\Part\Expression as Expr;
use Espo\ORM\Query\Part\WhereItem;
use Espo\ORM\Query\SelectBuilder;

/**
 * Where item `itvolgaFieldCompare` (reports): compares two date (or two date-time) fields of the same record, e.g.
 * "due date before invoice date". An empty field makes the record not match. Both fields must be readable by the user
 * and shown to users (utility attributes such as dateStartDate are refused).
 *
 *   {"type": "itvolgaFieldCompare", "attribute": "dateDue", "value": {"operator": "lessThan", "attribute": "dateInvoiced"}}
 */
class FieldCompare implements ItemConverter
{
    private const OPERATORS = ['equals', 'notEquals', 'lessThan', 'greaterThan', 'lessThanOrEquals',
        'greaterThanOrEquals'];

    public function __construct(
        private string $entityType,
        private User $user,
        private AclManager $aclManager,
        private Metadata $metadata,
    ) {}

    public function convert(SelectBuilder $queryBuilder, Item $item): WhereItem
    {
        $left = (string) $item->getAttribute();
        $value = $item->getValue();
        $operator = is_array($value) ? ($value['operator'] ?? null) : null;
        $right = is_array($value) ? ($value['attribute'] ?? null) : null;

        if (!in_array($operator, self::OPERATORS, true) || !is_string($right)) {
            throw new BadRequest('Bad itvolgaFieldCompare where item.');
        }

        $leftDefs = $this->fieldDefs($left);
        $rightDefs = $this->fieldDefs($right);
        $dateTypes = [['date'], ['datetime', 'datetimeOptional']];
        $sameKind = false;

        foreach ($dateTypes as $kind) {
            $sameKind = $sameKind ||
                in_array($leftDefs['type'] ?? null, $kind, true) && in_array($rightDefs['type'] ?? null, $kind, true);
        }

        if (!$sameKind) {
            throw new BadRequest('itvolgaFieldCompare needs two date or two date-time fields.');
        }

        $acl = $this->aclManager->createUserAcl($this->user);
        $forbiddenFields = $acl->getScopeForbiddenFieldList($this->entityType);
        // An attribute of a closed field (dateStartDate of dateStart) is in the attribute list only.
        $forbiddenAttributes = $acl->getScopeForbiddenAttributeList($this->entityType);

        foreach ([$left, $right] as $field) {
            if (in_array($field, $forbiddenFields, true) || in_array($field, $forbiddenAttributes, true)) {
                throw new Forbidden('Forbidden field in itvolgaFieldCompare.');
            }
        }

        $a = Expr::column($left);
        $b = Expr::column($right);

        return match ($operator) {
            'equals' => Cond::equal($a, $b),
            'notEquals' => Cond::notEqual($a, $b),
            'lessThan' => Cond::less($a, $b),
            'greaterThan' => Cond::greater($a, $b),
            'lessThanOrEquals' => Cond::lessOrEqual($a, $b),
            'greaterThanOrEquals' => Cond::greaterOrEqual($a, $b),
        };
    }

    /**
     * Definition of a field a report may show; utility, disabled and not-storable fields compare as nothing.
     *
     * @return array<string, mixed>
     */
    private function fieldDefs(string $field): array
    {
        $defs = $this->metadata->get(['entityDefs', $this->entityType, 'fields', $field]);

        if (!is_array($defs) || ($defs['utility'] ?? false) || ($defs['disabled'] ?? false) ||
            ($defs['notStorable'] ?? false)) {
            return [];
        }

        return $defs;
    }
}
