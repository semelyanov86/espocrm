<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Run;

use Closure;
use Espo\Modules\Itvolga\Tools\Finance\Decimal;
use Espo\Modules\Itvolga\Tools\Report\Core\DecimalMath;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\Aggregate;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\FieldInfo;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\GroupLevel;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\Having;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\ReportType;
use Espo\Modules\Itvolga\Tools\Report\Core\Format\RawNumber;
use Espo\Modules\Itvolga\Tools\Report\Core\Result\KeyOrder;
use Espo\Modules\Itvolga\Tools\Report\Format\ValueFormatter;
use Espo\Modules\Itvolga\Tools\Report\Query\ReportQuery;
use Espo\ORM\Query\Part\Expression as Expr;
use Espo\ORM\Query\Part\Order;
use Espo\ORM\Query\Part\WhereClause;
use Espo\ORM\Query\Select;
use Espo\ORM\Query\SelectBuilder;

/**
 * Executes the queries of one report type and assembles the result (reports.md §5–§6):
 *
 *  - tabular: a page of rows within the row limit, totals of numeric columns over ALL filtered rows (SQL, D-96),
 *    custom calculations per row and their totals over the rows up to the cap;
 *  - grouped (summaries, summariesWithDetails): one SQL query per level, so every aggregate is exact (COUNT DISTINCT,
 *    weighted AVG); HAVING, the group order and the group limit apply to level 1; lower levels, detail rows and the
 *    grand total are restricted to the shown level-1 groups (D-91);
 *  - matrix: rows = level 1 (as above), columns = values of level 2 (capped), cells, row and column totals and the
 *    grand total each from their own query.
 */
final class Assembler
{
    /**
     * @param Closure(Select): list<array<string, mixed>> $fetch
     */
    public function __construct(
        private readonly ReportQuery $query,
        private readonly ValueFormatter $formatter,
        private readonly Labels $labels,
        private readonly KeyOrder $order,
        private readonly int $maxRows,
        private readonly Closure $fetch,
    ) {}

    /**
     * @return list<array<string, mixed>>
     */
    private function fetch(SelectBuilder $builder): array
    {
        return ($this->fetch)($builder->build());
    }

    /**
     * Rows of a query bounded by the cap (D-95): one row more is asked for to detect the overflow, which is cut and
     * reported in the limits.
     *
     * @param array<string, mixed> $limits
     * @return list<array<string, mixed>>
     */
    private function fetchCapped(SelectBuilder $builder, int $cap, array &$limits): array
    {
        $rows = $this->fetch($builder->limit(0, $cap + 1));

        if (count($rows) > $cap) {
            $limits['capHit'] = true;
            $rows = array_slice($rows, 0, $cap);
        }

        return $rows;
    }

    /**
     * @return list<array{string, string}>
     */
    private function selectField(FieldInfo $field, string $prefix): array
    {
        $result = [];

        foreach ($this->query->valueExpressions($field) as $role => $expression) {
            $result[] = [$expression, $prefix . $role[0]];
        }

        return $result;
    }

    /**
     * @param array<string, mixed> $row
     * @return array<string, mixed>
     */
    private static function readField(array $row, string $prefix): array
    {
        return ['value' => $row[$prefix . 'v'] ?? null, 'currency' => $row[$prefix . 'c'] ?? null,
            'type' => $row[$prefix . 't'] ?? null, 'date' => $row[$prefix . 'd'] ?? null];
    }

    /**
     * @return list<array{string, string}>
     */
    private function selectAggregates(): array
    {
        $result = [['ITVOLGA_COUNT_DISTINCT:(id)', 'n']];

        foreach ($this->query->definition->aggregates as $i => $aggregate) {
            foreach ($this->query->aggregateExpressions($aggregate) as $role => $expression) {
                $result[] = [$expression, "a{$i}" . ($role === 'value' ? '' : $role)];
            }
        }

        return $result;
    }

