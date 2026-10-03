<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Finance\Printing;

use Espo\Modules\Itvolga\Tools\Finance\Decimal;
use Espo\Modules\Itvolga\Tools\Finance\Scale;

/**
 * View model of a print form (stage 05, D-79…D-81) from the stored values of a record: every value becomes a ready
 * string, the templates only place them. Totals are the stored ones (D-05), never recalculated:
 *
 * - discount of the document = subtotal + shipping − pre-tax total (shown when not zero);
 * - VAT = grand total − pre-tax total − adjustment (shown when not zero: the two source invoices of the class
 *   groupTaxAdded); otherwise the forms say «Без налога (НДС)», like the source (D-21);
 * - a line discount is shown in its own column when a line of the document has one: the entered amount, or the
 *   percent of quantity × price rounded to kopecks as DocumentCalculator applies it, so quantity × price − discount
 *   gives the line sum;
 * - a long line description is cut into parts that fit a page (`description` and the continuation rows `more`): the PDF
 *   engine cannot break a table row across pages and would clip it.
 *
 * Input arrays hold decimal strings and texts as stored (null for empty); see document() and cashReceipt().
 */
final class Presenter
{
    public const NO_NUMBER = 'б/н';
    public const NO_SIGNATURE = '_______________';
    public const NO_UNIT = '-';
    /**
     * A description part printed in one table row. It must fit a page even wrapped in the narrowest name column (the
     * act with a discount column, 150 pt at 8 pt: about 20 wide characters a line), so the bound is conservative.
     */
    public const PART_LINES = 20;
    public const PART_CHARS = 400;

    /**
     * Quote, SalesOrder, Invoice, Act.
     *
     * @param array{
     *     number?: ?string,
     *     subject?: ?string,
     *     date?: ?string,
     *     extraDate?: ?string,
     *     seller?: array<string, ?string>,
     *     buyer?: array{name?: ?string, inn?: ?string, kpp?: ?string, phone?: ?string,
     *         documentAddress?: array<string, ?string>, accountAddress?: array<string, ?string>},
     *     lines: list<array<string, ?string>>,
     *     totals: array<string, ?string>,
     *     terms?: ?string,
     *     contact?: ?string,
     *     manager?: ?array<string, ?string>,
     * } $document
     * @return array<string, mixed>
     */
    public static function document(array $document): array
    {
        $rows = self::rows($document['lines']);
        $totals = $document['totals'];
        $grandTotal = Decimal::ofNullable($totals['grandTotal'] ?? null);

        return [
            'number' => self::text($document['number'] ?? null) ?? self::NO_NUMBER,
            'subject' => self::text($document['subject'] ?? null),
            'date' => Formatter::date($document['date'] ?? null),
            'extraDate' => self::text($document['extraDate'] ?? null) !== null
                ? Formatter::date($document['extraDate']) : null,
            'seller' => self::seller($document['seller'] ?? []),
            'buyer' => self::buyer($document['buyer'] ?? []),
            'rows' => $rows,
            'hasDiscount' => in_array(true, array_column($rows, 'hasDiscount'), true),
            'count' => count($rows),
            'totals' => self::totals($totals),
            'words' => AmountInWords::rubles($grandTotal),
            'terms' => self::block($document['terms'] ?? null),
            'contact' => self::text($document['contact'] ?? null),
            'manager' => self::manager($document['manager'] ?? null),
        ];
    }

    /**
     * Cash receipt order (ПКО, КО-1) of an incoming payment.
     *
     * @param array{
     *     number?: ?string,
     *     documentNumber?: ?string,
     *     date?: ?string,
     *     amount: ?string,
     *     payer?: ?string,
     *     purpose?: ?string,
     *     seller?: array<string, ?string>,
     * } $payment
     * @return array<string, mixed>
     */
    public static function cashReceipt(array $payment): array
    {
        $amount = Decimal::ofNullable($payment['amount']);

        return [
            // «Номер документа» of the source form is doc_no; payments without it print their own number (D-81).
            'number' => self::text($payment['documentNumber'] ?? null) ?? self::text($payment['number'] ?? null)
                ?? self::NO_NUMBER,
            'date' => Formatter::numericDate($payment['date'] ?? null),
            'dateLong' => Formatter::date($payment['date'] ?? null),
            'amount' => Formatter::money($amount),
            'words' => AmountInWords::rubles($amount),
            'payer' => self::text($payment['payer'] ?? null) ?? '',
            'purpose' => self::text($payment['purpose'] ?? null) ?? '',
            'seller' => self::seller($payment['seller'] ?? []),
        ];
    }

