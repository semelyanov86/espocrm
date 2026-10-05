<?php

declare(strict_types=1);

namespace Itvolga\Tests\Reports;

use DateTimeZone;
use Espo\Modules\Itvolga\Tools\Report\Core\Export\CellText;
use Espo\Modules\Itvolga\Tools\Report\Core\Export\CsvWriter;
use Espo\Modules\Itvolga\Tools\Report\Core\Export\FlatSheet;
use Espo\Modules\Itvolga\Tools\Report\Core\Export\LimitNotes;
use Espo\Modules\Itvolga\Tools\Report\Core\Export\OutputWords;
use Espo\Modules\Itvolga\Tools\Report\Core\Export\ScreenHtml;
use Espo\Modules\Itvolga\Tools\Report\Core\Export\Sheet;
use Espo\Modules\Itvolga\Tools\Report\Core\Export\SheetCell;
use Espo\Modules\Itvolga\Tools\Report\Core\Export\SheetNumber;
use Itvolga\Tests\Finance\TestCase;

/**
 * Files and print view of a result (D-116…D-120): the flat sheet of the four report types (typed cells, currency
 * columns, totals, repeated parent groups), CSV (BOM, delimiter, formulas), the exact boundary of spreadsheet numbers,
 * the screen table of the PDF and the print (escaping, matrix header, orientation) and the limit notes.
 */
final class ExportTest extends TestCase
{
    private OutputWords $words;
    private DateTimeZone $moscow;

    public function setUp(): void
    {
        $this->words = new OutputWords(total: 'Итого', currency: 'Валюта', mixedCurrencies: 'разные валюты',
            noData: 'Нет данных', column: 'Колонка', function: 'Функция', value: 'Значение',
            functions: ['SUM' => 'Сумма', 'AVG' => 'Среднее', 'MIN' => 'Минимум', 'MAX' => 'Максимум']);
        $this->moscow = new DateTimeZone('Europe/Moscow');
    }

    private static function money(string $v, string $cur = 'RUB'): array
    {
        return ['v' => $v, 'f' => $v . ' ₽', 'cur' => $cur];
    }

    /**
     * @return list<list<string>> kinds and values of the rows, «kind:value»
     */
    private static function dump(Sheet $sheet): array
    {
        return array_map(fn ($row) => [$row['kind'], ...array_map(fn (SheetCell $c) =>
            $c->kind === SheetCell::EMPTY ? '' : $c->kind[0] . ':' . $c->value, $row['cells'])], $sheet->rows);
    }

    private function tabular(): array
    {
        return [
            'type' => 'tabular',
            'columns' => [
                ['key' => 'c:name', 'label' => '=Название', 'fieldType' => 'varchar', 'numeric' => false],
                ['key' => 'c:grandTotal', 'label' => 'Итого', 'fieldType' => 'currency', 'numeric' => true],
                ['key' => 'c:createdAt', 'label' => 'Создан', 'fieldType' => 'datetime', 'numeric' => false],
                ['key' => 'c:dateInvoiced', 'label' => 'Дата', 'fieldType' => 'date', 'numeric' => false],
                ['key' => 'c:status', 'label' => 'Статус', 'fieldType' => 'enum', 'numeric' => false],
            ],
            'calculations' => [['key' => 'k:k1', 'label' => 'Расчёт']],
            'rows' => [
                ['id' => 'i1', 'cells' => [['v' => '+7 999', 'f' => '+7 999'], self::money('19500.00000000'),
                    ['v' => '2026-10-04 21:30:00', 'f' => '05.10.2026 00:30'], ['v' => '2026-10-01', 'f' => '01.10.2026'],
                    ['v' => 'Draft', 'f' => 'Черновик']], 'calc' => [['v' => '1.5', 'f' => '1,50']]],
                ['id' => 'i2', 'cells' => [['v' => 'Б', 'f' => 'Б'], ['v' => null, 'f' => ''], ['v' => null, 'f' => ''],
                    ['v' => null, 'f' => ''], ['v' => null, 'f' => '']], 'calc' => [['v' => null, 'f' => '']]],
            ],
            'totals' => ['c:grandTotal' => ['SUM' => self::money('19500.00000000'),
                'MAX' => ['v' => null, 'f' => 'разные валюты', 'mixed' => true]]],
            'calculationTotals' => ['k:k1' => ['SUM' => ['v' => '1.5', 'f' => '1,50']]],
            'limits' => ['rowLimit' => 2, 'rowLimitHit' => true, 'capHit' => false, 'maxRows' => 5000],
        ];
    }

