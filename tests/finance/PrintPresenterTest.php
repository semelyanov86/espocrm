<?php

declare(strict_types=1);

namespace Itvolga\Tests\Finance;

use Espo\Modules\Itvolga\Tools\Finance\Printing\Formatter;
use Espo\Modules\Itvolga\Tools\Finance\Printing\Presenter;

/**
 * View model of the print forms (stage 05): stored totals as printed values, the discount column, the VAT row of
 * historical documents, the buyer address, the PKO number and the blanks of empty values. Synthetic values only.
 */
final class PrintPresenterTest extends TestCase
{
    public function testNewDocumentWithoutDiscountsPrintsStoredValues(): void
    {
        $view = Presenter::document($this->document());

        $this->assertSame('С-9001', $view['number']);
        $this->assertSame('3 октября 2026 г.', $view['date']);
        $this->assertSame(null, $view['extraDate']);
        $this->assertSame(2, $view['count']);
        $this->assertSame(false, $view['hasDiscount']);
        $this->assertSame('2,5', $view['rows'][1]['quantity']);
        $this->assertSame('1' . Formatter::NBSP . '800,00', $view['rows'][1]['price']);
        $this->assertSame('Часы', $view['rows'][1]['unit']);
        $this->assertSame(Presenter::NO_UNIT, $view['rows'][0]['unit']);
        $this->assertSame("за октябрь\nвторая строка", $view['rows'][0]['description']);
        $this->assertSame([
            'subtotal' => '19' . Formatter::NBSP . '500,00',
            'discount' => null,
            'shipping' => null,
            'tax' => null,
            'adjustment' => null,
            'grandTotal' => '19' . Formatter::NBSP . '500,00',
        ], $view['totals']);
        $this->assertSame('Девятнадцать тысяч пятьсот рублей 00 копеек', $view['words']);
    }

    public function testLongDescriptionsAreCutIntoPagePartsWithoutLoss(): void
    {
        $document = $this->document();
        $lines = array_map(static fn (int $n) => sprintf('LINE%03d', $n), range(1, 45));
        $long = str_repeat('слово ', 300);
        $document['lines'][0]['description'] = implode("\n", $lines) . "\n" . $long;

        $row = Presenter::document($document)['rows'][0];
        $parts = [$row['description'], ...$row['more']];

        // Nothing is dropped: a long line is cut at spaces, so only white space differs.
        $words = static fn (string $text) => preg_split('/\s+/u', trim($text));
        $this->assertSame($words(implode("\n", $lines) . "\n" . $long), $words(implode("\n", $parts)));
        foreach ($parts as $part) {
            $this->assertTrue(count(explode("\n", $part)) <= Presenter::PART_LINES, 'lines per part');
            $this->assertTrue(mb_strlen(str_replace("\n", '', $part)) <= Presenter::PART_CHARS, 'characters per part');
        }
        $this->assertSame('LINE001', explode("\n", $row['description'])[0]);
        // 20 + 20 + 5 short lines, then 1 800 characters of one line cut into parts of at most PART_CHARS.
        $this->assertSame(3 + (int) ceil(mb_strlen(trim($long)) / Presenter::PART_CHARS), count($parts));
        // An ordinary description stays in its row.
        $this->assertSame([], Presenter::document($this->document())['rows'][0]['more']);
    }

    public function testDiscountColumnShowsTheDiscountTheCalculatorApplied(): void
    {
        $document = $this->document();
        // 3 × 33.335 with 10 %: 100.005 × 10 / 100 = 10.0005 → 10.00; the line sum 90.01 = round(100.005 − 10.00).
        $document['lines'][0] = ['name' => 'Услуга', 'quantity' => '3.000', 'unitPrice' => '33.33500000',
            'discountAmount' => '0', 'discountPercent' => '10.000', 'amount' => '90.01000000'];
        $document['lines'][1]['discountAmount'] = '500.00000000';
        $document['lines'][1]['amount'] = '4000.00000000';

        $view = Presenter::document($document);

        $this->assertSame(true, $view['hasDiscount']);
        $this->assertSame('10,00 (10%)', $view['rows'][0]['discount']);
        $this->assertSame('33,335', $view['rows'][0]['price']);
        $this->assertSame('500,00', $view['rows'][1]['discount']);
        $this->assertSame('', Presenter::document($this->document())['rows'][0]['discount']);
    }

    public function testDocumentDiscountShippingAndAdjustmentRows(): void
    {
        $document = $this->document();
        $document['totals'] = ['subtotal' => '19500.00', 'shippingAmount' => '300.00', 'preTaxTotal' => '18800.00',
            'adjustment' => '-0.50', 'grandTotal' => '18799.50'];

        $totals = Presenter::document($document)['totals'];

        $this->assertSame('1' . Formatter::NBSP . '000,00', $totals['discount']);
        $this->assertSame('300,00', $totals['shipping']);
        $this->assertSame('-0,50', $totals['adjustment']);
        $this->assertSame(null, $totals['tax']);
    }

    public function testHistoricalTaxClasses(): void
    {
        // lineTaxNotApplied: 18 % in the lines, not in the totals — «Без налога (НДС)», stored totals.
        $document = $this->document();
        $document['lines'][0]['taxRate'] = '18.000';
        $this->assertSame(null, Presenter::document($document)['totals']['tax']);

        // groupTaxAdded: total = pre-tax + 18 % — the VAT row reconciles lines and total.
        $document['totals'] = ['subtotal' => '2500.00', 'shippingAmount' => '0', 'preTaxTotal' => '2500.00',
            'adjustment' => '0', 'grandTotal' => '2950.00'];
        $view = Presenter::document($document);
        $this->assertSame('450,00', $view['totals']['tax']);
        $this->assertSame('2' . Formatter::NBSP . '950,00', $view['totals']['grandTotal']);
        $this->assertSame('Две тысячи девятьсот пятьдесят рублей 00 копеек', $view['words']);
    }