    /**
     * @param list<array<string, ?string>> $lines
     * @return list<array<string, mixed>>
     */
    private static function rows(array $lines): array
    {
        $rows = [];

        foreach (array_values($lines) as $index => $line) {
            $quantity = Decimal::ofNullable($line['quantity'] ?? null);
            $price = Decimal::ofNullable($line['unitPrice'] ?? null);
            $discountAmount = Decimal::ofNullable($line['discountAmount'] ?? null);
            $discountPercent = Decimal::ofNullable($line['discountPercent'] ?? null);
            $discount = '';

            if (!$discountPercent->isZero()) {
                $discount = Formatter::money($quantity->mul($price)->percent($discountPercent)->round(Scale::MONEY))
                    . ' (' . Formatter::number($discountPercent) . '%)';
            } elseif (!$discountAmount->isZero()) {
                $discount = Formatter::money($discountAmount);
            }

            $parts = self::parts(self::block($line['description'] ?? null));

            $rows[] = [
                'no' => $index + 1,
                'name' => self::text($line['name'] ?? null) ?? '',
                'description' => $parts[0] ?? null,
                'more' => array_slice($parts, 1),
                'unit' => self::text($line['unit'] ?? null) ?? self::NO_UNIT,
                'quantity' => Formatter::quantity($quantity),
                'price' => Formatter::money($price),
                'discount' => $discount,
                'hasDiscount' => $discount !== '',
                'amount' => Formatter::money(Decimal::ofNullable($line['amount'] ?? null)),
            ];
        }

        return $rows;
    }

    /**
     * @param array<string, ?string> $totals subtotal, shippingAmount, preTaxTotal, adjustment, grandTotal
     * @return array<string, ?string>
     */
    private static function totals(array $totals): array
    {
        $subtotal = Decimal::ofNullable($totals['subtotal'] ?? null);
        $shipping = Decimal::ofNullable($totals['shippingAmount'] ?? null);
        $preTax = Decimal::ofNullable($totals['preTaxTotal'] ?? null);
        $adjustment = Decimal::ofNullable($totals['adjustment'] ?? null);
        $grandTotal = Decimal::ofNullable($totals['grandTotal'] ?? null);

        $discount = $subtotal->add($shipping)->sub($preTax);
        $tax = $grandTotal->sub($preTax)->sub($adjustment);

        return [
            'subtotal' => Formatter::money($subtotal),
            'discount' => $discount->isZero() ? null : Formatter::money($discount),
            'shipping' => $shipping->isZero() ? null : Formatter::money($shipping),
            'tax' => $tax->isZero() ? null : Formatter::money($tax),
            'adjustment' => $adjustment->isZero() ? null : Formatter::money($adjustment),
            'grandTotal' => Formatter::money($grandTotal),
        ];
    }

    /**
     * @param array<string, ?string> $seller LegalEntity attributes
     * @return array<string, ?string>
     */
    private static function seller(array $seller): array
    {
        $out = [];

        foreach (['name', 'inn', 'kpp', 'okpo', 'bankAccount', 'bankName', 'bic', 'corrAccount', 'phoneNumber',
            'website', 'logoId'] as $key) {
            $out[$key] = self::text($seller[$key] ?? null) ?? '';
        }

        $out['director'] = self::text($seller['director'] ?? null) ?? self::NO_SIGNATURE;
        $out['bookkeeper'] = self::text($seller['bookkeeper'] ?? null) ?? self::NO_SIGNATURE;
        $address = [
            'postalCode' => $seller['addressPostalCode'] ?? null,
            'state' => $seller['addressState'] ?? null,
            'city' => $seller['addressCity'] ?? null,
            'street' => $seller['addressStreet'] ?? null,
        ];
        $out['address'] = self::address($address);
        // «Новый акт» writes the seller as code, city, street (orgBillingAddress of SalesPlatform).
        $out['shortAddress'] = self::join([$address['postalCode'], $address['city'], $address['street']]);
        $out['line'] = self::join([
            $out['name'],
            self::labelled('ИНН', $out['inn']),
            $out['shortAddress'],
        ]);

        return $out;
    }