    /**
     * @param array<string, mixed> $row
     * @return list<array<string, mixed>>
     */
    private function aggregateCells(array $row): array
    {
        $cells = [];

        foreach ($this->query->definition->aggregates as $i => $aggregate) {
            $cells[] = $this->formatter->aggregate($aggregate, ['value' => $row["a$i"] ?? null,
                'currencyMin' => $row["a{$i}currencyMin"] ?? null, 'currencyMax' => $row["a{$i}currencyMax"] ?? null]);
        }

        return $cells;
    }

    private function applySorting(SelectBuilder $builder): void
    {
        foreach ($this->query->definition->sorting as [$field, $direction]) {
            $value = $this->query->valueExpressions($field)['value'];
            $desc = $direction === 'desc';

            if ($field->family() === FieldInfo::FAMILY_ENUM && $field->options !== []) {
                // The core order already sorts by position with DESC: the reverse direction reverses the options
                // (external review B15).
                $builder->order(Order::createByPositionInList(Expr::column($value),
                    $desc ? array_reverse($field->options) : $field->options));

                continue;
            }

            // A link of the main entity sorts by the name shown: the relation is joined for it (no ACL, the names of
            // linked records are shown to everyone who sees the record, like the core lists do).
            if ($field->family() === FieldInfo::FAMILY_LINK) {
                if (!$builder->hasLeftJoinAlias($field->ref->field)) {
                    $builder->leftJoin($field->ref->field);
                }

                $value = $field->ref->field . 'Name';
            }

            $builder->order($value, $desc ? 'DESC' : 'ASC');
        }

        $builder->order('id', 'ASC');
    }

    /**
     * @return array<string, mixed>
     */
    private function header(): array
    {
        $definition = $this->query->definition;

        return [
            'columns' => array_map(fn (FieldInfo $f) => ['key' => 'c:' . $f->ref->toString(),
                'field' => $f->ref->toString(), 'label' => $this->labels->column($f), 'fieldType' => $f->type,
                'numeric' => $f->isNumeric()], $definition->columns),
            'groups' => array_map(fn (GroupLevel $g, int $i) => ['key' => 'g:' . ($i + 1),
                'field' => $g->field->ref->toString(), 'label' => $this->labels->group($i, $g),
                'granularity' => $g->granularity?->value], $definition->groups, array_keys($definition->groups)),
            'aggregates' => array_map(fn (Aggregate $a) => ['key' => 'a:' . $a->key(), 'function' => $a->function,
                'field' => $a->field?->ref->toString(), 'label' => $this->labels->aggregate($a)],
                $definition->aggregates),
        ];
    }

    /**
     * @return array<string, mixed>
     */
    public function tabular(int $rowCount): array
    {
        $definition = $this->query->definition;
        $options = $this->query->options;
        $limit = $options->noLimit ? $this->maxRows : min($definition->rowLimit ?? $this->maxRows, $this->maxRows);
        $available = min($rowCount, $limit);
        $size = max(0, min($options->maxSize, $available - $options->offset));
        $select = [['id', 'id']];

        foreach ($definition->columns as $i => $column) {
            array_push($select, ...$this->selectField($column, "c$i"));
        }

        $rawRows = [];

        if ($size > 0) {
            $builder = $this->query->base()->select($select)->limit($options->offset, $size);
            $this->applySorting($builder);
            $rawRows = $this->fetch($builder);
        }

        $rows = [];

        foreach ($rawRows as $raw) {
            foreach ($definition->columns as $i => $column) {
                $this->formatter->rememberField($column, self::readField($raw, "c$i"));
            }
        }

        foreach ($rawRows as $raw) {
            $cells = [];
            $values = [];

            foreach ($definition->columns as $i => $column) {
                $value = self::readField($raw, "c$i");
                $cells[] = $this->formatter->field($column, $value);

                if ($column->isNumeric()) {
                    $values[$column->ref->toString()] = RawNumber::read($value['value']);
                }
            }

            $rows[] = ['id' => $raw['id'], 'cells' => $cells, 'calc' => $this->calculationCells($values)];
        }

        [$calculationTotals, $calculationsCapped] = $this->calculationTotals();

        return $this->header() + [
            'calculations' => array_map(fn ($c) => ['key' => 'k:' . $c->id,
                'label' => $definition->labels['k:' . $c->id] ?? $c->label], $definition->calculations),
            'rows' => $rows,
            'totals' => $this->columnTotals(),
            'calculationTotals' => $calculationTotals,
            'offset' => $options->offset,
            'maxSize' => $options->maxSize,
            'availableRows' => $available,
            'limits' => [
                'rowLimit' => $definition->rowLimit,
                'rowLimitHit' => !$options->noLimit && $definition->rowLimit !== null &&
                    $rowCount > $definition->rowLimit,
                'capHit' => $rowCount > $this->maxRows,
                'calculationsCapped' => $calculationsCapped,
            ],
        ];
    }

