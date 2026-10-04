<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Metric;

/**
 * A row of a key-metrics set (D-111): a label and its source — a tabular report with the record count or
 * SUM/AVG/MIN/MAX of one of its numeric columns, or a list filter of an entity (the record count only). A filter is
 * kept as the where items of the standard list: a system filter as its primary filter, a personal saved filter of the
 * author copied when chosen (its name is only shown, the conditions never follow later changes of the preset).
 */
final class MetricRow
{
    public const SOURCE_REPORT = 'report';
    public const SOURCE_FILTER = 'filter';
    public const KIND_SYSTEM = 'system';
    public const KIND_PRESET = 'preset';

    /**
     * @param ?array{kind: string, name: string} $filter
     * @param list<array<string, mixed>> $where
     */
    public function __construct(
        public readonly string $id,
        public readonly string $label,
        public readonly string $source,
        public readonly string $function = 'COUNT',
        public readonly ?string $reportId = null,
        public readonly ?string $column = null,
        public readonly ?string $entityType = null,
        public readonly ?array $filter = null,
        public readonly array $where = [],
    ) {}

    /**
     * @return array<string, mixed>
     */
    public function toArray(): array
    {
        $common = ['id' => $this->id, 'label' => $this->label, 'source' => $this->source];

        if ($this->source === self::SOURCE_REPORT) {
            return $common + ['reportId' => $this->reportId, 'function' => $this->function, 'column' => $this->column];
        }

        return $common + ['entityType' => $this->entityType, 'function' => 'COUNT', 'filter' => $this->filter,
            'where' => $this->where];
    }

    /**
     * What the value depends on (the source and the metric, not the label): a stored row whose source key is unchanged
     * is not checked again on save (D-111).
     */
    public function sourceKey(): string
    {
        $data = $this->toArray();
        unset($data['id'], $data['label']);

        return (string) json_encode($data);
    }
}
