<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Metric;

use Espo\Modules\Itvolga\Tools\Report\Core\Definition\Aggregate;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\Definition;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\DefinitionError;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\ReportType;

/**
 * The aggregate a metric of a tabular report computes (D-112): the record count, or SUM/AVG/MIN/MAX of one of the
 * report's numeric columns over all records of its conditions — exactly as the column totals do (D-96), so with a
 * to-many link only fields of that link (D-90).
 */
final class MetricRules
{
    public static function aggregate(Definition $definition, string $function, ?string $column): Aggregate
    {
        if ($definition->type !== ReportType::TABULAR) {
            throw new DefinitionError('metricNotTabular', 'reportId');
        }

        if ($function === 'COUNT') {
            if ($column !== null) {
                throw new DefinitionError('badMetric', 'column');
            }

            return new Aggregate('COUNT');
        }

        if (!in_array($function, Aggregate::FUNCTIONS, true)) {
            throw new DefinitionError('badMetric', 'function');
        }

        $field = $column === null ? null : $definition->column($column);

        if ($field === null || !$field->isNumeric()) {
            throw new DefinitionError('metricBadColumn', 'column', ['field' => (string) $column]);
        }

        if ($definition->manyLink !== null && !str_starts_with((string) $column, $definition->manyLink . '.')) {
            throw new DefinitionError('aggregateMultiplied', 'column',
                ['field' => (string) $column, 'link' => $definition->manyLink]);
        }

        return new Aggregate($function, $field);
    }
}