    /**
     * @param array<string, ?Decimal> $values
     * @return list<array<string, mixed>>
     */
    private function calculationCells(array $values): array
    {
        $cells = [];

        foreach ($this->query->definition->calculations as $calculation) {
            $value = $calculation->expression->evaluate($values);
            $cells[] = $value === null ? ['v' => null, 'f' => ''] :
                ['v' => $value->toString(), 'f' => $this->formatter->context()->numbers->format($value,
                    $calculation->expression->roundScale() ?? 2)];
        }

        return $cells;
    }

    /**
     * Totals of the numeric columns over all filtered rows (row limit and page ignored, D-96).
     *
     * @return array<string, array<string, array<string, mixed>>>
     */
    private function columnTotals(): array
    {
        $totals = $this->query->definition->totals;

        if ($totals === []) {
            return [];
        }

        $select = [];
        $aggregates = [];

        foreach ($totals as $ref => $functions) {
            $field = $this->query->definition->column($ref);

            foreach ($functions as $function) {
                $alias = 't' . count($aggregates);
                $aggregate = new Aggregate($function, $field);
                $aggregates[$alias] = [$ref, $aggregate];

                foreach ($this->query->aggregateExpressions($aggregate) as $role => $expression) {
                    $select[] = [$expression, $alias . ($role === 'value' ? '' : $role)];
                }
            }
        }

        $row = $this->fetch($this->query->base()->select($select))[0] ?? [];
        $result = [];

        foreach ($aggregates as $alias => [$ref, $aggregate]) {
            $result['c:' . $ref][$aggregate->function] = $this->formatter->aggregate($aggregate, [
                'value' => $row[$alias] ?? null, 'currencyMin' => $row[$alias . 'currencyMin'] ?? null,
                'currencyMax' => $row[$alias . 'currencyMax'] ?? null]);
        }

        return $result;
    }

    /**
     * Totals of the custom calculations: evaluated per row in PHP (exact decimals) over the filtered rows up to the
     * cap; capped = some rows were left out.
     *
     * @return array{array<string, array<string, array<string, mixed>>>, bool}
     */
    private function calculationTotals(): array
    {
        $calculations = array_filter($this->query->definition->calculations, fn ($c) => $c->functions !== []);

        if ($calculations === []) {
            return [[], false];
        }

        $select = [['id', 'id']];
        $refs = [];

        foreach ($calculations as $calculation) {
            foreach ($calculation->expression->references() as $ref) {
                $refs[$ref] ??= 'r' . count($refs);
            }
        }

        foreach ($refs as $ref => $alias) {
            $select[] = [$this->query->valueExpressions($this->query->definition->column($ref))['value'], $alias];
        }

        $rows = $this->fetch($this->query->base()->select($select)->order('id')->limit(0, $this->maxRows + 1));
        $capped = count($rows) > $this->maxRows;
        $rows = array_slice($rows, 0, $this->maxRows);
        $result = [];

        foreach ($calculations as $calculation) {
            $values = [];

            foreach ($rows as $row) {
                $operands = [];

                foreach ($refs as $ref => $alias) {
                    $operands[$ref] = RawNumber::read($row[$alias] ?? null);
                }

                $values[] = $calculation->expression->evaluate($operands);
            }

            $summary = DecimalMath::summarize($values);
            $scale = $calculation->expression->roundScale() ?? 2;

            foreach ($calculation->functions as $function) {
                $value = $summary[$function];
                $result['k:' . $calculation->id][$function] = $value === null ? ['v' => null, 'f' => ''] :
                    ['v' => $value->toString(), 'f' => $this->formatter->context()->numbers->format($value, $scale)];
            }
        }

        return [$result, $capped];
    }

