<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\FinanceDocument;

use Espo\Modules\Itvolga\Tools\Finance\Decimal;
use Espo\Modules\Itvolga\Tools\Finance\Editing\Limits;
use Espo\Modules\Itvolga\Tools\Finance\Exceptions\InvalidValue;
use Espo\Modules\Itvolga\Tools\Finance\Source\Verification;

/**
 * Source marks of an imported document (D-46): the formula class, how the stored totals compare with the core
 * recomputation, and the recomputed totals themselves («Пересчёт ядра», shown next to the mark when they differ).
 * Written together by itvolga-finance-verify, cleared together when the document is recalculated in EspoCRM (D-51)
 * and kept in its sourceTotals snapshot. The stored totals are never changed (D-05).
 */
final class SourceMarks
{
    /** Stored total → the attribute of its recomputation by the core. */
    public const EXPECTED = [
        'subtotal' => 'expectedSubtotal',
        'preTaxTotal' => 'expectedPreTaxTotal',
        'grandTotal' => 'expectedGrandTotal',
    ];

    /** @var list<string> */
    public const ATTRIBUTES = ['sourceFormula', 'totalsCheck', 'expectedSubtotal', 'expectedPreTaxTotal',
        'expectedGrandTotal'];

    /**
     * @return array<string, ?string> attribute → value; the recomputed totals are exact (an unverified document has
     *   none), stored at the scale of the total's column
     * @throws InvalidValue a recomputed total that does not fit its column: never truncated (MySQL is not strict, D-33)
     */
    public static function of(Verification $verification): array
    {
        $marks = [
            'sourceFormula' => $verification->formulaClass->value,
            'totalsCheck' => $verification->worstCheck()?->value ?? 'unverified',
        ];
        $expected = [
            'subtotal' => $verification->expectedSubtotal,
            'preTaxTotal' => $verification->expectedPreTaxTotal,
            'grandTotal' => $verification->expectedGrandTotal,
        ];

        foreach (self::EXPECTED as $total => $attribute) {
            $marks[$attribute] = self::stored($expected[$total], $total, $attribute);
        }

        return $marks;
    }

    /**
     * @return array<string, ?string> the marks of a document calculated in EspoCRM: none
     */
    public static function cleared(): array
    {
        return ['sourceFormula' => '', 'totalsCheck' => '', ...array_fill_keys(array_values(self::EXPECTED), null)];
    }

    private static function stored(?Decimal $value, string $total, string $attribute): ?string
    {
        if ($value === null) {
            return null;
        }

        Limits::check($value, Limits::TOTALS[$total], $attribute);

        return $value->toFixed(Limits::TOTALS[$total][1]);
    }
}
