<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core;

use Espo\Modules\Itvolga\Tools\Finance\Decimal;

/**
 * Report arithmetic over exact decimals (D-91): division and the summary functions of a column of values.
 * Floats never appear; an empty value is skipped by the summaries, like SQL aggregates do.
 */
final class DecimalMath
{
    /** Decimals kept by a quotient (and so by an average): the storage scale of decimal fields. */
    public const DIVISION_SCALE = 8;

    /**
     * Quotient with DIVISION_SCALE decimals rounded half away from zero; null when dividing by zero.
     */
    public static function divide(Decimal $dividend, Decimal $divisor): ?Decimal
    {
        if ($divisor->isZero()) {
            return null;
        }

        $quotient = bcdiv($dividend->toString(), $divisor->toString(), self::DIVISION_SCALE + 1);

        return Decimal::of($quotient)->round(self::DIVISION_SCALE);
    }

    /**
     * @param iterable<Decimal|null> $values
     * @return array{SUM: ?Decimal, AVG: ?Decimal, MIN: ?Decimal, MAX: ?Decimal, COUNT: int}
     */
    public static function summarize(iterable $values): array
    {
        $sum = null;
        $min = null;
        $max = null;
        $count = 0;

        foreach ($values as $value) {
            if ($value === null) {
                continue;
            }

            $count++;
            $sum = $sum === null ? $value : $sum->add($value);
            $min = $min === null || $value->compare($min) < 0 ? $value : $min;
            $max = $max === null || $value->compare($max) > 0 ? $value : $max;
        }

        return [
            'SUM' => $sum,
            'AVG' => $sum === null ? null : self::divide($sum, Decimal::of($count)),
            'MIN' => $min,
            'MAX' => $max,
            'COUNT' => $count,
        ];
    }
}