    /**
     * Rows of one group level: keys of levels 1..k, the number of records and the aggregates; HAVING on level 1.
     *
     * @param ?array<mixed> $keys restrict to these level-1 keys
     * @return list<array<string, mixed>>
     */
    private function levelRows(int $level, ?array $keys, int $limit): array
    {
        $groups = array_slice($this->query->definition->groups, 0, $level);
        $select = [];
        $groupBy = [];

        foreach ($groups as $i => $group) {
            $expression = $this->query->groupExpression($group);
            $select[] = [$expression, 'g' . $i];
            $groupBy[] = $expression;
            $select = [...$select, ...$this->tokenSelect($group, 't' . $i)];
        }

        $builder = $this->query->base()
            ->select([...$select, ...$this->selectAggregates()])
            ->group($groupBy)
            ->limit(0, $limit + 1);

        if ($level === 1) {
            foreach ($this->query->definition->having as $having) {
                $builder->having($this->havingClause($having));
            }
        }

        if ($keys !== null) {
            $builder->where($this->keyRestriction($this->query->groupExpression($this->query->definition->groups[0]),
                $keys));
        }

        return $this->fetch($builder);
    }

    private function havingClause(Having $having): WhereClause
    {
        $expression = $this->query->aggregateExpressions($having->aggregate)['value'];

        return WhereClause::fromRaw(match ($having->operator) {
            'equals' => [$expression . '=' => $having->value],
            'notEquals' => [$expression . '!=' => $having->value],
            'greaterThan' => [$expression . '>' => $having->value],
            'lessThan' => [$expression . '<' => $having->value],
            'greaterThanOrEquals' => [$expression . '>=' => $having->value],
            'lessThanOrEquals' => [$expression . '<=' => $having->value],
            'between' => ['AND' => [[$expression . '>=' => $having->value[0]],
                [$expression . '<=' => $having->value[1]]]],
        });
    }

    /**
     * @param array<mixed> $keys
     */
    private function keyRestriction(string $expression, array $keys): WhereClause
    {
        $values = array_values(array_filter($keys, fn ($k) => $k !== null));
        $or = [];

        if ($values !== []) {
            $or[] = [$expression => $values];
        }

        if (count($values) !== count($keys)) {
            $or[] = [$expression => null];
        }

        return WhereClause::fromRaw($or === [] ? ['id' => null] : ['OR' => $or]);
    }

    /**
     * @param list<array<string, mixed>> $rows
     */
    private function rememberKeys(array $rows, int $levels): void
    {
        foreach ($rows as $row) {
            for ($i = 0; $i < $levels; $i++) {
                $group = $this->query->definition->groups[$i];

                if ($group->granularity === null) {
                    $this->formatter->rememberField($group->field, ['value' => $row["g$i"] ?? null]);
                }
            }
        }
    }

    /**
     * @param array<string, mixed> $row
     * @return array<string, mixed>
     */
    private function node(array $row, int $level): array
    {
        $group = $this->query->definition->groups[$level];
        $key = $row["g$level"] ?? null;

        return [
            'key' => $this->formatter->groupKey($group, $key === '' ? null : $key),
            'count' => (int) ($row['n'] ?? 0),
            'values' => $this->aggregateCells($row),
            'raw' => $row,
            // The key as SQL returned it: lookups and restrictions use it, the display value may differ
            // (decimal '1.00000000' shows as '1', a flag '0' as false, '' as empty).
            'rawKey' => $key,
            'token' => $row["t$level"] ?? null,
        ];
    }

