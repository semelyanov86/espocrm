<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Metric;

use Espo\Modules\Itvolga\Tools\Report\Core\Definition\Aggregate;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\DefinitionError;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\FieldRef;

/**
 * Structure of the rows of a key-metrics set (D-111): at most MAX_ROWS rows in the order shown; each keeps its id
 * (`m<n>`, a new or repeated one gets a free number, as calculations do); a system filter becomes its primary where
 * item; the copied conditions of a saved filter are a list of where items of limited size. Whether the sources exist
 * and are allowed is checked by the module with the ACL of the saving user (MetricRowsValidator).
 */
final class MetricRowsParser
{
    public const MAX_ROWS = 30;
    public const MAX_LABEL_LENGTH = 150;
    public const MAX_WHERE_BYTES = 8192;

    /**
     * @return list<MetricRow>
     */
    public static function parse(mixed $raw): array
    {
        $raw = json_decode((string) json_encode($raw), true);

        if ($raw === null) {
            return [];
        }

        if (!is_array($raw) || !array_is_list($raw)) {
            throw new DefinitionError('badStructure', 'rows');
        }

        if (count($raw) > self::MAX_ROWS) {
            throw new DefinitionError('tooMany', 'rows', ['max' => self::MAX_ROWS]);
        }

        $ids = self::ids($raw);
        $result = [];

        foreach ($raw as $i => $item) {
            if (!is_array($item)) {
                throw new DefinitionError('badStructure', "rows[$i]");
            }

            $result[] = self::row($item, $ids[$i], "rows[$i]");
        }

        return $result;
    }

    /**
     * @param list<mixed> $raw
     * @return array<int, string>
     */
    private static function ids(array $raw): array
    {
        $ids = [];

        foreach ($raw as $i => $item) {
            $given = is_array($item) ? ($item['id'] ?? null) : null;

            if (is_string($given) && preg_match('/^m[1-9]\d{0,2}$/', $given) && !in_array($given, $ids, true)) {
                $ids[$i] = $given;
            }
        }

        foreach (array_keys($raw) as $i) {
            for ($n = 1; !isset($ids[$i]); $n++) {
                if (!in_array('m' . $n, $ids, true)) {
                    $ids[$i] = 'm' . $n;
                }
            }
        }

        return $ids;
    }

    /**
     * @param array<string, mixed> $item
     */
    private static function row(array $item, string $id, string $path): MetricRow
    {
        $label = is_string($item['label'] ?? null) ? trim($item['label']) : '';

        if ($label === '' || mb_strlen($label) > self::MAX_LABEL_LENGTH) {
            throw new DefinitionError('metricLabelRequired', "$path.label", ['max' => self::MAX_LABEL_LENGTH]);
        }

        return match ($item['source'] ?? null) {
            MetricRow::SOURCE_REPORT => self::reportRow($item, $id, $label, $path),
            MetricRow::SOURCE_FILTER => self::filterRow($item, $id, $label, $path),
            default => throw new DefinitionError('badMetricSource', "$path.source"),
        };
    }

    /**
     * @param array<string, mixed> $item
     */
    private static function reportRow(array $item, string $id, string $label, string $path): MetricRow
    {
        $reportId = $item['reportId'] ?? null;

        if (!is_string($reportId) || !preg_match('/^[A-Za-z0-9]{1,24}$/', $reportId)) {
            throw new DefinitionError('badMetricSource', "$path.reportId");
        }

        $function = $item['function'] ?? 'COUNT';
        $column = $item['column'] ?? null;

        if (!in_array($function, Aggregate::FUNCTIONS, true)) {
            throw new DefinitionError('badMetric', "$path.function");
        }

        if ($function === 'COUNT' ? $column !== null : FieldRef::parse($column) === null) {
            throw new DefinitionError('badMetric', "$path.column");
        }

        return new MetricRow($id, $label, MetricRow::SOURCE_REPORT, $function, $reportId,
            $function === 'COUNT' ? null : FieldRef::parse($column)?->toString());
    }

    /**
     * @param array<string, mixed> $item
     */
    private static function filterRow(array $item, string $id, string $label, string $path): MetricRow
    {
        $entityType = $item['entityType'] ?? null;

        if (!is_string($entityType) || !preg_match('/^[A-Z][A-Za-z0-9]{0,99}$/', $entityType)) {
            throw new DefinitionError('badMetricSource', "$path.entityType");
        }

        if (($item['function'] ?? 'COUNT') !== 'COUNT' || ($item['column'] ?? null) !== null) {
            throw new DefinitionError('badMetric', "$path.function");
        }

        $filter = is_array($item['filter'] ?? null) ? $item['filter'] : [];
        $kind = $filter['kind'] ?? null;
        $name = is_string($filter['name'] ?? null) ? trim($filter['name']) : '';

        if ($kind === MetricRow::KIND_SYSTEM) {
            if (!preg_match('/^[A-Za-z][A-Za-z0-9_]{0,99}$/', $name)) {
                throw new DefinitionError('badMetricFilter', "$path.filter");
            }

            return new MetricRow($id, $label, MetricRow::SOURCE_FILTER, 'COUNT', entityType: $entityType,
                filter: ['kind' => $kind, 'name' => $name], where: [['type' => 'primary', 'value' => $name]]);
        }

        if ($kind !== MetricRow::KIND_PRESET || $name === '' || mb_strlen($name) > self::MAX_LABEL_LENGTH) {
            throw new DefinitionError('badMetricFilter', "$path.filter");
        }

        $where = $item['where'] ?? null;

        if (!is_array($where) || !array_is_list($where) ||
            array_filter($where, fn ($w) => !is_array($w) || !is_string($w['type'] ?? null)) !== []) {
            throw new DefinitionError('badMetricFilter', "$path.where");
        }

        if (strlen((string) json_encode($where)) > self::MAX_WHERE_BYTES) {
            throw new DefinitionError('metricFilterTooLarge', "$path.where", ['max' => self::MAX_WHERE_BYTES]);
        }

        return new MetricRow($id, $label, MetricRow::SOURCE_FILTER, 'COUNT', entityType: $entityType,
            filter: ['kind' => $kind, 'name' => $name], where: array_values($where));
    }
}
