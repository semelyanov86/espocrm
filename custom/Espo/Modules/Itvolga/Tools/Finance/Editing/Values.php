<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Finance\Editing;

use Espo\Modules\Itvolga\Tools\Finance\Decimal;
use Espo\Modules\Itvolga\Tools\Finance\Exceptions\InvalidValue;

/**
 * Input values with the field and line they belong to, so that a refusal can be shown next to the right cell.
 */
final class Values
{
    public static function decimal(mixed $value, string $field, ?int $line): Decimal
    {
        $where = $line === null ? $field : "Line $line: $field";

        if (is_float($value)) {
            throw new InvalidValue("$where: float values are not accepted.", 'float', $line, $field);
        }

        try {
            return Decimal::of($value);
        } catch (InvalidValue) {
            throw new InvalidValue("$where: not a decimal number.", 'notDecimal', $line, $field);
        }
    }
}
