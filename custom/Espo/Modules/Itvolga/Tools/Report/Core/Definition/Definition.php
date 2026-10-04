<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Definition;

/**
 * A checked report definition (DefinitionParser): every field resolved by the Schema for the user, the type rules,
 * limits and cross-references verified. Immutable; toAttributes() gives the canonical stored JSON.
 */
final class Definition
{
    /**
     * @param list<FieldInfo> $columns
     * @param list<array{FieldInfo, string}> $sorting column and direction (asc|desc)
     * @param list<GroupLevel> $groups
     * @param list<Aggregate> $aggregates
     * @param ?array{aggregate: Aggregate, direction: string} $groupSort
     * @param array<string, list<string>> $totals column ref → functions
     * @param list<Calculation> $calculations
     * @param array<string, mixed> $filters normalised condition tree
     * @param array<string, FieldInfo> $filterFields ref → field of every condition of the tree
     * @param list<Having> $having
     * @param list<FieldInfo> $quickFilters
     * @param array<string, string> $labels result key → label
     * @param ?string $manyLink the single to-many link of columns, groups and aggregates
     * @param ChartSettings $charts charts of a summary type (D-105)
     * @param DashboardSettings $dashboard the report on a dashboard (D-109)
     */
    public function __construct(
        public readonly ReportType $type,
        public readonly string $entityType,
        public readonly array $columns,
        public readonly array $sorting,
        public readonly ?int $rowLimit,
        public readonly array $groups,
        public readonly array $aggregates,
        public readonly ?array $groupSort,
        public readonly ?int $groupLimit,
        public readonly array $totals,
        public readonly array $calculations,
        public readonly array $filters,
        public readonly array $filterFields,
        public readonly array $having,
        public readonly array $quickFilters,
        public readonly array $labels,
        public readonly ?string $manyLink,
        public readonly ChartSettings $charts = new ChartSettings(),
        public readonly DashboardSettings $dashboard = new DashboardSettings(),
    ) {}

    /**
     * A copy with some parts replaced, by the names of the constructor parameters.
     */
    public function with(mixed ...$changes): self
    {
        return new self(...array_merge(get_object_vars($this), $changes));
    }

    /**
     * @param array<string, mixed> $filters
     * @param array<string, FieldInfo> $filterFields
     */
    public function withFilters(array $filters, array $filterFields): self
    {
        return $this->with(filters: $filters, filterFields: $filterFields);
    }

    /**
     * @param array<string, string> $labels
     */
    public function withLabels(array $labels): self
    {
        return $this->with(labels: $labels);
    }

    public function aggregate(string $key): ?Aggregate
    {
        foreach ($this->aggregates as $aggregate) {
            if ($aggregate->key() === $key) {
                return $aggregate;
            }
        }

        return null;
    }

    public function column(string $ref): ?FieldInfo
    {
        foreach ($this->columns as $column) {
            if ($column->ref->toString() === $ref) {
                return $column;
            }
        }

        return null;
    }

    /**
     * Canonical stored form of the JSON parts (reports.md §2).
     *
     * @return array<string, mixed>
     */
    public function toAttributes(): array
    {
        return [
            'columns' => array_map(fn (FieldInfo $f) => $f->ref->toString(), $this->columns),
            'sorting' => array_map(fn ($s) => ['column' => $s[0]->ref->toString(), 'direction' => $s[1]],
                $this->sorting),
            'rowLimit' => $this->rowLimit,
            'groups' => array_map(fn (GroupLevel $g) => $g->toArray(), $this->groups),
            'aggregates' => array_map(fn (Aggregate $a) => $a->toArray(), $this->aggregates),
            'groupSort' => $this->groupSort === null ? null :
                ['aggregate' => $this->groupSort['aggregate']->key(), 'direction' => $this->groupSort['direction']],
            'groupLimit' => $this->groupLimit,
            'totals' => array_map(fn ($ref, $functions) => ['column' => $ref, 'functions' => $functions],
                array_keys($this->totals), array_values($this->totals)),
            'calculations' => array_map(fn (Calculation $c) => $c->toArray(), $this->calculations),
            'filters' => $this->filters,
            'havingFilters' => array_map(fn (Having $h) => $h->toArray(), $this->having),
            'quickFilters' => array_map(fn (FieldInfo $f) => $f->ref->toString(), $this->quickFilters),
            'labels' => (object) $this->labels,
            'charts' => $this->charts->toArray(),
            'dashboard' => $this->dashboard->toArray(),
        ];
    }
}
