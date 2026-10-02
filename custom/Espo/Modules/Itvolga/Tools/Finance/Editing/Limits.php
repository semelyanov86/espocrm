<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Finance\Editing;

use Espo\Modules\Itvolga\Tools\Finance\Decimal;
use Espo\Modules\Itvolga\Tools\Finance\Exceptions\InvalidValue;

/**
 * DECIMAL(precision, scale) of the storage columns (finance-contract.md §11). The server checks them itself because
 * MySQL runs with a non-strict sql_mode (D-33): a value that does not fit would be clamped silently instead of failing.
 */
final class Limits
{
    /** Document header inputs. */
    public const HEADER = [
        'discountAmount' => [25, 8],
        'discountPercent' => [25, 3],
        'shippingAmount' => [25, 8],
        'shippingTaxPercent' => [25, 3],
        'adjustment' => [25, 8],
    ];

    /** Document totals. */
    public const TOTALS = [
        'subtotal' => [25, 8],
        'preTaxTotal' => [25, 8],
        'grandTotal' => [25, 8],
    ];

    /** Item inputs and computed values. */
    public const LINE = [
        'quantity' => [25, 3],
        'unitPrice' => [27, 8],
        'discountAmount' => [27, 8],
        'discountPercent' => [7, 3],
        'taxRate' => [7, 3],
        'purchaseCost' => [27, 8],
        'amount' => [25, 8],
        'margin' => [27, 8],
    ];

    /**
     * @param array{int, int} $limit [precision, scale]
     */
    public static function check(Decimal $value, array $limit, string $field, ?int $line = null): void
    {
        [$precision, $scale] = $limit;

        if ($value->significantScale() > $scale) {
            throw new InvalidValue("$field has more than $scale decimals.", 'tooManyDecimals', $line, $field);
        }

        $integer = ltrim(explode('.', ltrim($value->toString(), '-'))[0], '0');

        if (strlen($integer) > $precision - $scale) {
            throw new InvalidValue("$field does not fit DECIMAL($precision,$scale).", 'tooLarge', $line, $field);
        }
    }
}
