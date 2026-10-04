<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Definition;

use Espo\Modules\Itvolga\Tools\Report\Core\Calculation\ParseError;
use Espo\Modules\Itvolga\Tools\Report\Core\Calculation\Parser;
use Espo\Modules\Itvolga\Tools\Report\Core\Granularity;

/**
 * Checks a stored report definition (the Report attributes) or the parameters of a run against the rules of
 * reports.md §2–§4 and resolves every field through the Schema of the acting user. Every field reference of every
 * section passes through Schema::field(), so a field closed by ACL is refused wherever it is used (D-99).
 */
final class DefinitionParser
{
    public const MAX_COLUMNS = 40;
    public const MAX_SORTING = 5;
    public const MAX_AGGREGATES = 20;
    public const MAX_CALCULATIONS = 10;
    public const MAX_HAVING = 10;
    public const MAX_QUICK_FILTERS = 10;
    public const MAX_FILTER_NODES = 100;
    public const MAX_FILTER_DEPTH = 4;
    public const MAX_LABEL_LENGTH = 150;
    public const MAX_ADVANCED_BYTES = 4096;
    public const MAX_ROWS = 5000;
    public const MAX_GROUPS = 1000;
    private const DIRECTIONS = ['asc', 'desc'];
    private const TOTAL_FUNCTIONS = ['SUM', 'AVG', 'MIN', 'MAX'];
    private const DECIMAL = '/^-?\d{1,20}(\.\d{1,10})?$/';

    private int $filterNodes = 0;

    public function __construct(private readonly Schema $schema) {}

    /**
     * @param array<string, mixed> $a attributes of a Report (JSON parts decoded to arrays)
     */
    public function parse(array $a): Definition
    {
        $type = is_string($a['type'] ?? null) ? ReportType::tryFrom($a['type']) : null;

        if (!$type) {
            throw new DefinitionError('badType', 'type');
        }

        $entityType = $a['entityType'] ?? null;

        if (!is_string($entityType) || !preg_match('/^[A-Z][A-Za-z0-9]{0,99}$/', $entityType)) {
            throw new DefinitionError('badEntityType', 'entityType');
        }

        $this->schema->assertEntity($entityType);

        $columns = $this->columns($a['columns'] ?? [], $type, $entityType);
        $sorting = $this->sorting($a['sorting'] ?? [], $columns);
        $groups = $this->groups($a['groups'] ?? [], $type, $entityType);
        $aggregates = $this->aggregates($a['aggregates'] ?? [], $type, $entityType);
        $groupSort = $this->groupSort($a['groupSort'] ?? null, $type, $aggregates);
        $totals = $this->totals($a['totals'] ?? [], $type, $columns);
        $calculations = $this->calculations($a['calculations'] ?? [], $type, $columns);
        [$filters, $filterFields] = $this->filters($a['filters'] ?? null, $entityType, 'filters');
        $having = $this->having($a['havingFilters'] ?? [], $type, $aggregates);
        $quickFilters = $this->quickFilters($a['quickFilters'] ?? [], $entityType);
        $manyLink = $this->manyLink($columns, $groups, $aggregates, $totals, $calculations);

        $definition = new Definition(
            type: $type,
            entityType: $entityType,
            columns: $columns,
            sorting: $sorting,
            rowLimit: $this->limit($a['rowLimit'] ?? null, self::MAX_ROWS, 'rowLimit'),
            groups: $groups,
            aggregates: $aggregates,
            groupSort: $groupSort,
            groupLimit: $type->isGrouped() ? $this->limit($a['groupLimit'] ?? null, self::MAX_GROUPS, 'groupLimit') :
                null,
            totals: $totals,
            calculations: $calculations,
            filters: $filters,
            filterFields: $filterFields,
            having: $having,
            quickFilters: $quickFilters,
            labels: [],
            manyLink: $manyLink,
        );

        return $definition->withLabels($this->labels($a['labels'] ?? null, $definition));
    }

