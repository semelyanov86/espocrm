<?php

declare(strict_types=1);

namespace Itvolga\Tests\Finance;

use Espo\Modules\Itvolga\Tools\Finance\Document;
use Espo\Modules\Itvolga\Tools\Finance\DocumentCalculator;
use Espo\Modules\Itvolga\Tools\Finance\Exceptions\InvalidValue;
use Espo\Modules\Itvolga\Tools\Finance\Exceptions\RuleNotSupported;
use Espo\Modules\Itvolga\Tools\Finance\Line;
use Espo\Modules\Itvolga\Tools\Finance\TaxMode;

/**
 * Documents created in EspoCRM: D-21 (no VAT), D-29 (line sums rounded half up, total = Σ rounded lines).
 */
final class DocumentCalculatorTest extends TestCase
{
    private DocumentCalculator $calculator;

    public function setUp(): void
    {
        $this->calculator = new DocumentCalculator();
    }

    public function testServiceInvoice(): void
    {
        $totals = $this->calculator->calculate(Document::of('individual', [Line::of('1', '15000.00')]));

        $this->assertDecimal('15000', $totals->lineAmounts[0]);
        $this->assertDecimal('15000', $totals->subtotal);
        $this->assertDecimal('15000', $totals->preTaxTotal);
        $this->assertDecimal('0', $totals->taxAmount);
        $this->assertDecimal('15000', $totals->grandTotal);
        $this->assertDecimal('15000', $totals->lineMargins[0]);
    }

    public function testLineSumsAreRoundedHalfUpBeforeTheyAreAdded(): void
    {
        // 3 × 33.335 = 100.005 → 100.01 (a float round() may give 100.00).
        $one = $this->calculator->calculate(Document::of('individual', [Line::of('3', '33.335')]));
        $this->assertDecimal('100.01', $one->grandTotal);

        // Two lines of 0.005 each: Σ rounded lines = 0.02, while rounding the exact sum would give 0.01 (D-29).
        $two = $this->calculator->calculate(Document::of('individual', [Line::of('1', '0.005'), Line::of('1', '0.005')]));
        $this->assertDecimal('0.01', $two->lineAmounts[0]);
        $this->assertDecimal('0.02', $two->subtotal);
        $this->assertDecimal('0.02', $two->grandTotal);

        // Fractional hours with three decimals.
        $hours = $this->calculator->calculate(Document::of('individual', [Line::of('0.333', '100.00'), Line::of('2.125', '1999.99')]));
        $this->assertDecimal('33.3', $hours->lineAmounts[0]);
        $this->assertDecimal('4249.98', $hours->lineAmounts[1]); // 4249.97875
        $this->assertDecimal('4283.28', $hours->grandTotal);
    }

    public function testLineAndDocumentDiscountAmounts(): void
    {
        $document = Document::of('individual', [
            Line::of('1', '10000.00', discountAmount: '1500.00', purchaseCost: '6000.00'),
            Line::of('2', '250.00'),
        ], discountAmount: '1000.00');
        $totals = $this->calculator->calculate($document);

        $this->assertDecimal('8500', $totals->lineAmounts[0]);
        $this->assertDecimal('2500', $totals->lineMargins[0]);
        $this->assertDecimal('9000', $totals->subtotal);
        $this->assertDecimal('1000', $totals->discountAmount);
        $this->assertDecimal('8000', $totals->preTaxTotal);
        $this->assertDecimal('8000', $totals->grandTotal);
    }

    public function testTaxModeWithoutTaxDoesNotChangeTotals(): void
    {
        foreach (TaxMode::cases() as $mode) {
            $totals = $this->calculator->calculate(Document::of($mode, [Line::of('1.5', '1000.00')]));
            $this->assertDecimal('1500', $totals->grandTotal, $mode->value);
        }
    }

    public function testFreeLineIsAllowed(): void
    {
        $totals = $this->calculator->calculate(Document::of('individual', [Line::of('1', '0'), Line::of('1', '100')]));
        $this->assertDecimal('100', $totals->grandTotal);
    }

    public function testRulesWithoutConfirmationAreRefused(): void
    {
        $refused = [
            'vat' => Document::of('individual', [Line::of('1', '100', taxPercent: '20')]),
            'line-discount-percent' => Document::of('individual', [Line::of('1', '100', discountPercent: '10')]),
            'header-discount-percent' => Document::of('individual', [Line::of('1', '100')], discountPercent: '5'),
            'shipping' => Document::of('individual', [Line::of('1', '100')], shippingAmount: '300'),
            'shipping-tax' => Document::of('individual', [Line::of('1', '100')], shippingTaxPercent: '18'),
            'adjustment' => Document::of('individual', [Line::of('1', '100')], adjustment: '-10'),
            'non-positive-quantity' => Document::of('individual', [Line::of('0', '100')]),
            'negative-value' => Document::of('individual', [Line::of('1', '-100')]),
            'negative-line' => Document::of('individual', [Line::of('1', '100', discountAmount: '100.01')]),
            'negative-total' => Document::of('individual', [Line::of('1', '100')], discountAmount: '100.01'),
        ];

        foreach ($refused as $rule => $document) {
            $e = $this->assertThrows(RuleNotSupported::class, fn () => $this->calculator->calculate($document));
            $this->assertSame($rule, $e->rule, "rule of $rule");
            $this->assertSame($rule === 'vat' ? 'D-21' : 'Q-38', $e->reference, "reference of $rule");
        }
    }

    public function testMalformedInputIsRejected(): void
    {
        $this->assertThrows(InvalidValue::class, fn () => Line::of(1.5, '100'), 'Float');
        $this->assertThrows(InvalidValue::class, fn () => Line::of('1', 99.9), 'Float');
        $this->assertThrows(InvalidValue::class,
            fn () => $this->calculator->calculate(Document::of('individual', [Line::of('1.0001', '100')])), 'quantity');
        $this->assertThrows(InvalidValue::class,
            fn () => $this->calculator->calculate(Document::of('individual', [Line::of('1', '100', discountAmount: '0.001')])), 'discount');
        $this->assertThrows(InvalidValue::class,
            fn () => $this->calculator->calculate(Document::of('individual', [Line::of('1', '100')], discountAmount: '0.005')), 'Document discount');
        $this->assertThrows(InvalidValue::class, fn () => $this->calculator->calculate(Document::of('individual', [])), 'at least one line');
        $this->assertThrows(InvalidValue::class, fn () => Document::of('vat18', [Line::of('1', '1')]), 'tax mode');
    }

    public function testCalculationIsRepeatable(): void
    {
        // Saving a document again must not drift its sums.
        $document = Document::of('individual', [Line::of('2.5', '1333.33'), Line::of('1', '0.01')], discountAmount: '0.33');
        $first = $this->calculator->calculate($document);
        $again = $this->calculator->calculate(Document::of('individual', [
            Line::of($first->lineAmounts[0]->toString(), '1'), Line::of($first->lineAmounts[1]->toString(), '1'),
        ], discountAmount: '0.33'));

        $this->assertDecimal('3333.33', $first->lineAmounts[0]); // 3333.325
        $this->assertDecimal('3333.01', $first->grandTotal);
        $this->assertTrue($first->grandTotal->equals($again->grandTotal), 'recalculation from stored line sums differs');
    }
}
