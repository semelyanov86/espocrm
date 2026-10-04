<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Definition;

/**
 * Categories of the charts: groups of level 1, or groups of level 1 with the values of group 2 as series (D-106).
 */
enum ChartAxis: string
{
    case GROUP1 = 'group1';
    case GROUP1_GROUP2 = 'group1group2';
}
