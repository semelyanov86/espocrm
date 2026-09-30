<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Finance\Source;

use Espo\Modules\Itvolga\Tools\Finance\Decimal;
use Espo\Modules\Itvolga\Tools\Finance\Document;
use Espo\Modules\Itvolga\Tools\Finance\Line;
use Espo\Modules\Itvolga\Tools\Finance\Scale;
use Espo\Modules\Itvolga\Tools\Finance\TaxMode;

/**
 * Recomputes a Vtiger document from its lines and compares the result with the stored totals.
 *
 * The stored totals stay the reference (D-05): this class never returns "corrected" values for storage, it only says
 * which formula explains them (FormulaClass) and where they differ (TotalCheck). Formulas are the ones that reproduce
 * every live document of the source (finance-contract.md §4, §12); combinations the data does not contain —
 * VAT added per line after 2018-07, percent discounts, shipping, adjustment, group tax with a document discount —
 * are Unverified instead of being guessed.
 */
final class SourceVerifier
{
    public function verify(SourceDocument $source): Verification
    {
        $document = $source->document;
        $reasons = $this->unconfirmedInputs($document);
        $class = $this->classify($source, $reasons);
        $margins = array_map(fn (Line $line) => $this->checkMargin($line), $document->lines);

        if ($class === FormulaClass::Unverified) {
            return new Verification($class, $reasons, null, null, null, null, [], $margins);
        }

        $subtotal = $document->netSum();
        $preTaxTotal = $subtotal->sub($document->discountAmount);
        $tax = $class === FormulaClass::GroupTaxAdded
            // Vtiger rounds the pre-tax base and the group tax to kopecks (Inventory Edit.js, calculateGroupTax).
            ? $preTaxTotal->round(Scale::MONEY)->percent($document->lines[0]->taxPercent)->round(Scale::MONEY)
            : Decimal::zero();
        $grandTotal = $preTaxTotal->add($tax);

        $checks = [
            'subtotal' => $this->compare($source->subtotal, $subtotal),
            'preTaxTotal' => $this->compare($source->preTaxTotal, $preTaxTotal),
            'grandTotal' => $this->compare($source->grandTotal, $grandTotal),
        ];

        return new Verification($class, [], $subtotal, $preTaxTotal, $tax, $grandTotal, $checks, $margins);
    }

    /**
     * @return list<string>
     */
    private function unconfirmedInputs(Document $document): array
    {
        $reasons = [];

        if ($document->lines === []) {
            $reasons[] = 'no lines (every live document has at least one)';
        }

        foreach ($document->lines as $index => $line) {
            if (!$line->discountPercent->isZero()) {
                $reasons[] = 'line ' . ($index + 1) . ': percent discount (not used in the source)';
            }
        }

        $header = [
            'document percent discount' => $document->discountPercent,
            'shipping amount' => $document->shippingAmount,
            'shipping tax' => $document->shippingTaxPercent,
            'adjustment' => $document->adjustment,
        ];

        foreach ($header as $name => $value) {
            if (!$value->isZero()) {
                $reasons[] = "$name (always 0 in the source)";
            }
        }

        return $reasons;
    }

    /**
     * @param list<string> $reasons
     */
    private function classify(SourceDocument $source, array &$reasons): FormulaClass
    {
        $document = $source->document;

        if ($reasons !== []) {
            return FormulaClass::Unverified;
        }

        if (!$document->hasLineTax()) {
            return FormulaClass::NoLineTax;
        }

        if ($source->regionId === null) {
            if ($document->taxMode === TaxMode::Individual) {
                return FormulaClass::LineTaxNotApplied;
            }

            if ($document->taxMode === TaxMode::GroupTaxIncluded) {
                return FormulaClass::TaxIncludedInPrice;
            }

            if ($this->sameRateOnAllLines($document) && $document->discountAmount->isZero()) {
                return FormulaClass::GroupTaxAdded;
            }

            $reasons[] = 'group tax with different line rates or with a document discount (not in the source)';

            return FormulaClass::Unverified;
        }

        $reasons[] = "line tax on a document with region_id {$source->regionId} and mode {$document->taxMode->value} "
            . '(after the 2018-07 upgrade no live document has tax on its lines)';

        return FormulaClass::Unverified;
    }

    private function sameRateOnAllLines(Document $document): bool
    {
        $rate = $document->lines[0]->taxPercent;

        foreach ($document->lines as $line) {
            if (!$line->taxPercent->equals($rate)) {
                return false;
            }
        }

        return true;
    }

    private function checkMargin(Line $line): MarginCheck
    {
        if ($line->margin === null) {
            return MarginCheck::Absent;
        }

        $expected = $line->net()->sub($line->purchaseCost);

        if ($this->compare($line->margin, $expected) !== TotalCheck::Mismatch) {
            return MarginCheck::Ok;
        }

        return $line->margin->isZero() ? MarginCheck::NotComputed : MarginCheck::Mismatch;
    }

    private function compare(Decimal $stored, Decimal $expected): TotalCheck
    {
        if ($stored->equals($expected)) {
            return TotalCheck::Exact;
        }

        return $stored->equals($expected->round(Scale::MONEY)) ? TotalCheck::Rounded : TotalCheck::Mismatch;
    }
}
