<?php

declare(strict_types=1);

namespace Itvolga\Tests\Finance;

use Espo\Modules\Itvolga\Tools\Finance\Editing\DocumentEditor;
use Espo\Modules\Itvolga\Tools\Finance\Editing\HeaderInputs;
use Espo\Modules\Itvolga\Tools\Finance\Editing\LineInput;
use Espo\Modules\Itvolga\Tools\Finance\Editing\StoredDocument;
use Espo\Modules\Itvolga\Tools\Finance\Exceptions\InvalidValue;
use Espo\Modules\Itvolga\Tools\Finance\Exceptions\RuleNotSupported;

/**
 * Edit rule of documents (stage 04.2, owner decision 2026-10-01): new documents are calculated (D-47); saved ones
 * are recalculated only when a calculation input changes; an imported document keeps its source totals (D-05) until
 * then, and its historical 18 % lines are refused on recalculation (D-21).
 */
final class DocumentEditorTest extends TestCase
{
    private DocumentEditor $editor;

    public function setUp(): void
    {
        $this->editor = new DocumentEditor();
    }

    public function testNewDocumentIsCalculatedAndCopiedIdsAreDropped(): void
    {
        $plan = $this->editor->plan(null, self::header(), [
            self::line(['id' => 'other-doc-item', 'quantity' => '3', 'unitPrice' => '33.335']),
            self::line(['quantity' => '1.5', 'unitPrice' => '1000', 'discountPercent' => '10', 'purchaseCost' => '100']),
        ]);

        $this->assertTrue($plan->recalculated);
        $this->assertSame(null, $plan->lines[0]->input->id, 'ids of a copied document are not reused');
        $this->assertSame([1, 2], [$plan->lines[0]->order, $plan->lines[1]->order]);
        $this->assertDecimal('100.01', $plan->lines[0]->amount);
        $this->assertDecimal('1350', $plan->lines[1]->amount);
        $this->assertDecimal('1250', $plan->lines[1]->margin);
        $this->assertDecimal('1450.01', $plan->totals?->grandTotal);
        $this->assertSame(false, $plan->replacesSourceTotals);
        $this->assertSame([], $plan->removedIds);
    }

    public function testNewDocumentNeedsALine(): void
    {
        $e = $this->assertThrows(InvalidValue::class, fn () => $this->editor->plan(null, self::header(), []));
        $this->assertSame('noLines', $e->key);
    }

    public function testUnchangedInputsKeepStoredTotals(): void
    {
        $stored = self::stored([['id' => 'a', 'quantity' => '2.000', 'unitPrice' => '10.00000000']]);

        // The same values written differently, the stored lines (null) and a header with the same values.
        foreach ([[self::line(['id' => 'a', 'quantity' => '2', 'unitPrice' => '10'])], null] as $lines) {
            $plan = $this->editor->plan($stored, self::header(['discountAmount' => '0.00']), $lines);
            $this->assertSame(false, $plan->recalculated);
            $this->assertSame(null, $plan->totals);
            $this->assertSame(null, $plan->lines[0]->amount, 'stored amount kept');
        }
    }

    public function testProductDescriptionAndOrderAreNotCalculationInputs(): void
    {
        $stored = self::stored([
            ['id' => 'a', 'quantity' => '1', 'unitPrice' => '10'],
            ['id' => 'b', 'quantity' => '1', 'unitPrice' => '20'],
        ], true);

        $plan = $this->editor->plan($stored, self::header(), [
            self::line(['id' => 'b', 'quantity' => '1', 'unitPrice' => '20', 'productId' => 'p2', 'description' => 'new']),
            self::line(['id' => 'a', 'quantity' => '1', 'unitPrice' => '10']),
        ]);

        $this->assertSame(false, $plan->recalculated);
        $this->assertSame(false, $plan->replacesSourceTotals, 'source totals survive a non-money edit');
        $this->assertSame(['b', 'a'], [$plan->lines[0]->input->id, $plan->lines[1]->input->id]);
        $this->assertSame([1, 2], [$plan->lines[0]->order, $plan->lines[1]->order]);
        $this->assertSame('p2', $plan->lines[0]->input->productId);
    }

