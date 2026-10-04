<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Definition;

/**
 * One chart: its type and the aggregate it plots — one of the report's aggregates or the record count (COUNT is
 * always available: every group carries its exact COUNT DISTINCT).
 */
final class ChartItem
{
    public function __construct(
        public readonly ChartType $type,
        public readonly Aggregate $aggregate,
    ) {}

    /**
     * @return array{type: string, aggregate: string}
     */
    public function toArray(): array
    {
        return ['type' => $this->type->value, 'aggregate' => $this->aggregate->key()];
    }
}
