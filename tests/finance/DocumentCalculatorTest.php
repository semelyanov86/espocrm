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
 * Documents created in EspoCRM: D-21 (no VAT), D-29 (line sums rounded half up, total = Σ rounded lines), D-47
 * (discount as amount or percent, shipping without tax, signed adjustment — owner decision Q-38).
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

    public function testPercentDiscounts(): void
    {
        // Line: 10 % of 999.99 = 99.999 → 100.00; line sum 899.99.
        $line = $this->calculator->calculate(Document::of('individual', [Line::of('1', '999.99', discountPercent: '10')]));
        $this->assertDecimal('100', $line->lineDiscounts[0]);
        $this->assertDecimal('899.99', $line->lineAmounts[0]);

        // Line percent with fractional hours: 2.5 × 1333.33 = 3333.325; 7.5 % = 249.999375 → 250.00; 3083.325 → 3083.33.
        $hours = $this->calculator->calculate(Document::of('individual', [Line::of('2.5', '1333.33', discountPercent: '7.5')]));
        $this->assertDecimal('250', $hours->lineDiscounts[0]);
        $this->assertDecimal('3083.33', $hours->lineAmounts[0]);

        // Document: 7 % of 333.33 = 23.3331 → 23.33.
        $document = $this->calculator->calculate(Document::of('individual', [Line::of('1', '333.33')], discountPercent: '7'));
        $this->assertDecimal('23.33', $document->discountAmount);
        $this->assertDecimal('310', $document->preTaxTotal);
        $this->assertDecimal('310', $document->grandTotal);

        // 100 % is allowed and gives a zero document.
        $free = $this->calculator->calculate(Document::of('individual', [Line::of('1', '50')], discountPercent: '100'));
        $this->assertDecimal('0', $free->grandTotal);
    }

    public function testShippingAndAdjustment(): void
    {
        $document = Document::of('individual', [Line::of('2', '1500.00')],
            discountAmount: '200.00', shippingAmount: '350.00', adjustment: '-0.50');
        $totals = $this->calculator->calculate($document);

        $this->assertDecimal('3000', $totals->subtotal);
        $this->assertDecimal('200', $totals->discountAmount);
        $this->assertDecimal('350', $totals->shippingAmount);
        $this->assertDecimal('3150', $totals->preTaxTotal);   // 3000 − 200 + 350
        $this->assertDecimal('-0.5', $totals->adjustment);
        $this->assertDecimal('3149.5', $totals->grandTotal);  // pre-tax + adjustment
        $this->assertDecimal('0', $totals->taxAmount);

        $plus = $this->calculator->calculate(Document::of('individual', [Line::of('1', '100')], adjustment: '15.25'));
        $this->assertDecimal('115.25', $plus->grandTotal);
    }

    public function testRefusedRules(): void
    {
        $refused = [
            'vat' => [Document::of('individual', [Line::of('1', '100', taxPercent: '20')]), 'D-21'],
            'shipping-tax' => [Document::of('individual', [Line::of('1', '100')], shippingAmount: '10', shippingTaxPercent: '18'), 'D-21'],
            'non-positive-quantity' => [Document::of('individual', [Line::of('0', '100')]), 'D-47'],
            'negative-value' => [Document::of('individual', [Line::of('1', '-100')]), 'D-47'],
            'negative-line' => [Document::of('individual', [Line::of('1', '100', discountAmount: '100.01')]), 'D-47'],
            // −0.004 would round to 0.00: the sign is checked before rounding.
            'negative-line (hidden by rounding)' => [Document::of('individual', [Line::of('1', '0.006', discountAmount: '0.01')]), 'D-47'],
            'negative-total' => [Document::of('individual', [Line::of('1', '100')], discountAmount: '100.01'), 'D-47'],
        ];
        $refused['negative-total (adjustment)'] = [Document::of('individual', [Line::of('1', '100')], adjustment: '-100.01'), 'D-47'];
        $refused['negative-value (shipping)'] = [Document::of('individual', [Line::of('1', '100')], shippingAmount: '-1'), 'D-47'];
        $refused['negative-value (discount percent)'] = [Document::of('individual', [Line::of('1', '100', discountPercent: '-5')]), 'D-47'];

        foreach ($refused as $name => [$document, $reference]) {
            $e = $this->assertThrows(RuleNotSupported::class, fn () => $this->calculator->calculate($document));
            $this->assertSame(explode(' ', $name)[0], $e->rule, "rule of $name");
            $this->assertSame($reference, $e->reference, "reference of $name");
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
        $this->assertThrows(InvalidValue::class,
            fn () => $this->calculator->calculate(Document::of('individual', [Line::of('1', '100', discountAmount: '5', discountPercent: '5')])), 'not both');
        $this->assertThrows(InvalidValue::class,
            fn () => $this->calculator->calculate(Document::of('individual', [Line::of('1', '100')], discountAmount: '5', discountPercent: '5')), 'not both');
        $this->assertThrows(InvalidValue::class,
            fn () => $this->calculator->calculate(Document::of('individual', [Line::of('1', '100', discountPercent: '100.001')])), 'percent');
        $this->assertThrows(InvalidValue::class,
            fn () => $this->calculator->calculate(Document::of('individual', [Line::of('1', '100')], discountPercent: '101')), 'above 100');
        $this->assertThrows(InvalidValue::class,
            fn () => $this->calculator->calculate(Document::of('individual', [Line::of('1', '100')], adjustment: '0.001')), 'Adjustment');
        $this->assertThrows(InvalidValue::class,
            fn () => $this->calculator->calculate(Document::of('individual', [Line::of('1', '100')], shippingAmount: '0.001')), 'Shipping');
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
