<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core;

/**
 * Date granularity of a group (D-89). Half-year: January–June is the 1st.
 */
enum Granularity: string
{
    case DAY = 'day';
    case WEEK = 'week';
    case MONTH = 'month';
    case QUARTER = 'quarter';
    case HALF_YEAR = 'halfYear';
    case YEAR = 'year';
}
