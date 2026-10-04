<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Definition;

/**
 * Charts of a summary report (D-105): settings common to all charts and up to three charts. The canonical stored
 * form is always an object, so a stored NULL only means "not saved since the charts exist" (D-114).
 */
final class ChartSettings
{
    public const MAX_ITEMS = 3;
    public const MAX_TITLE_LENGTH = 150;
    public const POSITIONS = ['top', 'bottom'];
    public const PROGRESS_LINES = ['MIN', 'AVG', 'MAX'];

    /**
     * @param list<string> $progressLines subset of PROGRESS_LINES in their order
     * @param list<ChartItem> $items
     */
    public function __construct(
        public readonly string $title = '',
        public readonly string $position = 'top',
        public readonly bool $collapseTable = false,
        public readonly ChartAxis $axis = ChartAxis::GROUP1,
        public readonly array $progressLines = [],
        public readonly array $items = [],
    ) {}

    public function isEmpty(): bool
    {
        return $this->items === [];
    }

    /**
     * @return array<string, mixed>
     */
    public function toArray(): array
    {
        return [
            'title' => $this->title,
            'position' => $this->position,
            'collapseTable' => $this->collapseTable,
            'axis' => $this->axis->value,
            'progressLines' => $this->progressLines,
            'items' => array_map(fn (ChartItem $item) => $item->toArray(), $this->items),
        ];
    }
}
