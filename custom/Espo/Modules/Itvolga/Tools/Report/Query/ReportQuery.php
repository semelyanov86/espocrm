<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Query;

use Espo\Core\Select\SelectBuilderFactory;
use Espo\Core\Select\Where\Item;
use Espo\Entities\User;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\Aggregate;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\Definition;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\FieldInfo;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\GroupLevel;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\QuickFilterValue;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\RunOptions;
use Espo\Modules\Itvolga\Tools\Report\Core\Filter\RunContext;
use Espo\Modules\Itvolga\Tools\Report\Core\Filter\WhereTranslator;
use Espo\Modules\Itvolga\Tools\Report\Core\Granularity;
use Espo\ORM\Defs;
use Espo\ORM\Query\Part\WhereClause;
use Espo\ORM\Query\Select;
use Espo\ORM\Query\SelectBuilder as OrmSelectBuilder;
use Espo\ORM\Type\RelationType;
use LogicException;

/**
 * The SQL side of one report run (reports.md §5), built only through the core select builder and the ORM:
 *
 *  - eligible(): ids of the main records the user may read and the conditions select — the core strict select builder
 *    with the translated where tree (its checker and converter check every attribute against the field ACL);
 *  - base(): a plain ORM query of the main entity restricted to those ids, so the access filters of the core (their
 *    joins, DISTINCT) never mix with the report's grouping; related entities are LEFT JOINed by entity type with
 *    `deleted = 0` and the ids the user may read in the ON clause (D-89): a hidden related record looks like none;
 *    a many-to-many link restricts the middle table too, so hidden targets add no rows;
 *  - expressions of values, group keys and aggregates — composed only from checked field names.
 */
final class ReportQuery
{
    /** @var array<string, string> link → alias */
    private array $aliases = [];
    private ?Select $eligible = null;

    public function __construct(
        public readonly Definition $definition,
        public readonly RunOptions $options,
        public readonly User $user,
        public readonly RunContext $context,
        private readonly SelectBuilderFactory $selectBuilderFactory,
        private readonly Defs $defs,
    ) {
        foreach ($this->usedFields() as $field) {
            if ($field->ref->link !== null) {
                $this->aliases[$field->ref->link] = 'j' . ucfirst($field->ref->link);
            }
        }
    }

    /**
     * @return list<FieldInfo>
     */
    private function usedFields(): array
    {
        $definition = $this->definition;

        return [
            ...$definition->columns,
            ...array_map(fn (GroupLevel $g) => $g->field, $definition->groups),
            ...array_values(array_filter(array_map(fn (Aggregate $a) => $a->field, $definition->aggregates))),
            ...$definition->quickFilters,
            ...array_filter([$definition->dashboard->filterField]),
        ];
    }

    public function eligible(): Select
    {
        if ($this->eligible) {
            return $this->eligible;
        }

        $builder = $this->selectBuilderFactory
            ->create()
            ->from($this->definition->entityType)
            ->forUser($this->user)
            ->withStrictAccessControl();

        $where = WhereTranslator::translate($this->definition->filters, $this->definition->filterFields,
            $this->context);

        if ($where !== null) {
            $builder->withWhere(Item::fromRaw($where));
        }

        return $this->eligible = $builder->buildQueryBuilder()->select(['id'])->order([])->build();
    }

    /**
     * The main records of the report with the joins of the related fields and the quick filters of the run.
     *
     * @param ?list<QuickFilterValue> $quickFilters null = those of the run options
     */
    public function base(?array $quickFilters = null): OrmSelectBuilder
    {
        $builder = OrmSelectBuilder::create()
            ->from($this->definition->entityType)
            ->where(['id=s' => $this->eligible()]);

        foreach ($this->aliases as $link => $alias) {
            $this->join($builder, $link, $alias);
        }

        foreach ($quickFilters ?? $this->options->quickFilters as $quick) {
            $builder->where($this->quickFilter($quick));
        }

        return $builder;
    }

