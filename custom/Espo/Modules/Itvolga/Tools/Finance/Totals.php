<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Finance;

/**
 * Totals of a document created in EspoCRM (DocumentCalculator).
 */
final class Totals
{
    /**
     * @param list<Decimal> $lineAmounts line sums rounded to kopecks, in line order
     * @param list<Decimal> $lineDiscounts line discounts in kopecks (entered amount or percent of qty × price)
     * @param list<Decimal> $lineMargins line amount − purchase cost, in line order
     */
    public function __construct(
        public readonly array $lineAmounts,
        public readonly array $lineDiscounts,
        public readonly array $lineMargins,
        public readonly Decimal $subtotal,
        /** Document discount in kopecks (entered amount or percent of the subtotal). */
        public readonly Decimal $discountAmount,
        public readonly Decimal $shippingAmount,
        /** subtotal − discount + shipping. */
        public readonly Decimal $preTaxTotal,
        public readonly Decimal $taxAmount,
        /** Signed: added to the pre-tax total. */
        public readonly Decimal $adjustment,
        public readonly Decimal $grandTotal,
    ) {}
}
