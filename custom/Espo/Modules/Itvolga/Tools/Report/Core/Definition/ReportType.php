<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Definition;

/**
 * The four report types and the parts each of them has (the steps of the builder, reports.md §2).
 */
enum ReportType: string
{
    case TABULAR = 'tabular';
    case SUMMARIES = 'summaries';
    case SUMMARIES_WITH_DETAILS = 'summariesWithDetails';
    case MATRIX = 'matrix';

    /**
     * @return array{int, int} allowed number of group levels
     */
    public function groupLevels(): array
    {
        return match ($this) {
            self::TABULAR => [0, 0],
            self::SUMMARIES => [1, 3],
            self::SUMMARIES_WITH_DETAILS => [1, 1],
            self::MATRIX => [2, 2],
        };
    }

    public function isGrouped(): bool
    {
        return $this !== self::TABULAR;
    }

    public function hasColumns(): bool
    {
        return $this === self::TABULAR || $this === self::SUMMARIES_WITH_DETAILS;
    }

    public function hasCalculations(): bool
    {
        return $this === self::TABULAR;
    }
}