    /**
     * Sorts nodes of one level: by the chosen aggregate (level 1, D-91), then by the group key.
     *
     * @param list<array<string, mixed>> $nodes
     * @return list<array<string, mixed>>
     */
    private function sortNodes(array $nodes, int $level): array
    {
        $group = $this->query->definition->groups[$level];
        $groupSort = $level === 0 ? $this->query->definition->groupSort : null;
        $index = $groupSort === null ? null :
            array_search($groupSort['aggregate'], $this->query->definition->aggregates, true);

        usort($nodes, function (array $a, array $b) use ($group, $groupSort, $index): int {
            if ($groupSort !== null && $index !== false) {
                $va = RawNumber::read($a['raw']["a$index"] ?? null);
                $vb = RawNumber::read($b['raw']["a$index"] ?? null);

                if ($va === null || $vb === null) {
                    $result = ($va === null) <=> ($vb === null);
                } else {
                    $result = $va->compare($vb) * ($groupSort['direction'] === 'desc' ? -1 : 1);
                }

                if ($result !== 0) {
                    return $result;
                }
            }

            return $this->order->compare($group, $a['key'], $b['key']);
        });

        return $nodes;
    }

    /**
     * Level-1 groups: all of them up to the cap, sorted, then cut to the group limit.
     *
     * @return array{list<array<string, mixed>>, array<string, mixed>, ?array<mixed>}
     */
    private function firstLevel(): array
    {
        $definition = $this->query->definition;
        $rows = $this->levelRows(1, null, ReportRunner::MAX_GROUPS);
        $capHit = count($rows) > ReportRunner::MAX_GROUPS;
        $rows = array_slice($rows, 0, ReportRunner::MAX_GROUPS);
        $this->rememberKeys($rows, 1);
        $nodes = $this->sortNodes(array_map(fn ($row) => $this->node($row, 0), $rows), 0);
        $limit = $this->query->options->noLimit ? ReportRunner::MAX_GROUPS :
            ($definition->groupLimit ?? ReportRunner::MAX_GROUPS);
        $groupsHit = count($nodes) > $limit;
        $shown = array_slice($nodes, 0, $limit);
        $restricted = $groupsHit || $capHit || $definition->having !== [];
        $keys = $restricted ? array_map(fn ($node) => $node['rawKey'], $shown) : null;

        return [$shown, [
            'groupLimit' => $definition->groupLimit,
            'groupCount' => count($nodes),
            'groupLimitHit' => $groupsHit && !$this->query->options->noLimit && $definition->groupLimit !== null,
            'capHit' => $capHit,
        ], $keys];
    }

    /**
     * @param ?array<mixed> $keys
     * @return list<array<string, mixed>>
     */
    private function grandTotal(?array $keys): array
    {
        $builder = $this->query->base()->select($this->selectAggregates());

        if ($keys !== null) {
            $builder->where($this->keyRestriction(
                $this->query->groupExpression($this->query->definition->groups[0]), $keys));
        }

        $row = $this->fetch($builder)[0] ?? [];

        return ['count' => (int) ($row['n'] ?? 0), 'values' => $this->aggregateCells($row)];
    }

    /**
     * @return array<string, mixed>
     */
    public function grouped(): array
    {
        $definition = $this->query->definition;
        [$level1, $limits, $keys] = $this->firstLevel();
        $restrictKeys = $keys ?? array_map(fn ($node) => $node['rawKey'], $level1);
        $levels = count($definition->groups);
        $tree = $level1;

        if ($levels > 1 && $level1 !== []) {
            $tree = $this->attachLevels($level1, $restrictKeys, $levels, $limits);
        }

        if ($definition->type === ReportType::SUMMARIES_WITH_DETAILS) {
            $tree = $this->attachDetails($tree, $restrictKeys, $limits);
        }

        return $this->header() + [
            'tree' => self::stripRaw($tree),
            'grandTotal' => $this->grandTotal($keys),
            'limits' => $limits + ['rowLimit' => $definition->rowLimit],
        ];
    }