    /**
     * One-off conditions and quick filter values of a run.
     *
     * @param array<string, mixed> $raw
     * @return array{Definition, RunOptions}
     */
    public function parseRun(Definition $definition, array $raw): array
    {
        if (array_key_exists('filters', $raw) && $raw['filters'] !== null) {
            [$filters, $fields] = $this->filters($raw['filters'], $definition->entityType, 'filters');
            $definition = $definition->withFilters($filters, $fields);
        }

        $offset = $raw['offset'] ?? 0;
        $maxSize = $raw['maxSize'] ?? 50;

        if (!is_int($offset) || $offset < 0 || !is_int($maxSize) || $maxSize < 1 ||
            $maxSize > RunOptions::MAX_PAGE_SIZE) {
            throw new DefinitionError('badPage', 'offset');
        }

        $quick = [];

        foreach ($this->listOf($raw['quickFilters'] ?? [], self::MAX_QUICK_FILTERS, 'quickFilters') as $i => $item) {
            $path = "quickFilters[$i]";
            $field = null;

            foreach ($definition->quickFilters as $candidate) {
                if (is_array($item) && $candidate->ref->toString() === ($item['field'] ?? null)) {
                    $field = $candidate;
                }
            }

            $values = $item['values'] ?? [];

            if ($field === null || !in_array($item['mode'] ?? 'in', ['in', 'notIn'], true) || !is_array($values) ||
                !array_is_list($values) || count($values) > WhereRules::MAX_LIST ||
                !is_bool($item['includeEmpty'] ?? false)) {
                throw new DefinitionError('badQuickFilter', $path);
            }

            // A JSON true/false only for a flag: elsewhere it would compare as 1/0, not as the chosen text.
            $isFlag = $field->family() === FieldInfo::FAMILY_BOOL;

            foreach ($values as $value) {
                if (!(is_string($value) && mb_strlen($value) <= WhereRules::MAX_TEXT || is_int($value) ||
                    is_bool($value) && $isFlag)) {
                    throw new DefinitionError('badQuickFilter', $path);
                }
            }

            $quick[] = new QuickFilterValue($field, $item['mode'] ?? 'in', $values, $item['includeEmpty'] ?? false);
        }

        return [$definition, new RunOptions(
            offset: $offset,
            maxSize: $maxSize,
            quickFilters: array_values(array_filter($quick, fn (QuickFilterValue $q) => !$q->isEmpty())),
            noLimit: ($raw['noLimit'] ?? false) === true,
            withQuickFilterOptions: ($raw['withQuickFilterOptions'] ?? true) !== false,
        )];
    }

    private function field(string $entityType, mixed $value, string $path): FieldInfo
    {
        $ref = FieldRef::parse($value);

        if ($ref === null) {
            throw new DefinitionError('badField', $path);
        }

        $field = $this->schema->field($entityType, $ref);

        if ($field === null) {
            throw new DefinitionError('unknownField', $path, ['field' => $ref->toString()]);
        }

        return $field;
    }

    /**
     * @return list<mixed>
     */
    private function listOf(mixed $value, int $max, string $path): array
    {
        if ($value === null) {
            return [];
        }

        if (!is_array($value) || !array_is_list($value)) {
            throw new DefinitionError('badStructure', $path);
        }

        if (count($value) > $max) {
            throw new DefinitionError('tooMany', $path, ['max' => $max]);
        }

        return $value;
    }

    /**
     * @return list<FieldInfo>
     */
    private function columns(mixed $raw, ReportType $type, string $entityType): array
    {
        $list = $this->listOf($raw, self::MAX_COLUMNS, 'columns');

        if (!$type->hasColumns()) {
            if ($list !== []) {
                throw new DefinitionError('notForType', 'columns');
            }

            return [];
        }

        if ($list === []) {
            throw new DefinitionError('columnsRequired', 'columns');
        }

        $result = [];

        foreach ($list as $i => $value) {
            $field = $this->field($entityType, $value, "columns[$i]");

            if (!$field->canColumn()) {
                throw new DefinitionError('fieldNotForColumn', "columns[$i]", ['field' => $field->ref->toString()]);
            }

            $result[$field->ref->toString()] ??= $field;
        }

        return array_values($result);
    }