    public function testTabularSheet(): void
    {
        $sheet = FlatSheet::build($this->tabular(), $this->words, $this->moscow, ['Ограничено: 2']);

        $this->assertSame(['=Название', 'Итого', 'Валюта', 'Создан', 'Дата', 'Статус', 'Расчёт'], $sheet->header);
        $this->assertSame([
            ['data', 't:+7 999', 'n:19500.00000000', 't:RUB', 'd:2026-10-05 00:30', 'd:2026-10-01', 't:Черновик', 'n:1.5'],
            ['data', 't:Б', '', '', '', '', '', ''],
            ['blank'],
            ['header', 't:Колонка', 't:Функция', 't:Значение', 't:Валюта'],
            ['total', 't:Итого', 't:Сумма', 'n:19500.00000000', 't:RUB'],
            ['total', 't:Итого', 't:Максимум', '', 't:разные валюты'],
            ['total', 't:Расчёт', 't:Сумма', 'n:1.5', ''],
            ['blank'],
            ['note', 't:Ограничено: 2'],
        ], self::dump($sheet));
        // The UTC moment is shown in the time zone of the file, as a date-time cell.
        $this->assertSame(SheetCell::DATETIME, $sheet->rows[0]['cells'][3]->kind);
    }

    public function testSummariesRepeatParents(): void
    {
        $result = [
            'type' => 'summaries',
            'groups' => [['label' => 'Статус', 'fieldType' => 'enum', 'granularity' => null],
                ['label' => 'Дата (месяц)', 'fieldType' => 'date', 'granularity' => 'month']],
            'aggregates' => [['label' => 'Число', 'function' => 'COUNT', 'fieldType' => null],
                ['label' => 'Сумма: Итого', 'function' => 'SUM', 'fieldType' => 'currency']],
            'tree' => [
                ['key' => ['v' => 'Draft', 'f' => 'Черновик'], 'count' => 3, 'values' => [['v' => 3, 'f' => '3'],
                    self::money('30.00')], 'children' => [
                    ['key' => ['v' => '2026-09', 'f' => 'Сентябрь 2026'], 'count' => 1,
                        'values' => [['v' => 1, 'f' => '1'], self::money('10.00')]],
                    ['key' => ['v' => null, 'f' => '(пусто)'], 'count' => 2,
                        'values' => [['v' => 2, 'f' => '2'], self::money('20.00')]],
                ]],
            ],
            'grandTotal' => ['count' => 3, 'values' => [['v' => 3, 'f' => '3'], self::money('30.00')]],
        ];
        $sheet = FlatSheet::build($result, $this->words, $this->moscow);

        $this->assertSame(['Статус', 'Дата (месяц)', 'Число', 'Сумма: Итого', 'Валюта'], $sheet->header);
        $this->assertSame([
            ['data', 't:Черновик', '', 'n:3', 'n:30.00', 't:RUB'],
            ['data', 't:Черновик', 't:Сентябрь 2026', 'n:1', 'n:10.00', 't:RUB'],
            ['data', 't:Черновик', 't:(пусто)', 'n:2', 'n:20.00', 't:RUB'],
            ['total', 't:Итого', '', 'n:3', 'n:30.00', 't:RUB'],
        ], self::dump($sheet));
    }