    /**
     * @param list<array<string, mixed>> $level1
     * @param array<mixed> $keys
     * @param array<string, mixed> $limits
     * @return list<array<string, mixed>>
     */
    private function attachLevels(array $level1, array $keys, int $levels, array &$limits): array
    {
        $children = [];

        for ($level = 2; $level <= $levels; $level++) {
            $rows = $this->levelRows($level, $keys, $this->maxRows);

            if (count($rows) > $this->maxRows) {
                $limits['capHit'] = true;
                $rows = array_slice($rows, 0, $this->maxRows);
            }

            $this->rememberKeys($rows, $level);

            foreach ($rows as $row) {
                $path = [];

                for ($i = 0; $i < $level - 1; $i++) {
                    $path[] = $this->key($row["g$i"] ?? null, $row["t$i"] ?? null);
                }

                $children[$level][implode("\x1F", $path)][] = $this->node($row, $level - 1);
            }
        }

        $build = function (array $nodes, int $level, array $path) use (&$build, $children, $levels): array {
            $nodes = $this->sortNodes($nodes, $level - 1);

            foreach ($nodes as &$node) {
                $nodePath = [...$path, $this->nodeKey($node)];

                if ($level < $levels) {
                    $node['children'] = $build($children[$level + 1][implode("\x1F", $nodePath)] ?? [], $level + 1,
                        $nodePath);
                }
            }

            return $nodes;
        };

        $result = [];

        foreach ($level1 as $node) {
            $node['children'] = $build($children[2][$this->nodeKey($node)] ?? [], 2, [$this->nodeKey($node)]);
            $result[] = $node;
        }

        return $result;
    }

    /**
     * Record rows of each shown level-1 group (summariesWithDetails): the row limit applies per group (D-97).
     *
     * @param list<array<string, mixed>> $level1
     * @param array<mixed> $keys
     * @param array<string, mixed> $limits
     * @return list<array<string, mixed>>
     */
    private function attachDetails(array $level1, array $keys, array &$limits): array
    {
        $definition = $this->query->definition;
        $select = [['id', 'id'], [$this->query->groupExpression($definition->groups[0]), 'gk'],
            ...$this->tokenSelect($definition->groups[0], 'gt')];

        foreach ($definition->columns as $i => $column) {
            array_push($select, ...$this->selectField($column, "c$i"));
        }

        $builder = $this->query->base()->select($select)
            ->where($this->keyRestriction($this->query->groupExpression($definition->groups[0]), $keys));
        $this->applySorting($builder);
        $rows = $this->fetchCapped($builder, $this->maxRows, $limits);

        foreach ($rows as $raw) {
            foreach ($definition->columns as $i => $column) {
                $this->formatter->rememberField($column, self::readField($raw, "c$i"));
            }
        }

        $byKey = [];

        foreach ($rows as $raw) {
            $byKey[$this->key($raw['gk'] ?? null, $raw['gt'] ?? null)][] = $raw;
        }

        $perGroup = $this->query->options->noLimit ? $this->maxRows : ($definition->rowLimit ?? $this->maxRows);
        $limits['rowLimitHit'] = false;

        foreach ($level1 as &$node) {
            $groupRows = $byKey[$this->nodeKey($node)] ?? [];

            if (count($groupRows) > $perGroup) {
                $limits['rowLimitHit'] = true;
                $groupRows = array_slice($groupRows, 0, $perGroup);
            }

            $node['rows'] = array_map(function (array $raw) use ($definition): array {
                $cells = [];

                foreach ($definition->columns as $i => $column) {
                    $cells[] = $this->formatter->field($column, self::readField($raw, "c$i"));
                }

                return ['id' => $raw['id'], 'cells' => $cells];
            }, $groupRows);
        }

        return $level1;
    }