    public function testLineChangesRecalculate(): void
    {
        $stored = self::stored([
            ['id' => 'a', 'quantity' => '1', 'unitPrice' => '10'],
            ['id' => 'b', 'quantity' => '1', 'unitPrice' => '20'],
        ]);

        $changedQuantity = $this->editor->plan($stored, self::header(), [
            self::line(['id' => 'a', 'quantity' => '2', 'unitPrice' => '10']),
            self::line(['id' => 'b', 'quantity' => '1', 'unitPrice' => '20']),
        ]);
        $this->assertTrue($changedQuantity->recalculated);
        $this->assertDecimal('40', $changedQuantity->totals?->grandTotal);

        $removed = $this->editor->plan($stored, self::header(), [self::line(['id' => 'b', 'quantity' => '1', 'unitPrice' => '20'])]);
        $this->assertTrue($removed->recalculated);
        $this->assertSame(['a'], $removed->removedIds);
        $this->assertDecimal('20', $removed->totals?->grandTotal);
        $this->assertSame(1, $removed->lines[0]->order);

        $added = $this->editor->plan($stored, self::header(), [
            self::line(['id' => 'a', 'quantity' => '1', 'unitPrice' => '10']),
            self::line(['id' => 'b', 'quantity' => '1', 'unitPrice' => '20']),
            self::line(['quantity' => '1', 'unitPrice' => '0.01']),
        ]);
        $this->assertTrue($added->recalculated);
        $this->assertDecimal('30.01', $added->totals?->grandTotal);

        foreach (['discountAmount', 'discountPercent', 'taxRate', 'purchaseCost'] as $field) {
            $plan = $this->editor->plan($stored, self::header(), [
                self::line(['id' => 'a', 'quantity' => '1', 'unitPrice' => '10', $field => $field === 'taxRate' ? '0.000' : '1']),
                self::line(['id' => 'b', 'quantity' => '1', 'unitPrice' => '20']),
            ]);
            $this->assertSame($field !== 'taxRate', $plan->recalculated, "$field change");
        }
    }

    public function testHeaderChangesRecalculateTheStoredLines(): void
    {
        $stored = self::stored([['id' => 'a', 'quantity' => '1', 'unitPrice' => '100']]);
        $cases = [
            'discountAmount' => ['10', '90'],
            'discountPercent' => ['5', '95'],
            'shippingAmount' => ['7.5', '107.5'],
            'adjustment' => ['-0.5', '99.5'],
        ];

        foreach ($cases as $field => [$value, $total]) {
            $plan = $this->editor->plan($stored, self::header([$field => $value]), null);
            $this->assertTrue($plan->recalculated, $field);
            $this->assertDecimal($total, $plan->totals?->grandTotal, $field);
        }

        $mode = $this->editor->plan($stored, self::header(['taxMode' => 'group_tax_inc']), null);
        $this->assertTrue($mode->recalculated, 'taxMode');
        $this->assertDecimal('100', $mode->totals?->grandTotal);
    }

    public function testImportedDocumentIsRecalculatedOnlyWhenTheHistoricalTaxIsCleared(): void
    {
        $stored = self::stored([
            ['id' => 'a', 'quantity' => '1', 'unitPrice' => '1000', 'taxRate' => '18.000'],
            ['id' => 'b', 'quantity' => '2', 'unitPrice' => '500', 'taxRate' => '18.000'],
        ], true);

        // A money edit keeps the historical rate of line 2 → refused there, with the line and field.
        $e = $this->assertThrows(RuleNotSupported::class, fn () => $this->editor->plan($stored, self::header(), [
            self::line(['id' => 'a', 'quantity' => '2', 'unitPrice' => '1000', 'taxRate' => '0']),
            self::line(['id' => 'b', 'quantity' => '2', 'unitPrice' => '500', 'taxRate' => '18']),
        ]));
        $this->assertSame(['vat', 2, 'taxRate'], [$e->rule, $e->documentLine, $e->field]);

        $plan = $this->editor->plan($stored, self::header(), [
            self::line(['id' => 'a', 'quantity' => '2', 'unitPrice' => '1000', 'taxRate' => '0']),
            self::line(['id' => 'b', 'quantity' => '2', 'unitPrice' => '500', 'taxRate' => '0']),
        ]);
        $this->assertTrue($plan->recalculated);
        $this->assertTrue($plan->replacesSourceTotals, 'the caller keeps the source totals');
        $this->assertDecimal('3000', $plan->totals?->grandTotal);
    }

    public function testItemsOfOtherDocumentsAreRefused(): void
    {
        $stored = self::stored([['id' => 'a', 'quantity' => '1', 'unitPrice' => '10']]);

        foreach ([[self::line(['id' => 'x', 'quantity' => '1', 'unitPrice' => '10'])],
                  [self::line(['id' => 'a', 'quantity' => '1', 'unitPrice' => '10']), self::line(['id' => 'a', 'quantity' => '1', 'unitPrice' => '10'])]]
                 as $lines) {
            $e = $this->assertThrows(InvalidValue::class, fn () => $this->editor->plan($stored, self::header(), $lines));
            $this->assertSame('unknownLine', $e->key);
        }
    }

