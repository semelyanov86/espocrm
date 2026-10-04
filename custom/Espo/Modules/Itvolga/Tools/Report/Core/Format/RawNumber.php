<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Format;

use Espo\Modules\Itvolga\Tools\Finance\Decimal;

/**
 * A number read from SQL as Decimal (D-93): DECIMAL and aggregates come as strings, INT as int; a FLOAT column (the
 * only place a binary float exists) is written out with 10 decimals once, at this boundary, and never computed with.
 */
final class RawNumber
{
    public static function read(mixed $value): ?Decimal
    {
        if ($value === null || $value === '') {
            return null;
        }

        if (is_float($value)) {
            $value = rtrim(rtrim(sprintf('%.10F', $value), '0'), '.');
        }

        if (is_bool($value)) {
            $value = (int) $value;
        }

        return Decimal::of(is_string($value) && str_starts_with($value, '.') ? '0' . $value : $value);
    }
}