    private function join(OrmSelectBuilder $builder, string $link, string $alias): void
    {
        $main = $this->definition->entityType;
        $relation = $this->defs->getEntity($main)->getRelation($link);
        $foreign = $relation->getForeignEntityType();
        // Administrators too: mandatory filters hide records even from them (system and super-admin users).
        $readable = $this->selectBuilderFactory
            ->create()
            ->from($foreign)
            ->forUser($this->user)
            ->withAccessControlFilter()
            ->buildQueryBuilder()
            ->select(['id'])
            ->order([])
            ->build();
        $conditions = ["$alias.deleted" => false];

        switch ($relation->getType()) {
            case RelationType::BELONGS_TO:
                $conditions["$alias.id:"] = $relation->getKey();

                break;

            case RelationType::HAS_MANY:
                $conditions["$alias." . $relation->getForeignKey() . ':'] = 'id';

                break;

            case RelationType::HAS_CHILDREN:
                $conditions["$alias." . $relation->getForeignKey() . ':'] = 'id';
                $conditions["$alias." . ($relation->getParam('foreignType') ?? 'parentType')] = $main;

                break;

            case RelationType::MANY_MANY:
                $middle = $alias . 'Middle';
                $middleConditions = [
                    "$middle." . $relation->getMidKey() . ':' => 'id',
                    "$middle.deleted" => false,
                ];

                foreach ($relation->getConditions() as $key => $value) {
                    $middleConditions["$middle.$key"] = $value;
                }

                $middleConditions["$middle." . $relation->getForeignMidKey() . '=s'] = $readable;

                $builder->leftJoin(ucfirst($relation->getRelationshipName()), $middle, $middleConditions);
                $conditions["$alias.id:"] = "$middle." . $relation->getForeignMidKey();

                break;

            default:
                throw new LogicException("Link '$link' cannot be joined.");
        }

        $conditions["$alias.id=s"] = $readable;
        $builder->leftJoin($foreign, $alias, $conditions);
    }

    /**
     * ORM expression of an attribute of a field: of the main entity, or of the joined related entity.
     */
    public function attribute(FieldInfo $field, string $attribute): string
    {
        if ($field->ref->link === null) {
            return $attribute;
        }

        $alias = $this->aliases[$field->ref->link] ?? throw new LogicException('Link not joined.');

        return "$alias.$attribute";
    }

    /**
     * Attributes whose values show the field: id (and type) of a link, amount and currency of money, else the field.
     *
     * @return array<string, string> role → ORM expression (roles: value, currency, type)
     */
    public function valueExpressions(FieldInfo $field): array
    {
        $name = $field->ref->field;

        return match ($field->type) {
            'link' => ['value' => $this->attribute($field, $name . 'Id')],
            'linkParent' => ['value' => $this->attribute($field, $name . 'Id'),
                'type' => $this->attribute($field, $name . 'Type')],
            'currency' => ['value' => $this->attribute($field, $name),
                'currency' => $this->attribute($field, $name . 'Currency')],
            // A date-only value keeps its calendar date apart; the moment column holds the start of the day or, for
            // an end, of the next one in the system time zone (external review B14).
            'datetimeOptional' => ['value' => $this->attribute($field, $name),
                'date' => $this->attribute($field, $name . 'Date')],
            default => ['value' => $this->attribute($field, $name)],
        };
    }