    /**
     * @return array<string, mixed>
     */
    public function matrix(): array
    {
        $definition = $this->query->definition;
        [$rows, $limits, $keys] = $this->firstLevel();
        $rowKeys = array_map(fn ($node) => $node['rawKey'], $rows);
        $g1 = $this->query->groupExpression($definition->groups[0]);
        $g2 = $this->query->groupExpression($definition->groups[1]);
        $columns = [];
        $cells = [];
        $columnsHit = false;

        if ($rows !== []) {
            $fetchColumns = function (array $rowKeys) use ($definition, $g1, $g2, &$limits): array {
                $columnRows = $this->fetchCapped($this->query->base()
                    ->select([[$g2, 'g1'], ...$this->tokenSelect($definition->groups[1], 't1'),
                        ...$this->selectAggregates()])
                    ->group([$g2])
                    ->where($this->keyRestriction($g1, $rowKeys)), $this->maxRows, $limits);
                $this->rememberKeysOf($columnRows, 1);

                return $this->sortNodes(array_map(fn ($row) => $this->node($row, 1), $columnRows), 1);
            };
            $columns = $fetchColumns($rowKeys);
            // All cells of the shown rows must fit the cap: otherwise fewer rows are shown, and the columns and the
            // grand total are those of the shown rows only (no cell is silently missing).
            $width = max(1, min(count($columns), ReportRunner::MAX_MATRIX_COLUMNS));
            $fitting = max(1, intdiv($this->maxRows, $width));

            if (count($rows) > $fitting) {
                $rows = array_slice($rows, 0, $fitting);
                $rowKeys = array_map(fn ($node) => $node['rawKey'], $rows);
                $keys = $rowKeys;
                $limits['capHit'] = true;
                $columns = $fetchColumns($rowKeys);
            }

            $columnsHit = count($columns) > ReportRunner::MAX_MATRIX_COLUMNS;
            $columns = array_slice($columns, 0, ReportRunner::MAX_MATRIX_COLUMNS);
            $columnKeys = array_map(fn ($node) => $node['rawKey'], $columns);

            $cellRows = $this->fetchCapped($this->query->base()
                ->select([[$g1, 'g0'], [$g2, 'g1'], ...$this->tokenSelect($definition->groups[0], 't0'),
                    ...$this->tokenSelect($definition->groups[1], 't1'), ...$this->selectAggregates()])
                ->group([$g1, $g2])
                ->where($this->keyRestriction($g1, $rowKeys))
                ->where($this->keyRestriction($g2, $columnKeys)), $this->maxRows, $limits);
            $byKey = [];

            foreach ($cellRows as $row) {
                $byKey[$this->key($row['g0'] ?? null, $row['t0'] ?? null)][$this->key($row['g1'] ?? null,
                    $row['t1'] ?? null)] = $row;
            }

            foreach ($rows as $node) {
                $line = [];

                foreach ($columns as $column) {
                    $row = $byKey[$this->nodeKey($node)][$this->nodeKey($column)] ?? null;
                    $line[] = $row === null ? null : ['count' => (int) ($row['n'] ?? 0),
                        'values' => $this->aggregateCells($row)];
                }

                $cells[] = $line;
            }
        }

        return $this->header() + [
            'matrix' => [
                'rows' => self::stripRaw($rows),
                'columns' => self::stripRaw($columns),
                'cells' => $cells,
            ],
            'grandTotal' => $this->grandTotal($keys),
            'limits' => $limits + ['matrixColumnsHit' => $columnsHit,
                'maxMatrixColumns' => ReportRunner::MAX_MATRIX_COLUMNS],
        ];
    }

    /**
     * Column keys of a matrix come as `g1` of single-level rows: names of their links are prefetched like keys.
     *
     * @param list<array<string, mixed>> $rows
     */
    private function rememberKeysOf(array $rows, int $level): void
    {
        $group = $this->query->definition->groups[$level];

        if ($group->granularity !== null) {
            return;
        }

        foreach ($rows as $row) {
            $this->formatter->rememberField($group->field, ['value' => $row["g$level"] ?? null]);
        }
    }