    public function testDetailsAndDayGroups(): void
    {
        $result = [
            'type' => 'summariesWithDetails',
            'groups' => [['label' => 'Дата', 'fieldType' => 'date', 'granularity' => 'day']],
            'aggregates' => [['label' => 'Сумма', 'function' => 'SUM', 'fieldType' => 'currency']],
            'columns' => [['key' => 'c:name', 'label' => 'Название', 'fieldType' => 'varchar'],
                ['key' => 'c:amount', 'label' => 'Сумма', 'fieldType' => 'currency']],
            'tree' => [['key' => ['v' => '2026-10-01', 'f' => '01.10.2026'], 'count' => 1,
                'values' => [self::money('5.00')],
                'rows' => [['id' => 'x', 'cells' => [['v' => 'A', 'f' => 'A'], self::money('5.00', 'EUR')]]]]],
            'grandTotal' => ['count' => 1, 'values' => [self::money('5.00')]],
        ];
        $sheet = FlatSheet::build($result, $this->words, $this->moscow);

        $this->assertSame(['Дата', 'Сумма', 'Валюта', 'Название', 'Сумма', 'Валюта'], $sheet->header);
        $this->assertSame([
            ['data', 'd:2026-10-01', 'n:5.00', 't:RUB', '', '', ''],
            ['data', 'd:2026-10-01', '', '', 't:A', 'n:5.00', 't:EUR'],
            ['total', 't:Итого', 'n:5.00', 't:RUB', '', '', ''],
        ], self::dump($sheet));
    }

    private function matrixResult(int $aggregates): array
    {
        $count = ['label' => 'Число', 'function' => 'COUNT', 'fieldType' => null];
        $sum = ['label' => 'Сумма', 'function' => 'SUM', 'fieldType' => 'currency'];
        $value = fn (int $n, string $s) => $aggregates === 1 ? [['v' => $n, 'f' => (string) $n]] :
            [['v' => $n, 'f' => (string) $n], self::money($s)];

        return [
            'type' => 'matrix',
            'groups' => [['label' => 'Товар', 'fieldType' => 'link', 'granularity' => null],
                ['label' => 'Месяц', 'fieldType' => 'date', 'granularity' => 'month']],
            'aggregates' => $aggregates === 1 ? [$count] : [$count, $sum],
            'matrix' => [
                'rows' => [['key' => ['v' => 'p1', 'f' => '<b>Товар</b>', 'id' => 'p1', 'et' => 'Product'],
                    'count' => 2, 'values' => $value(2, '3.00')]],
                'columns' => [['key' => ['v' => '2026-09', 'f' => 'Сентябрь'], 'values' => $value(1, '1.00')],
                    ['key' => ['v' => '2026-10', 'f' => 'Октябрь'], 'values' => $value(1, '2.00')]],
                'cells' => [[['count' => 1, 'values' => $value(1, '1.00')], null]],
            ],
            'grandTotal' => ['count' => 2, 'values' => $value(2, '3.00')],
        ];
    }

    public function testMatrixSheet(): void
    {
        $single = FlatSheet::build($this->matrixResult(1), $this->words, $this->moscow);
        $this->assertSame(['Товар', 'Сентябрь', 'Октябрь', 'Итого'], $single->header);
        $this->assertSame([['data', 't:<b>Товар</b>', 'n:1', '', 'n:2'], ['total', 't:Итого', 'n:1', 'n:1', 'n:2']],
            self::dump($single));

        $double = FlatSheet::build($this->matrixResult(2), $this->words, $this->moscow);
        $this->assertSame(['Товар', 'Сентябрь — Число', 'Сентябрь — Сумма', 'Валюта', 'Октябрь — Число',
            'Октябрь — Сумма', 'Валюта', 'Итого — Число', 'Итого — Сумма', 'Валюта'], $double->header);
        // An empty cell keeps its columns, so every row has the width of the header.
        $this->assertSame(['data', 't:<b>Товар</b>', 'n:1', 'n:1.00', 't:RUB', '', '', '', 'n:2', 'n:3.00', 't:RUB'],
            self::dump($double)[0]);
        $this->assertSame(10, count($double->rows[1]['cells']));
    }

