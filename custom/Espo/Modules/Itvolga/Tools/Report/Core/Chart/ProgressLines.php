<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Chart;

use Espo\Modules\Itvolga\Tools\Finance\Decimal;
use Espo\Modules\Itvolga\Tools\Report\Core\DecimalMath;

/**
 * Progress lines of a chart (D-107): for each category in the shown order, the minimum, the average and the maximum of
 * the values from the first category up to it. The average is the plain mean of the category values (not weighted by
 * records); an empty category is skipped, and before the first value there is none.
 */
final class ProgressLines
{
    /**
     * @param list<?Decimal> $values
     * @param list<string> $functions MIN, AVG, MAX
     * @return array<string, list<?Decimal>>
     */
    public static function compute(array $values, array $functions): array
    {
        $result = array_fill_keys($functions, []);
        $min = null;
        $max = null;
        $sum = null;
        $count = 0;

        foreach ($values as $value) {
            if ($value !== null) {
                $count++;
                $sum = $sum === null ? $value : $sum->add($value);
                $min = $min === null || $value->compare($min) < 0 ? $value : $min;
                $max = $max === null || $value->compare($max) > 0 ? $value : $max;
            }

            foreach ($functions as $function) {
                $result[$function][] = match ($function) {
                    'MIN' => $min,
                    'MAX' => $max,
                    'AVG' => $sum === null ? null : DecimalMath::divide($sum, Decimal::of($count)),
                };
            }
        }

        return $result;
    }
}