    public function testBuyerAddressOfTheDocumentFirst(): void
    {
        $document = $this->document();
        $buyer = Presenter::document($document)['buyer'];

        $this->assertSame('620000, Свердловская обл., г. Примерград, пр. Образцов, 10', $buyer['address']);
        $this->assertSame('ООО «Покупатель», ИНН 77-SYNTH-01, КПП 770-SYNTH, ' . $buyer['address'], $buyer['line']);
        $this->assertSame($buyer['line'] . ', тел.: +7 SYNTH', $buyer['linePhone']);

        // An empty document address falls back to the account's; «г.» is not doubled.
        $document['buyer']['documentAddress'] = ['postalCode' => ' ', 'city' => null];
        $this->assertSame('г. Тестовск, ул. Счётная, 5', Presenter::document($document)['buyer']['address']);

        // A partial document address is used as it is.
        $document['buyer']['documentAddress'] = ['city' => 'Примерград'];
        $this->assertSame('г. Примерград', Presenter::document($document)['buyer']['address']);

        // Empty requisites are skipped, not printed as «ИНН ,».
        $document['buyer'] = ['name' => 'ИП Синтетика'];
        $this->assertSame('ИП Синтетика', Presenter::document($document)['buyer']['line']);
    }

    public function testSellerRequisitesAndBlanks(): void
    {
        $seller = Presenter::document($this->document())['seller'];

        $this->assertSame('101000, Московская обл., г. Тестовск, ул. Синтетическая, 1', $seller['address']);
        $this->assertSame('101000, Тестовск, ул. Синтетическая, 1', $seller['shortAddress']);
        $this->assertSame('ООО «Продавец», ИНН 50-SYNTH-02, 101000, Тестовск, ул. Синтетическая, 1', $seller['line']);
        $this->assertSame('Тестов Т. Т.', $seller['director']);

        $document = $this->document();
        $document['seller'] = [];
        $document['number'] = ' ';
        $document['date'] = null;
        $view = Presenter::document($document);
        $this->assertSame(Presenter::NO_SIGNATURE, $view['seller']['director']);
        $this->assertSame(Presenter::NO_SIGNATURE, $view['seller']['bookkeeper']);
        $this->assertSame('', $view['seller']['inn']);
        $this->assertSame(Presenter::NO_NUMBER, $view['number']);
        $this->assertSame(Formatter::BLANK_DATE, $view['date']);
    }

    public function testCashReceiptNumberIsTheDocumentNumberThenThePaymentNumber(): void
    {
        $payment = ['number' => '991', 'documentNumber' => '77', 'date' => '2026-10-03', 'amount' => '19500.00000000',
            'payer' => 'ООО «Покупатель»', 'purpose' => 'Оплата по счёту', 'seller' => ['name' => 'ООО «Продавец»']];

        $view = Presenter::cashReceipt($payment);
        $this->assertSame('77', $view['number']);
        $this->assertSame('03.10.2026', $view['date']);
        $this->assertSame('3 октября 2026 г.', $view['dateLong']);
        $this->assertSame('19' . Formatter::NBSP . '500,00', $view['amount']);
        $this->assertSame('Девятнадцать тысяч пятьсот рублей 00 копеек', $view['words']);
        $this->assertSame(Presenter::NO_SIGNATURE, $view['seller']['bookkeeper']);

        $payment['documentNumber'] = null;
        $this->assertSame('991', Presenter::cashReceipt($payment)['number']);
        $payment['number'] = '';
        $this->assertSame(Presenter::NO_NUMBER, Presenter::cashReceipt($payment)['number']);
    }

    /**
     * @return array<string, mixed>
     */
    private function document(): array
    {
        return [
            'number' => 'С-9001',
            'date' => '2026-10-03',
            'seller' => [
                'name' => 'ООО «Продавец»', 'inn' => '50-SYNTH-02', 'kpp' => '500-SYNTH', 'director' => 'Тестов Т. Т.',
                'addressPostalCode' => '101000', 'addressState' => 'Московская обл.', 'addressCity' => 'Тестовск',
                'addressStreet' => 'ул. Синтетическая, 1',
            ],
            'buyer' => [
                'name' => 'ООО «Покупатель»', 'inn' => '77-SYNTH-01', 'kpp' => '770-SYNTH', 'phone' => '+7 SYNTH',
                'documentAddress' => ['postalCode' => '620000', 'state' => 'Свердловская обл.', 'city' => 'Примерград',
                    'street' => 'пр. Образцов, 10'],
                'accountAddress' => ['city' => 'г. Тестовск', 'street' => 'ул. Счётная, 5'],
            ],
            'lines' => [
                ['name' => 'Абонентское обслуживание', 'description' => "за октябрь\r\nвторая строка", 'unit' => null,
                    'quantity' => '1.000', 'unitPrice' => '15000.00000000', 'discountAmount' => '0.00000000',
                    'discountPercent' => '0.000', 'amount' => '15000.00000000'],
                ['name' => 'Настройка сети', 'description' => null, 'unit' => 'Часы', 'quantity' => '2.500',
                    'unitPrice' => '1800.00000000', 'discountAmount' => null, 'discountPercent' => null,
                    'amount' => '4500.00000000'],
            ],
            'totals' => ['subtotal' => '19500.00000000', 'shippingAmount' => '0.00000000',
                'preTaxTotal' => '19500.00000000', 'adjustment' => '0.00000000', 'grandTotal' => '19500.00000000'],
        ];
    }
}