    public function testCsv(): void
    {
        $sheet = FlatSheet::build($this->tabular(), $this->words, $this->moscow);
        $csv = CsvWriter::write($sheet, ';');
        $lines = explode("\r\n", substr($csv, 3));

        $this->assertSame(CsvWriter::BOM, substr($csv, 0, 3));
        $this->assertSame("'=Название;Итого;Валюта;Создан;Дата;Статус;Расчёт", $lines[0]);
        $this->assertSame("\"'+7 999\";19500.00000000;RUB;\"2026-10-05 00:30\";2026-10-01;Черновик;1.5", $lines[1]);
        $this->assertSame('Итого;Максимум;;"разные валюты"', $lines[6]);

        $this->assertSame("\t", CsvWriter::delimiter('\t'));
        $this->assertSame(',', CsvWriter::delimiter(null));
        $this->assertSame(',', CsvWriter::delimiter('#'));
        $this->assertSame("a\tb\r\n", substr(CsvWriter::write(new Sheet(['a', 'b'], []), "\t"), 3));
    }

    public function testFormulasAndFileNames(): void
    {
        $this->assertSame("'=1+1", CellText::safe('=1+1'));
        $this->assertSame("'  @x", CellText::safe('  @x'));
        $this->assertSame("'\tx", CellText::safe("\tx"));
        $this->assertSame('-12.5', CellText::safe('-12.5'));
        $this->assertSame('Обычный текст', CellText::safe('Обычный текст'));

        $this->assertSame('Счета_ итоги _2026_.csv', CellText::fileName('Счета: итоги "2026"', 'csv'));
        $this->assertSame('report.pdf', CellText::fileName(' .. ', 'pdf'));
        $this->assertSame(150 + 5, mb_strlen(CellText::fileName(str_repeat('я', 300), 'xlsx')));
    }

    public function testSpreadsheetNumbersStayExact(): void
    {
        $this->assertSame(19500, SheetNumber::native('19500.00000000'));
        $this->assertSame(0.01, SheetNumber::native('0.01000000'));
        $this->assertSame(-1234.56, SheetNumber::native('-1234.56'));
        $this->assertSame(0, SheetNumber::native('0.000'));
        $this->assertSame(-123456789012345, SheetNumber::native('-123456789012345'));
        $this->assertSame(12345678901.25, SheetNumber::native('12345678901.25'));
        // The writer prints a float with the PHP precision: a number goes to the file only as its own digits, else
        // as text (internal review: with precision 14, 1234567890123.45 became 1234567890123.4 in the file).
        foreach (['1234567890123.45', '9999999999999.99', '0.1', '12345678901.25', '-0.5'] as $decimal) {
            $number = SheetNumber::native($decimal);
            $this->assertTrue($number === null || (string) $number === $decimal, "$decimal: its digits or text");
        }

        $this->assertSame(null, SheetNumber::native('9999999999999.99'), 'precision 14 rounds it up to 1E13');
        // More than 15 significant digits would change in a double: the file keeps the text.
        $this->assertSame(null, SheetNumber::native('-1234567890123456'));
        $this->assertSame(null, SheetNumber::native('12345678901234.56'));
        $this->assertSame(null, SheetNumber::native('1e5'));
    }