    /**
     * @param list<FieldInfo> $columns
     * @return list<array{FieldInfo, string}>
     */
    private function sorting(mixed $raw, array $columns): array
    {
        $result = [];

        foreach ($this->listOf($raw, self::MAX_SORTING, 'sorting') as $i => $item) {
            $column = null;

            foreach ($columns as $candidate) {
                if (is_array($item) && $candidate->ref->toString() === ($item['column'] ?? null)) {
                    $column = $candidate;
                }
            }

            $direction = is_array($item) ? ($item['direction'] ?? 'asc') : null;

            if ($column === null || !in_array($direction, self::DIRECTIONS, true)) {
                throw new DefinitionError('badSorting', "sorting[$i]");
            }

            if (!$column->canSort()) {
                throw new DefinitionError('fieldNotForSorting', "sorting[$i]", ['field' => $column->ref->toString()]);
            }

            $result[$column->ref->toString()] ??= [$column, $direction];
        }

        return array_values($result);
    }

    /**
     * @return list<GroupLevel>
     */
    private function groups(mixed $raw, ReportType $type, string $entityType): array
    {
        $list = $this->listOf($raw, 3, 'groups');
        [$min, $max] = $type->groupLevels();

        if (count($list) < $min || count($list) > $max) {
            throw new DefinitionError($type === ReportType::MATRIX ? 'matrixNeedsTwoGroups' :
                ($max === 0 ? 'notForType' : 'groupsRequired'), 'groups', ['min' => $min, 'max' => $max]);
        }

        $result = [];
        $seen = [];

        foreach ($list as $i => $item) {
            $path = "groups[$i]";

            if (!is_array($item)) {
                throw new DefinitionError('badStructure', $path);
            }

            $field = $this->field($entityType, $item['field'] ?? null, "$path.field");

            if (!$field->canGroup()) {
                throw new DefinitionError('fieldNotForGroup', $path, ['field' => $field->ref->toString()]);
            }

            $granularity = null;

            if ($field->isDate()) {
                $granularity = Granularity::tryFrom((string) ($item['granularity'] ?? 'day'));

                if ($granularity === null) {
                    throw new DefinitionError('badGranularity', "$path.granularity");
                }
            } elseif (($item['granularity'] ?? null) !== null) {
                throw new DefinitionError('badGranularity', "$path.granularity");
            }

            $direction = $item['direction'] ?? 'asc';

            if (!in_array($direction, self::DIRECTIONS, true)) {
                throw new DefinitionError('badDirection', "$path.direction");
            }

            $key = $field->ref->toString() . '/' . ($granularity?->value ?? '');

            if (isset($seen[$key])) {
                throw new DefinitionError('duplicateGroup', $path);
            }

            $seen[$key] = true;
            $result[] = new GroupLevel($field, $granularity, $direction);
        }

        return $result;
    }

    /**
     * @return list<Aggregate>
     */
    private function aggregates(mixed $raw, ReportType $type, string $entityType): array
    {
        $list = $this->listOf($raw, self::MAX_AGGREGATES, 'aggregates');

        if (!$type->isGrouped()) {
            if ($list !== []) {
                throw new DefinitionError('notForType', 'aggregates');
            }

            return [];
        }

        if ($list === []) {
            throw new DefinitionError('aggregatesRequired', 'aggregates');
        }

        $result = [];

        foreach ($list as $i => $item) {
            $path = "aggregates[$i]";
            $function = is_array($item) ? ($item['function'] ?? null) : null;

            if (!in_array($function, Aggregate::FUNCTIONS, true)) {
                throw new DefinitionError('badAggregate', $path);
            }

            $field = null;

            if ($function === 'COUNT') {
                if (($item['field'] ?? null) !== null || ($item['link'] ?? null) !== null) {
                    throw new DefinitionError('badAggregate', $path);
                }
            } else {
                $link = $item['link'] ?? null;
                $name = $item['field'] ?? null;

                if (!is_string($name) || ($link !== null && !is_string($link))) {
                    throw new DefinitionError('badAggregate', $path);
                }

                $field = $this->field($entityType, $link === null ? $name : "$link.$name", $path);

                if (!$field->isNumeric()) {
                    throw new DefinitionError('aggregateNotNumeric', $path, ['field' => $field->ref->toString()]);
                }
            }

            $aggregate = new Aggregate($function, $field);

            if (isset($result[$aggregate->key()])) {
                throw new DefinitionError('duplicateAggregate', $path);
            }

            $result[$aggregate->key()] = $aggregate;
        }

        return array_values($result);
    }

