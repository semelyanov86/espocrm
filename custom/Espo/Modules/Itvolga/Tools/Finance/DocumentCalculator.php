<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Finance;

use Espo\Modules\Itvolga\Tools\Finance\Exceptions\InvalidValue;
use Espo\Modules\Itvolga\Tools\Finance\Exceptions\RuleNotSupported;

/**
 * Totals of documents created in EspoCRM (Quote, SalesOrder, Invoice, Act).
 *
 * Rules: no VAT (D-21); every line sum is rounded to kopecks half up and the document total is the sum of the rounded
 * lines (D-29); a line discount is an amount, the header discount is an amount (both confirmed by source documents).
 * Everything the source data does not confirm — percent discounts, shipping, adjustment, negative lines — is refused
 * with RuleNotSupported until the owner decides (Q-38). Imported documents are never recalculated here: their stored
 * totals are the reference (D-05) and SourceVerifier only compares.
 */
final class DocumentCalculator
{
    public function calculate(Document $document): Totals
    {
        if ($document->lines === []) {
            throw new InvalidValue('A document needs at least one line (every source document has one).');
        }

        $amounts = [];
        $margins = [];

        foreach ($document->lines as $index => $line) {
            $n = $index + 1;
            $this->checkLine($line, $n);

            $amount = $line->net()->round(Scale::MONEY);

            if ($amount->isNegative()) {
                throw new RuleNotSupported('negative-line', 'Q-38', "Line $n: the discount exceeds the line sum.");
            }

            $amounts[] = $amount;
            $margins[] = $amount->sub($line->purchaseCost);
        }

        $this->checkHeader($document);

        $subtotal = Decimal::sum($amounts);
        $preTaxTotal = $subtotal->sub($document->discountAmount);

        if ($preTaxTotal->isNegative()) {
            throw new RuleNotSupported('negative-total', 'Q-38', 'The document discount exceeds the sum of the lines.');
        }

        return new Totals(
            lineAmounts: $amounts,
            lineMargins: $margins,
            subtotal: $subtotal,
            discountAmount: $document->discountAmount,
            preTaxTotal: $preTaxTotal,
            taxAmount: Decimal::zero(),
            grandTotal: $preTaxTotal,
        );
    }

    private function checkLine(Line $line, int $n): void
    {
        $this->requireScale($line->quantity, Scale::QUANTITY, "Line $n quantity");
        $this->requireScale($line->unitPrice, Scale::UNIT_PRICE, "Line $n unit price");
        $this->requireScale($line->discountAmount, Scale::MONEY, "Line $n discount");
        $this->requireScale($line->purchaseCost, Scale::MONEY, "Line $n purchase cost");

        if (!$line->quantity->isPositive()) {
            throw new RuleNotSupported('non-positive-quantity', 'Q-38', "Line $n: quantity must be positive.");
        }

        foreach (['unit price' => $line->unitPrice, 'discount' => $line->discountAmount, 'purchase cost' => $line->purchaseCost] as $name => $value) {
            if ($value->isNegative()) {
                throw new RuleNotSupported('negative-value', 'Q-38', "Line $n: negative $name.");
            }
        }

        if (!$line->discountPercent->isZero()) {
            throw new RuleNotSupported('line-discount-percent', 'Q-38', "Line $n: percent discounts are not used in the source.");
        }

        if (!$line->taxPercent->isZero()) {
            throw new RuleNotSupported('vat', 'D-21', "Line $n: documents are issued without VAT.");
        }
    }

    private function checkHeader(Document $document): void
    {
        $this->requireScale($document->discountAmount, Scale::MONEY, 'Document discount');

        if ($document->discountAmount->isNegative()) {
            throw new RuleNotSupported('negative-value', 'Q-38', 'Negative document discount.');
        }

        $unconfirmed = [
            'header-discount-percent' => $document->discountPercent,
            'shipping' => $document->shippingAmount,
            'shipping-tax' => $document->shippingTaxPercent,
            'adjustment' => $document->adjustment,
        ];

        foreach ($unconfirmed as $rule => $value) {
            if (!$value->isZero()) {
                throw new RuleNotSupported($rule, 'Q-38', "The source never uses $rule: no confirmed rule.");
            }
        }
    }

    private function requireScale(Decimal $value, int $scale, string $name): void
    {
        if ($value->significantScale() > $scale) {
            throw new InvalidValue("$name has more than $scale decimals: {$value->toString()}.");
        }
    }
}