    public function testScreenTableEscapesAndMirrorsTheScreen(): void
    {
        $html = ScreenHtml::table($this->matrixResult(2), $this->words);

        $this->assertTrue(str_contains($html, '<th rowspan="2">Товар \\ Месяц</th>'), 'corner of the matrix');
        $this->assertTrue(str_contains($html, '<th class="c" colspan="2">Сентябрь</th>'), 'column over its aggregates');
        $this->assertTrue(str_contains($html, '&lt;b&gt;Товар&lt;/b&gt;'), 'escaped value');
        $this->assertTrue(!str_contains($html, '<b>'), 'no markup from data');
        $this->assertTrue(!str_contains($html, 'data-action') && !str_contains($html, '<a '), 'no buttons, no links');

        $tabular = ScreenHtml::table($this->tabular(), $this->words);
        $this->assertTrue(str_contains($tabular, '<tfoot><tr><th>Сумма</th><td class="r">19500.00000000 ₽</td>'),
            'the function label in the first column without a total');
        $this->assertTrue(str_contains($tabular, '<td class="r w">разные валюты</td>'), 'mixed currencies marked');

        $this->assertSame('<p class="no-data">Нет данных</p>', ScreenHtml::table(['type' => 'summaries', 'tree' => []],
            $this->words));

        $body = ScreenHtml::body('{{x}} <i>', ['Всего записей: 2'], ['Ограничено'], $this->matrixResult(1), $this->words);
        $this->assertTrue(str_starts_with($body, '<h1>{{x}} &lt;i&gt;</h1><div class="meta">Всего записей: 2</div>'),
            'title escaped');
    }

    public function testDetailsHeaderAndOrientation(): void
    {
        $result = [
            'type' => 'summariesWithDetails',
            'groups' => [['label' => 'Статус']],
            'aggregates' => [['label' => 'Сумма']],
            'columns' => [['label' => 'Название', 'numeric' => false], ['label' => 'Итого', 'numeric' => true]],
            'tree' => [['key' => ['v' => 'Draft', 'f' => 'Черновик'], 'count' => 2, 'values' => [['f' => '7,00 ₽']],
                'rows' => [['cells' => [['f' => 'A'], ['f' => '7,00 ₽']]]]]],
            'grandTotal' => ['count' => 2, 'values' => [['f' => '7,00 ₽']]],
        ];
        $html = ScreenHtml::table($result, $this->words);

        $this->assertTrue(str_contains($html, '<tr class="group"><th colspan="2">Статус = Черновик (2): Сумма 7,00 ₽</th>'),
            'group header over its records');
        $this->assertTrue(str_contains($html, '<tfoot><tr><th colspan="2">Итого (2): Сумма 7,00 ₽</th>'), 'total');
        $this->assertSame(6, ScreenHtml::cellCount($result));

        $this->assertSame(ScreenHtml::LANDSCAPE, ScreenHtml::orientation(['type' => 'matrix']));
        $this->assertSame(ScreenHtml::PORTRAIT, ScreenHtml::orientation(['type' => 'tabular',
            'columns' => array_fill(0, 10, []), 'calculations' => []]));
        $this->assertSame(ScreenHtml::LANDSCAPE, ScreenHtml::orientation(['type' => 'tabular',
            'columns' => array_fill(0, 10, []), 'calculations' => [[]]]));
        $this->assertSame(ScreenHtml::LANDSCAPE, ScreenHtml::orientation(['type' => 'summaries',
            'aggregates' => array_fill(0, 8, [])]));

        $document = ScreenHtml::document('Т', '<p>x</p>', 'td{}', ScreenHtml::LANDSCAPE, 'ru');
        $this->assertTrue(str_contains($document, '@page { size: A4 landscape;') && !str_contains($document, '<script'),
            'print document');
    }

    public function testLimitNotes(): void
    {
        $templates = ['limitedRows' => 'строк {n}', 'limitedGroups' => 'групп {n}', 'limitedCap' => 'потолок {n}',
            'limitedColumns' => 'колонок {n}', 'calculationsCapped' => 'расчёты {n}'];

        $this->assertSame(['строк 5', 'потолок 5000', 'расчёты 5000'], LimitNotes::of(['limits' => ['rowLimit' => 5,
            'rowLimitHit' => true, 'capHit' => true, 'maxRows' => 5000, 'calculationsCapped' => true]], $templates));
        $this->assertSame(['групп 20', 'колонок 50'], LimitNotes::of(['limits' => ['groupLimit' => 20,
            'groupLimitHit' => true, 'matrixColumnsHit' => true, 'maxMatrixColumns' => 50]], $templates));
        $this->assertSame([], LimitNotes::of([], $templates));
    }
}