    /**
     * @param list<Aggregate> $aggregates
     * @return ?array{aggregate: Aggregate, direction: string}
     */
    private function groupSort(mixed $raw, ReportType $type, array $aggregates): ?array
    {
        if ($raw === null || $raw === [] || (is_object($raw) && get_object_vars($raw) === [])) {
            return null;
        }

        $raw = (array) $raw;

        if (!$type->isGrouped()) {
            throw new DefinitionError('notForType', 'groupSort');
        }

        foreach ($aggregates as $aggregate) {
            if ($aggregate->key() === ($raw['aggregate'] ?? null) &&
                in_array($raw['direction'] ?? 'desc', self::DIRECTIONS, true)) {
                return ['aggregate' => $aggregate, 'direction' => $raw['direction'] ?? 'desc'];
            }
        }

        throw new DefinitionError('badGroupSort', 'groupSort');
    }

    /**
     * @param list<FieldInfo> $columns
     * @return array<string, list<string>>
     */
    private function totals(mixed $raw, ReportType $type, array $columns): array
    {
        $list = $this->listOf($raw, self::MAX_COLUMNS, 'totals');

        if ($list !== [] && !$type->hasCalculations()) {
            throw new DefinitionError('notForType', 'totals');
        }

        $result = [];

        foreach ($list as $i => $item) {
            $ref = is_array($item) ? ($item['column'] ?? null) : null;
            $column = null;

            foreach ($columns as $candidate) {
                if ($candidate->ref->toString() === $ref) {
                    $column = $candidate;
                }
            }

            if ($column === null || !$column->isNumeric()) {
                throw new DefinitionError('badTotal', "totals[$i]");
            }

            $functions = $this->functions($item['functions'] ?? null, "totals[$i].functions");

            if ($functions !== []) {
                $result[$column->ref->toString()] = $functions;
            }
        }

        return $result;
    }

    /**
     * @return list<string>
     */
    private function functions(mixed $raw, string $path): array
    {
        if (!is_array($raw) || !array_is_list($raw)) {
            throw new DefinitionError('badStructure', $path);
        }

        foreach ($raw as $function) {
            if (!in_array($function, self::TOTAL_FUNCTIONS, true)) {
                throw new DefinitionError('badFunction', $path);
            }
        }

        return array_values(array_intersect(self::TOTAL_FUNCTIONS, $raw));
    }

    /**
     * @param list<FieldInfo> $columns
     * @return list<Calculation>
     */
    private function calculations(mixed $raw, ReportType $type, array $columns): array
    {
        $list = $this->listOf($raw, self::MAX_CALCULATIONS, 'calculations');

        if ($list !== [] && !$type->hasCalculations()) {
            throw new DefinitionError('notForType', 'calculations');
        }

        $numeric = [];

        foreach ($columns as $column) {
            if ($column->isNumeric()) {
                $numeric[$column->ref->toString()] = true;
            }
        }

        $result = [];

        foreach ($list as $i => $item) {
            $path = "calculations[$i]";
            $id = 'k' . ($i + 1);
            $label = is_array($item) ? trim((string) ($item['label'] ?? '')) : '';

            if ($label === '' || mb_strlen($label) > self::MAX_LABEL_LENGTH) {
                throw new DefinitionError('calculationLabelRequired', "$path.label");
            }

            try {
                $expression = Parser::parse((string) ($item['expression'] ?? ''));
            } catch (ParseError $e) {
                throw new DefinitionError('calculation' . ucfirst($e->key), "$path.expression",
                    ['position' => $e->position, 'label' => $label]);
            }

            foreach ($expression->references() as $reference) {
                if (!isset($numeric[$reference])) {
                    throw new DefinitionError('calculationBadReference', "$path.expression",
                        ['position' => $expression->positionOf($reference), 'label' => $label,
                            'reference' => $reference]);
                }
            }

            $result[] = new Calculation($id, $label, $expression, $this->functions($item['functions'] ?? [],
                "$path.functions"));
        }

        return $result;
    }

    /**
     * @return array{array<string, mixed>, array<string, FieldInfo>}
     */
    public function filters(mixed $raw, string $entityType, string $path): array
    {
        $this->filterNodes = 0;
        $fields = [];

        if ($raw === null || $raw === [] || (is_object($raw) && get_object_vars($raw) === [])) {
            return [['type' => 'and', 'items' => []], []];
        }

        $tree = $this->filterNode(json_decode(json_encode($raw), true), $entityType, $path, 1, $fields);

        if (!isset($tree['items'])) {
            throw new DefinitionError('badCondition', $path);
        }

        return [$tree, $fields];
    }

