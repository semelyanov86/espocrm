<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Definition;

/**
 * Chart types of a summary report (D-105). Stacked types differ from plain ones only on the axis «group 1 → group 2»
 * (series of group 2 stacked in a category).
 */
enum ChartType: string
{
    case BAR = 'bar';
    case STACKED_BAR = 'stackedBar';
    case HORIZONTAL_BAR = 'horizontalBar';
    case STACKED_HORIZONTAL_BAR = 'stackedHorizontalBar';
    case LINE = 'line';
    case PIE = 'pie';
    case PIE_PERCENT = 'piePercent';
    case FUNNEL = 'funnel';

    public function isPie(): bool
    {
        return $this === self::PIE || $this === self::PIE_PERCENT;
    }

    /**
     * Progress lines are drawn over bars and lines (D-107), not over pies and the funnel.
     */
    public function hasProgressLines(): bool
    {
        return !$this->isPie() && $this !== self::FUNNEL;
    }

    /**
     * A funnel shows one series: on the axis «group 1 → group 2» it would have to add up values of group 2 across
     * group 1, which is wrong for COUNT DISTINCT and AVG (D-106).
     */
    public function allowsSecondGroup(): bool
    {
        return $this !== self::FUNNEL;
    }
}