    /**
     * The address of the document (its own billing address); an empty one falls back to the account's (D-80).
     *
     * @param array<string, mixed> $buyer
     * @return array<string, string>
     */
    private static function buyer(array $buyer): array
    {
        $address = self::address($buyer['documentAddress'] ?? []);

        if ($address === '') {
            $address = self::address($buyer['accountAddress'] ?? []);
        }

        $name = self::text($buyer['name'] ?? null) ?? '';
        $inn = self::text($buyer['inn'] ?? null) ?? '';
        $kpp = self::text($buyer['kpp'] ?? null) ?? '';
        $phone = self::text($buyer['phone'] ?? null) ?? '';
        $line = self::join([$name, self::labelled('ИНН', $inn), self::labelled('КПП', $kpp), $address]);

        return [
            'name' => $name,
            'inn' => $inn,
            'kpp' => $kpp,
            'phone' => $phone,
            'address' => $address,
            'line' => $line,
            'linePhone' => self::join([$line, self::labelled('тел.:', $phone)]),
        ];
    }

    /**
     * @param ?array<string, ?string> $manager
     * @return ?array<string, string>
     */
    private static function manager(?array $manager): ?array
    {
        $name = self::text($manager['name'] ?? null);

        if ($name === null) {
            return null;
        }

        return [
            'name' => $name,
            'email' => self::text($manager['email'] ?? null) ?? '',
            'phone' => self::text($manager['phone'] ?? null) ?? '',
        ];
    }

    /**
     * «101000, Московская обл., г. Тестовск, ул. Синтетическая, 1» — postal code, region, city, street.
     *
     * @param array<string, ?string> $values postalCode, state, city, street
     */
    private static function address(array $values): string
    {
        $city = self::text($values['city'] ?? null);

        if ($city !== null && !preg_match('/^г\.?\s/u', $city)) {
            $city = 'г. ' . $city;
        }

        return self::join([$values['postalCode'] ?? null, $values['state'] ?? null, $city, $values['street'] ?? null]);
    }

    private static function labelled(string $label, string $value): ?string
    {
        return $value === '' ? null : $label . ' ' . $value;
    }

    /**
     * @param list<?string> $parts
     */
    private static function join(array $parts): string
    {
        return implode(', ', array_filter(array_map(self::text(...), $parts), static fn ($part) => $part !== null));
    }

    /**
     * One line: inner whitespace collapsed, empty → null.
     */
    private static function text(?string $value): ?string
    {
        $value = $value === null ? null : trim(preg_replace('/\s+/u', ' ', $value) ?? '');

        return $value === '' ? null : $value;
    }

    /**
     * Multi-line text (terms, line descriptions): line breaks kept for `white-space: pre-line`, empty → null.
     */
    private static function block(?string $value): ?string
    {
        $value = $value === null ? null : trim(str_replace(["\r\n", "\r"], "\n", $value));

        return $value === '' ? null : $value;
    }

    /**
     * A description cut at line breaks (a line longer than PART_CHARS at spaces) into parts of at most PART_LINES lines
     * and PART_CHARS characters; nothing is dropped.
     *
     * @return list<string>
     */
    private static function parts(?string $text): array
    {
        if ($text === null) {
            return [];
        }

        $pieces = [];

        foreach (explode("\n", $text) as $line) {
            while (mb_strlen($line) > self::PART_CHARS) {
                $cut = mb_strrpos(mb_substr($line, 0, self::PART_CHARS), ' ') ?: self::PART_CHARS;
                $pieces[] = mb_substr($line, 0, $cut);
                $line = ltrim(mb_substr($line, $cut));
            }

            $pieces[] = $line;
        }

        $parts = [];
        $current = [];
        $chars = 0;

        foreach ($pieces as $piece) {
            if ($current !== [] && (count($current) >= self::PART_LINES || $chars + mb_strlen($piece) > self::PART_CHARS)) {
                $parts[] = implode("\n", $current);
                $current = [];
                $chars = 0;
            }

            $current[] = $piece;
            $chars += mb_strlen($piece);
        }

        $parts[] = implode("\n", $current);

        return $parts;
    }
}