    public function testLineInputValues(): void
    {
        $float = $this->assertThrows(InvalidValue::class, fn () => LineInput::fromArray(
            ['productId' => 'p', 'quantity' => 1.5, 'unitPrice' => '1'], 3));
        $this->assertSame(['float', 3, 'quantity'], [$float->key, $float->documentLine, $float->field]);

        foreach (['1,5', '1e3', ' 1', '+1', '.5', true] as $bad) {
            $e = $this->assertThrows(InvalidValue::class, fn () => LineInput::fromArray(
                ['productId' => 'p', 'quantity' => '1', 'unitPrice' => $bad], 1));
            $this->assertSame('notDecimal', $e->key, var_export($bad, true));
        }

        $missing = $this->assertThrows(InvalidValue::class, fn () => LineInput::fromArray(['productId' => 'p', 'unitPrice' => '1'], 1));
        $this->assertSame(['required', 'quantity'], [$missing->key, $missing->field]);
        $product = $this->assertThrows(InvalidValue::class, fn () => LineInput::fromArray(['quantity' => '1', 'unitPrice' => '1'], 2));
        $this->assertSame(['required', 'product'], [$product->key, $product->field]);

        $line = LineInput::fromArray(['productId' => 'p', 'quantity' => 2, 'unitPrice' => '3.5', 'discountAmount' => '',
            'amount' => 'ignored', 'margin' => 999.5], 1);
        $this->assertDecimal('0', $line->value('discountAmount'), 'empty optional value is zero');
        $this->assertSame('2|3.5|0|0|0|0', $line->calculationKey(), 'outputs are not inputs');
    }

    public function testHeaderInputValues(): void
    {
        $this->assertSame('taxMode', $this->assertThrows(InvalidValue::class, fn () => HeaderInputs::fromArray(['taxMode' => 'vat20']))->key);
        $float = $this->assertThrows(InvalidValue::class, fn () => HeaderInputs::fromArray(['adjustment' => -0.5]));
        $this->assertSame(['float', null, 'adjustment'], [$float->key, $float->documentLine, $float->field]);
        $this->assertTrue(HeaderInputs::fromArray([])->equals(self::header()), 'empty inputs are the defaults');
    }

    public function testValuesMustFitTheColumns(): void
    {
        // DECIMAL(25,8) has 17 integer digits; the non-strict sql_mode would clamp a larger value silently.
        $header = $this->assertThrows(InvalidValue::class, fn () => $this->editor->plan(null,
            self::header(['shippingAmount' => '1' . str_repeat('0', 17)]), [self::line(['quantity' => '1', 'unitPrice' => '1'])]));
        $this->assertSame(['tooLarge', 'shippingAmount'], [$header->key, $header->field]);

        // Each input fits, the computed line amount (DECIMAL(25,8)) does not.
        $amount = $this->assertThrows(InvalidValue::class, fn () => $this->editor->plan(null, self::header(),
            [self::line(['quantity' => '1' . str_repeat('0', 9), 'unitPrice' => '1' . str_repeat('0', 9)])]));
        $this->assertSame(['tooLarge', 1, 'amount'], [$amount->key, $amount->documentLine, $amount->field]);

        $scale = $this->assertThrows(InvalidValue::class, fn () => $this->editor->plan(null, self::header(),
            [self::line(['quantity' => '1.0001', 'unitPrice' => '1'])]));
        $this->assertSame(['tooManyDecimals', 1, 'quantity'], [$scale->key, $scale->documentLine, $scale->field]);
    }

    public function testCalculatorRefusalsCarryLineAndField(): void
    {
        $cases = [
            [['quantity' => '0', 'unitPrice' => '1'], 'non-positive-quantity', 'quantity'],
            [['quantity' => '1', 'unitPrice' => '1', 'discountAmount' => '2'], 'negative-line', 'discountAmount'],
            [['quantity' => '1', 'unitPrice' => '-1'], 'negative-value', 'unitPrice'],
        ];

        foreach ($cases as [$values, $rule, $field]) {
            $e = $this->assertThrows(RuleNotSupported::class, fn () => $this->editor->plan(null, self::header(),
                [self::line(['quantity' => '1', 'unitPrice' => '1']), self::line($values)]));
            $this->assertSame([$rule, 2, $field], [$e->rule, $e->documentLine, $e->field]);
        }

        $both = $this->assertThrows(InvalidValue::class, fn () => $this->editor->plan(null,
            self::header(['discountAmount' => '1', 'discountPercent' => '1']), [self::line(['quantity' => '1', 'unitPrice' => '10'])]));
        $this->assertSame(['bothDiscounts', null], [$both->key, $both->documentLine]);
    }

    /**
     * @param array<string, mixed> $values
     */
    private static function header(array $values = []): HeaderInputs
    {
        return HeaderInputs::fromArray($values);
    }

    /**
     * @param array<string, mixed> $values
     */
    private static function line(array $values): LineInput
    {
        return LineInput::fromArray($values + ['productId' => 'p1'], 1);
    }

    /**
     * @param list<array<string, mixed>> $lines
     */
    private static function stored(array $lines, bool $hasSourceTotals = false): StoredDocument
    {
        return new StoredDocument(self::header(), array_map(static fn (array $l) => self::line($l), $lines), $hasSourceTotals);
    }
}