    /**
     * Options of the quick filter blocks: the values the report's conditions select (quick filters of the run aside,
     * so the options stay stable while ticking), the empty value as its own item.
     *
     * @return list<array<string, mixed>>
     */
    public function quickFilterOptions(): array
    {
        $result = [];

        foreach ($this->query->definition->quickFilters as $field) {
            $expression = $this->query->valueExpressions($field)['value'];

            // A text that the column collation finds equal to '' (spaces, a no-break space) is the empty item, as
            // the quick filter compares it.
            if (in_array($field->family(), [FieldInfo::FAMILY_TEXT, FieldInfo::FAMILY_ENUM], true)) {
                $expression = "NULLIF:($expression, '')";
            }

            $rows = $this->fetch($this->query->base([])
                ->select([[$expression, 'v']])
                ->group([$expression])
                ->limit(0, ReportRunner::MAX_QUICK_FILTER_OPTIONS + 1));
            $truncated = count($rows) > ReportRunner::MAX_QUICK_FILTER_OPTIONS;
            $rows = array_slice($rows, 0, ReportRunner::MAX_QUICK_FILTER_OPTIONS);

            foreach ($rows as $row) {
                $this->formatter->rememberField($field, ['value' => $row['v']]);
            }

            $options = [];
            $hasEmpty = false;

            foreach ($rows as $row) {
                if ($row['v'] === null || $row['v'] === '') {
                    $hasEmpty = true;

                    continue;
                }

                $cell = $this->formatter->field($field, ['value' => $row['v']]);
                $options[] = ['v' => $field->family() === FieldInfo::FAMILY_BOOL ? (bool) $row['v'] : (string) $row['v'],
                    'f' => $cell['f']];
            }

            $group = new GroupLevel($field, null, 'asc');
            usort($options, fn ($a, $b) => $this->order->compare($group, $a, $b));

            if ($hasEmpty) {
                $options[] = ['v' => null, 'f' => $this->formatter->groupKey($group, null)['f'], 'empty' => true];
            }

            $result[] = ['field' => $field->ref->toString(), 'label' => $this->labels->field($field),
                'options' => $options, 'truncated' => $truncated];
        }

        return $result;
    }

    /**
     * Columns of the collation token of a text group (empty for other groups).
     *
     * @return list<array{string, string}>
     */
    private function tokenSelect(GroupLevel $group, string $alias): array
    {
        $token = $this->query->groupToken($group);

        return $token === null ? [] : [[$token, $alias]];
    }

    /**
     * Lookup key of a group value, equal for the values the database puts into one group: a text group by its
     * collation token ("<space weight>:<weights>" from ITVOLGA_GROUP_TOKEN, trailing space weights stripped as
     * PAD SPACE compares), so a record of «berlin» finds the group «Berlin» (external review B8); other values as SQL
     * returned them.
     */
    private function key(mixed $value, ?string $token): string
    {
        if ($value === null) {
            return "\x00";
        }

        if ($token === null) {
            return (string) $value;
        }

        [$space, $weights] = array_pad(explode(':', $token, 2), 2, '');

        while ($space !== '' && str_ends_with($weights, $space)) {
            $weights = substr($weights, 0, -strlen($space));
        }

        return "\x01" . $weights;
    }

    /**
     * @param array<string, mixed> $node
     */
    private function nodeKey(array $node): string
    {
        return $this->key($node['rawKey'], $node['token']);
    }

    /**
     * @param list<array<string, mixed>> $nodes
     * @return list<array<string, mixed>>
     */
    private static function stripRaw(array $nodes): array
    {
        return array_map(function (array $node): array {
            unset($node['raw'], $node['rawKey'], $node['token']);

            if (isset($node['children'])) {
                $node['children'] = self::stripRaw($node['children']);
            }

            return $node;
        }, $nodes);
    }
}