    /**
     * @param array<string, FieldInfo> $fields
     * @return array<string, mixed>
     */
    private function filterNode(mixed $node, string $entityType, string $path, int $depth, array &$fields): array
    {
        if (!is_array($node) || ++$this->filterNodes > self::MAX_FILTER_NODES) {
            throw new DefinitionError($this->filterNodes > self::MAX_FILTER_NODES ? 'tooMany' : 'badCondition',
                $path, ['max' => self::MAX_FILTER_NODES]);
        }

        if (array_key_exists('items', $node)) {
            if (!in_array($node['type'] ?? null, ['and', 'or'], true) || $depth > self::MAX_FILTER_DEPTH ||
                !is_array($node['items']) || !array_is_list($node['items'])) {
                throw new DefinitionError('badCondition', $path);
            }

            $items = [];

            foreach ($node['items'] as $i => $item) {
                $items[] = $this->filterNode($item, $entityType, "$path.items[$i]", $depth + 1, $fields);
            }

            return ['type' => $node['type'], 'items' => $items];
        }

        $field = $this->field($entityType, $node['field'] ?? null, "$path.field");

        if (!$field->canFilter()) {
            throw new DefinitionError('fieldNotForFilter', $path, ['field' => $field->ref->toString()]);
        }

        $where = WhereRules::normalize($node['where'] ?? null, $field, "$path.where");
        $this->checkCompare($where, $entityType, $field, $path);
        $fields[$field->ref->toString()] = $field;
        $result = ['field' => $field->ref->toString(), 'where' => $where];

        if (isset($node['advanced'])) {
            $advanced = json_encode($node['advanced']);

            if (!is_array($node['advanced']) || $advanced === false || strlen($advanced) > self::MAX_ADVANCED_BYTES) {
                throw new DefinitionError('badCondition', "$path.advanced");
            }

            $result['advanced'] = $node['advanced'];
        }

        return $result;
    }

    /**
     * @param array<string, mixed> $where
     */
    private function checkCompare(array $where, string $entityType, FieldInfo $field, string $path): void
    {
        if (($where['type'] ?? null) === 'compareField') {
            $other = $this->field($entityType, $where['value']['field'], "$path.where.value.field");

            if ($other->linkKind !== FieldInfo::LINK_NONE || !$other->isDate() ||
                $other->family() !== $field->family()) {
                throw new DefinitionError('badCompareField', $path);
            }
        }

        if (!in_array($where['type'] ?? null, ['and', 'or'], true)) {
            return;
        }

        foreach ($where['value'] as $i => $sub) {
            $this->checkCompare($sub, $entityType, $field, "$path.where.value[$i]");
        }
    }

    /**
     * @param list<Aggregate> $aggregates
     * @return list<Having>
     */
    private function having(mixed $raw, ReportType $type, array $aggregates): array
    {
        $list = $this->listOf($raw, self::MAX_HAVING, 'havingFilters');

        if ($list !== [] && !$type->isGrouped()) {
            throw new DefinitionError('notForType', 'havingFilters');
        }

        $byKey = [];

        foreach ($aggregates as $aggregate) {
            $byKey[$aggregate->key()] = $aggregate;
        }

        $result = [];

        foreach ($list as $i => $item) {
            $path = "havingFilters[$i]";
            $aggregate = is_array($item) ? ($byKey[$item['aggregate'] ?? ''] ?? null) : null;
            $operator = is_array($item) ? ($item['operator'] ?? null) : null;
            $value = is_array($item) ? ($item['value'] ?? null) : null;

            if ($aggregate === null || !in_array($operator, Having::OPERATORS, true)) {
                throw new DefinitionError('badHaving', $path);
            }

            $valid = $operator === 'between' ?
                is_array($value) && array_is_list($value) && count($value) === 2 &&
                    is_string($value[0]) && is_string($value[1]) &&
                    preg_match(self::DECIMAL, $value[0]) && preg_match(self::DECIMAL, $value[1]) :
                (is_string($value) && preg_match(self::DECIMAL, $value));

            if (!$valid) {
                throw new DefinitionError('badHavingValue', $path);
            }

            $result[] = new Having($aggregate, $operator, $value);
        }

        return $result;
    }