    /**
     * Group key expression (D-89): the value, or the period of a date in the run's time zone for date-time fields:
     * day 'YYYY-MM-DD', week 'YYYY/W' (ISO), month 'YYYY-MM', quarter 'YYYY_Q', half-year 'YYYY_H', year.
     */
    public function groupExpression(GroupLevel $group): string
    {
        $values = $this->valueExpressions($group->field);
        $value = $values['value'];

        if ($group->granularity === null) {
            // A text '' and NULL are one empty group, as in drill-down and quick filters.
            return in_array($group->field->family(), [FieldInfo::FAMILY_TEXT, FieldInfo::FAMILY_ENUM], true) ?
                "NULLIF:($value, '')" : $value;
        }

        if ($group->field->family() === FieldInfo::FAMILY_DATETIME) {
            $value = "TZ:($value, {$this->context->offsetHours()})";

            if (isset($values['date'])) {
                $value = "IF:(IS_NOT_NULL:({$values['date']}), {$values['date']}, $value)";
            }
        }

        return match ($group->granularity) {
            Granularity::DAY => "DAY:($value)",
            Granularity::WEEK => "WEEK_1:($value)",
            Granularity::MONTH => "MONTH:($value)",
            Granularity::QUARTER => "QUARTER:($value)",
            Granularity::HALF_YEAR =>
                "CONCAT:(YEAR:($value), '_', IF:(LESS_THAN_OR_EQUAL:(MONTH_NUMBER:($value), 6), '1', '2'))",
            Granularity::YEAR => "YEAR:($value)",
        };
    }

    /**
     * Collation token of a text group key (ITVOLGA_GROUP_TOKEN, external review B8), or null when the key compares as
     * SQL returns it (numbers, dates, periods, ids).
     */
    public function groupToken(GroupLevel $group): ?string
    {
        if ($group->granularity !== null ||
            !in_array($group->field->family(), [FieldInfo::FAMILY_TEXT, FieldInfo::FAMILY_ENUM], true)) {
            return null;
        }

        return 'ITVOLGA_GROUP_TOKEN:(' . $this->groupExpression($group) . ')';
    }

    /**
     * Aggregate expressions: COUNT is the number of distinct main records (D-90); a money aggregate also gives the
     * lowest and highest currency of its values, so mixed currencies are detected (D-94).
     *
     * @return array<string, string> role → expression (value, currencyMin, currencyMax)
     */
    public function aggregateExpressions(Aggregate $aggregate): array
    {
        if ($aggregate->field === null) {
            return ['value' => 'ITVOLGA_COUNT_DISTINCT:(id)'];
        }

        $values = $this->valueExpressions($aggregate->field);
        $result = ['value' => "{$aggregate->function}:({$values['value']})"];

        if (isset($values['currency'])) {
            $result['currencyMin'] = "MIN:({$values['currency']})";
            $result['currencyMax'] = "MAX:({$values['currency']})";
        }

        return $result;
    }

    /**
     * Condition of a quick filter (D-97): the shown value of the field — a hidden or missing related record counts as
     * empty, like in the result; a text value '' is empty too.
     *
     * @return WhereClause
     */
    public function quickFilter(QuickFilterValue $quick): WhereClause
    {
        $expression = $this->valueExpressions($quick->field)['value'];
        $isText = in_array($quick->field->family(), [FieldInfo::FAMILY_TEXT, FieldInfo::FAMILY_ENUM], true);
        $empty = $isText ? ['OR' => [[$expression => null], [$expression => '']]] : [$expression => null];
        $notEmpty = $isText ? ['AND' => [[$expression . '!=' => null], [$expression . '!=' => '']]] :
            [$expression . '!=' => null];
        $values = $quick->field->family() === FieldInfo::FAMILY_BOOL ?
            array_map(fn ($v) => $v === true || $v === 'true' || $v === 1 || $v === '1', $quick->values) :
            $quick->values;

        if ($quick->mode === 'in') {
            $or = [];

            if ($values !== []) {
                $or[] = ['AND' => [$notEmpty, [$expression => $values]]];
            }

            if ($quick->includeEmpty) {
                $or[] = $empty;
            }

            return WhereClause::fromRaw(['OR' => $or]);
        }

        $or = [['AND' => [$notEmpty, ...($values !== [] ? [[$expression . '!=' => $values]] : [])]]];

        if (!$quick->includeEmpty) {
            $or[] = $empty;
        }

        return WhereClause::fromRaw(['OR' => $or]);
    }
}
