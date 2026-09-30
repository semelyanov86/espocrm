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
            throw new InvalidValue('A document needs at least one line (every source document has one).');
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
                throw new RuleNotSupported('negative-line', 'D-47', "Line $n: the discount exceeds the line sum.");
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
            throw new RuleNotSupported('negative-total', 'D-47', 'The document discount exceeds the sum of the lines.');
        }

        $preTaxTotal = $subtotal->sub($discount)->add($document->shippingAmount);
        $grandTotal = $preTaxTotal->add($document->adjustment);

        if ($grandTotal->isNegative()) {
            throw new RuleNotSupported('negative-total', 'D-47', 'The adjustment makes the document total negative.');
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
        $this->requireScale($line->quantity, Scale::QUANTITY, "Line $n quantity");
        $this->requireScale($line->unitPrice, Scale::UNIT_PRICE, "Line $n unit price");
        $this->requireScale($line->discountAmount, Scale::MONEY, "Line $n discount");
        $this->requireScale($line->purchaseCost, Scale::MONEY, "Line $n purchase cost");
        $this->checkDiscount($line->discountAmount, $line->discountPercent, "Line $n");

        if (!$line->quantity->isPositive()) {
            throw new RuleNotSupported('non-positive-quantity', 'D-47', "Line $n: quantity must be positive.");
        }

        foreach (['unit price' => $line->unitPrice, 'purchase cost' => $line->purchaseCost] as $name => $value) {
            if ($value->isNegative()) {
                throw new RuleNotSupported('negative-value', 'D-47', "Line $n: negative $name.");
            }
        }

        if (!$line->taxPercent->isZero()) {
            throw new RuleNotSupported('vat', 'D-21', "Line $n: documents are issued without VAT.");
        }
    }

    private function checkHeader(Document $document): void
    {
        $this->requireScale($document->discountAmount, Scale::MONEY, 'Document discount');
        $this->requireScale($document->shippingAmount, Scale::MONEY, 'Shipping amount');
        $this->requireScale($document->adjustment, Scale::MONEY, 'Adjustment');
        $this->checkDiscount($document->discountAmount, $document->discountPercent, 'Document');

        if ($document->shippingAmount->isNegative()) {
            throw new RuleNotSupported('negative-value', 'D-47', 'Negative shipping amount.');
        }

        if (!$document->shippingTaxPercent->isZero()) {
            throw new RuleNotSupported('shipping-tax', 'D-21', 'Shipping is charged without VAT.');
        }
    }

    private function checkDiscount(Decimal $amount, Decimal $percent, string $name): void
    {
        $this->requireScale($percent, Scale::PERCENT, "$name discount percent");

        if ($amount->isNegative() || $percent->isNegative()) {
            throw new RuleNotSupported('negative-value', 'D-47', "$name: negative discount.");
        }

        if ($percent->compare(self::HUNDRED) > 0) {
            throw new InvalidValue("$name: discount percent above 100.");
        }

        if (!$amount->isZero() && !$percent->isZero()) {
            // Vtiger offers one discount type at a time (amount or percent); no source record has both.
            throw new InvalidValue("$name: either a discount amount or a discount percent, not both.");
        }
    }

    private function requireScale(Decimal $value, int $scale, string $name): void
    {
        if ($value->significantScale() > $scale) {
            throw new InvalidValue("$name has more than $scale decimals: {$value->toString()}.");
        }
    }
}