    /**
     * @return list<FieldInfo>
     */
    private function quickFilters(mixed $raw, string $entityType): array
    {
        $result = [];

        foreach ($this->listOf($raw, self::MAX_QUICK_FILTERS, 'quickFilters') as $i => $value) {
            $field = $this->field($entityType, $value, "quickFilters[$i]");

            if (!$field->canQuickFilter()) {
                throw new DefinitionError('fieldNotForQuickFilter', "quickFilters[$i]",
                    ['field' => $field->ref->toString()]);
            }

            $result[$field->ref->toString()] ??= $field;
        }

        return array_values($result);
    }

    private function limit(mixed $value, int $max, string $path): ?int
    {
        if ($value === null) {
            return null;
        }

        if (!is_int($value) || $value < 1 || $value > $max) {
            throw new DefinitionError('badLimit', $path, ['max' => $max]);
        }

        return $value;
    }

    /**
     * Result keys a label may override: "c:<column>", "g:<level 1..3>", "a:<aggregate key>", "k:<calculation id>".
     * Labels of parts that no longer exist are dropped; an empty label restores the standard one.
     *
     * @return array<string, string>
     */
    private function labels(mixed $raw, Definition $definition): array
    {
        if ($raw === null) {
            return [];
        }

        $raw = json_decode(json_encode($raw), true);

        if (!is_array($raw)) {
            throw new DefinitionError('badStructure', 'labels');
        }

        $keys = [];

        foreach ($definition->columns as $column) {
            $keys['c:' . $column->ref->toString()] = true;
        }

        foreach (array_keys($definition->groups) as $i) {
            $keys['g:' . ($i + 1)] = true;
        }

        foreach ($definition->aggregates as $aggregate) {
            $keys['a:' . $aggregate->key()] = true;
        }

        foreach ($definition->calculations as $calculation) {
            $keys['k:' . $calculation->id] = true;
        }

        $result = [];

        foreach ($raw as $key => $label) {
            if (!is_string($label) || mb_strlen($label) > self::MAX_LABEL_LENGTH) {
                throw new DefinitionError('badLabel', "labels.$key", ['max' => self::MAX_LABEL_LENGTH]);
            }

            if (isset($keys[$key]) && trim($label) !== '') {
                $result[(string) $key] = trim($label);
            }
        }

        return $result;
    }

    /**
     * The single to-many link a report may join (D-90) and the aggregates it forbids: with rows of the main entity
     * repeated per related record, SUM/AVG/MIN/MAX (and totals) of main or to-one fields would be inflated.
     *
     * @param list<FieldInfo> $columns
     * @param list<GroupLevel> $groups
     * @param list<Aggregate> $aggregates
     * @param array<string, list<string>> $totals
     * @param list<Calculation> $calculations
     */
    private function manyLink(array $columns, array $groups, array $aggregates, array $totals,
        array $calculations): ?string
    {
        $fields = [...$columns, ...array_map(fn (GroupLevel $g) => $g->field, $groups),
            ...array_filter(array_map(fn (Aggregate $a) => $a->field, $aggregates))];
        $links = [];

        foreach ($fields as $field) {
            if ($field->linkKind === FieldInfo::LINK_MANY) {
                $links[(string) $field->ref->link] = true;
            }
        }

        if (count($links) > 1) {
            throw new DefinitionError('oneManyLink', 'columns', ['links' => implode(', ', array_keys($links))]);
        }

        $link = array_key_first($links);

        if ($link === null) {
            return null;
        }

        foreach ($aggregates as $i => $aggregate) {
            if ($aggregate->field !== null && $aggregate->field->ref->link !== $link) {
                throw new DefinitionError('aggregateMultiplied', "aggregates[$i]",
                    ['field' => $aggregate->field->ref->toString(), 'link' => $link]);
            }
        }

        foreach (array_keys($totals) as $ref) {
            if (!str_starts_with($ref, "$link.")) {
                throw new DefinitionError('aggregateMultiplied', 'totals', ['field' => $ref, 'link' => $link]);
            }
        }

        foreach ($calculations as $i => $calculation) {
            foreach ($calculation->functions === [] ? [] : $calculation->expression->references() as $ref) {
                if (!str_starts_with($ref, "$link.")) {
                    throw new DefinitionError('aggregateMultiplied', "calculations[$i]",
                        ['field' => $ref, 'link' => $link]);
                }
            }
        }

        return $link;
    }
}
