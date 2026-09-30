<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Finance\Source;

use Espo\Modules\Itvolga\Tools\Finance\Decimal;

/**
 * Result of SourceVerifier: the formula class, recomputed totals and how the stored values compare.
 */
final class Verification
{
    /**
     * @param list<string> $reasons why the document is Unverified (empty otherwise)
     * @param array<string, TotalCheck> $checks subtotal / preTaxTotal / grandTotal → result (empty when Unverified)
     * @param list<MarginCheck> $margins per line, in line order
     */
    public function __construct(
        public readonly FormulaClass $formulaClass,
        public readonly array $reasons,
        public readonly ?Decimal $expectedSubtotal,
        public readonly ?Decimal $expectedPreTaxTotal,
        public readonly ?Decimal $expectedTaxAmount,
        public readonly ?Decimal $expectedGrandTotal,
        public readonly array $checks,
        public readonly array $margins,
    ) {}

    /**
     * True when the tax on the lines exists in the source but is not part of the totals (contract rule §4.2).
     */
    public function lineTaxNotApplied(): bool
    {
        return $this->formulaClass === FormulaClass::LineTaxNotApplied;
    }

    /**
     * Class known and no total differs beyond rounding.
     */
    public function totalsConsistent(): bool
    {
        if ($this->formulaClass === FormulaClass::Unverified) {
            return false;
        }

        foreach ($this->checks as $check) {
            if ($check === TotalCheck::Mismatch) {
                return false;
            }
        }

        return true;
    }

    public function worstCheck(): ?TotalCheck
    {
        if ($this->checks === []) {
            return null;
        }

        $values = array_values($this->checks);

        return in_array(TotalCheck::Mismatch, $values, true) ? TotalCheck::Mismatch
            : (in_array(TotalCheck::Rounded, $values, true) ? TotalCheck::Rounded : TotalCheck::Exact);
    }
}
