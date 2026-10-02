<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Finance;

use Espo\Modules\Itvolga\Tools\Finance\Exceptions\InvalidValue;
use Espo\Modules\Itvolga\Tools\Finance\Exceptions\RuleNotSupported;

/**
 * Totals of documents created in EspoCRM (Quote, SalesOrder, Invoice, Act), D-47.
 *
 * Line: the discount is an amount or a percent of qty × price (the percent discount is rounded to kopecks); the line
 * sum is rounded to kopecks half up (D-29). Document: subtotal = Σ rounded lines; the document discount is an amount or
 * a percent of the subtotal (rounded to kopecks); pre-tax total = subtotal − discount + shipping; grand total =
 * pre-tax total + adjustment (signed). No VAT and no tax on shipping (D-21). Negative lines and totals and zero
 * quantities stay refused (owner decision Q-38). Imported documents are never recalculated here: their stored totals
 * are the reference (D-05) and SourceVerifier only compares.
 */
final class DocumentCalculator
{
    private const HUNDRED = '100';

    public function calculate(Document $document): Totals
    {
        if ($document->lines === []) {
            throw new InvalidValue('A document needs at least one line (every source document has one).', 'noLines');
        }

        $amounts = [];
        $discounts = [];
        $margins = [];

        foreach ($document->lines as $index => $line) {
            $n = $index + 1;
            $this->checkLine($line, $n);

            $gross = $line->gross();
            $discount = $this->discount($line->discountAmount, $line->discountPercent, $gross);
            $exact = $gross->sub($discount);

            // Checked before rounding: a discount above the line sum must not disappear in the rounding to kopecks.
            if ($exact->isNegative()) {
                throw new RuleNotSupported('negative-line', 'D-47', "Line $n: the discount exceeds the line sum.", $n, 'discountAmount');
            }

            $amount = $exact->round(Scale::MONEY);

            $amounts[] = $amount;
            $discounts[] = $discount;
            $margins[] = $amount->sub($line->purchaseCost);
        }

        $this->checkHeader($document);

        $subtotal = Decimal::sum($amounts);
        $discount = $this->discount($document->discountAmount, $document->discountPercent, $subtotal);

        if ($subtotal->sub($discount)->isNegative()) {
            throw new RuleNotSupported('negative-total', 'D-47', 'The document discount exceeds the sum of the lines.', null,
                'discountAmount');
        }

        $preTaxTotal = $subtotal->sub($discount)->add($document->shippingAmount);
        $grandTotal = $preTaxTotal->add($document->adjustment);

        if ($grandTotal->isNegative()) {
            throw new RuleNotSupported('negative-total', 'D-47', 'The adjustment makes the document total negative.', null,
                'adjustment');
        }

        return new Totals(
            lineAmounts: $amounts,
            lineDiscounts: $discounts,
            lineMargins: $margins,
            subtotal: $subtotal,
            discountAmount: $discount,
            shippingAmount: $document->shippingAmount,
            preTaxTotal: $preTaxTotal,
            taxAmount: Decimal::zero(),
            adjustment: $document->adjustment,
            grandTotal: $grandTotal,
        );
    }

    /**
     * Discount in kopecks: the amount as entered, or the percent of the base rounded half up (Vtiger computes the
     * percent discount of a line from qty × price and of a document from the subtotal, then rounds it to kopecks).
     */
    private function discount(Decimal $amount, Decimal $percent, Decimal $base): Decimal
    {
        return $percent->isZero() ? $amount : $base->percent($percent)->round(Scale::MONEY);
    }

    private function checkLine(Line $line, int $n): void
    {
        $this->requireScale($line->quantity, Scale::QUANTITY, "Line $n quantity", $n, 'quantity');
        $this->requireScale($line->unitPrice, Scale::UNIT_PRICE, "Line $n unit price", $n, 'unitPrice');
        $this->requireScale($line->discountAmount, Scale::MONEY, "Line $n discount", $n, 'discountAmount');
        $this->requireScale($line->purchaseCost, Scale::MONEY, "Line $n purchase cost", $n, 'purchaseCost');
        $this->checkDiscount($line->discountAmount, $line->discountPercent, "Line $n", $n);

        if (!$line->quantity->isPositive()) {
            throw new RuleNotSupported('non-positive-quantity', 'D-47', "Line $n: quantity must be positive.", $n,
                'quantity');
        }

        foreach (['unitPrice' => $line->unitPrice, 'purchaseCost' => $line->purchaseCost] as $field => $value) {
            if ($value->isNegative()) {
                $name = $field === 'unitPrice' ? 'unit price' : 'purchase cost';

                throw new RuleNotSupported('negative-value', 'D-47', "Line $n: negative $name.", $n, $field);
            }
        }

        if (!$line->taxPercent->isZero()) {
            throw new RuleNotSupported('vat', 'D-21', "Line $n: documents are issued without VAT.", $n, 'taxRate');
        }
    }

    private function checkHeader(Document $document): void
    {
        $this->requireScale($document->discountAmount, Scale::MONEY, 'Document discount', null, 'discountAmount');
        $this->requireScale($document->shippingAmount, Scale::MONEY, 'Shipping amount', null, 'shippingAmount');
        $this->requireScale($document->adjustment, Scale::MONEY, 'Adjustment', null, 'adjustment');
        $this->checkDiscount($document->discountAmount, $document->discountPercent, 'Document', null);

        if ($document->shippingAmount->isNegative()) {
            throw new RuleNotSupported('negative-value', 'D-47', 'Negative shipping amount.', null, 'shippingAmount');
        }

        if (!$document->shippingTaxPercent->isZero()) {
            throw new RuleNotSupported('shipping-tax', 'D-21', 'Shipping is charged without VAT.', null,
                'shippingTaxPercent');
        }
    }

    private function checkDiscount(Decimal $amount, Decimal $percent, string $name, ?int $line): void
    {
        $this->requireScale($percent, Scale::PERCENT, "$name discount percent", $line, 'discountPercent');

        if ($amount->isNegative() || $percent->isNegative()) {
            throw new RuleNotSupported('negative-value', 'D-47', "$name: negative discount.", $line,
                $amount->isNegative() ? 'discountAmount' : 'discountPercent');
        }

        if ($percent->compare(self::HUNDRED) > 0) {
            throw new InvalidValue("$name: discount percent above 100.", 'percentAbove100', $line, 'discountPercent');
        }

        if (!$amount->isZero() && !$percent->isZero()) {
            // Vtiger offers one discount type at a time (amount or percent); no source record has both.
            throw new InvalidValue("$name: either a discount amount or a discount percent, not both.", 'bothDiscounts',
                $line, 'discountPercent');
        }
    }

    private function requireScale(Decimal $value, int $scale, string $name, ?int $line, string $field): void
    {
        if ($value->significantScale() > $scale) {
            throw new InvalidValue("$name has more than $scale decimals: {$value->toString()}.", 'tooManyDecimals',
                $line, $field);
        }
    }
}
