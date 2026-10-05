<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Export;

use DateTimeImmutable;
use Espo\Modules\Itvolga\Tools\Report\Core\Export\Sheet;
use Espo\Modules\Itvolga\Tools\Report\Core\Export\SheetCell;
use Espo\Modules\Itvolga\Tools\Report\Core\Export\SheetNumber;
use OpenSpout\Common\Entity\Cell;
use OpenSpout\Common\Entity\Cell\DateTimeCell;
use OpenSpout\Common\Entity\Cell\EmptyCell;
use OpenSpout\Common\Entity\Cell\NumericCell;
use OpenSpout\Common\Entity\Cell\StringCell;
use OpenSpout\Common\Entity\Row;
use OpenSpout\Common\Entity\Style\Style;
use OpenSpout\Writer\XLSX\Entity\SheetView;
use OpenSpout\Writer\XLSX\Options;
use OpenSpout\Writer\XLSX\Writer;
use RuntimeException;
use Throwable;

/**
 * XLSX of a flat sheet (D-118) with OpenSpout of the core vendor, streamed to a temporary file: a bold, frozen header;
 * numbers as numeric cells only when exact (SheetNumber), else text; dates and date-times as date cells; texts as
 * explicit string cells, so a text never becomes a formula.
 */
final class XlsxWriter
{
    private const COLUMN_WIDTH = 20;

    public static function write(Sheet $sheet): string
    {
        $path = tempnam(sys_get_temp_dir(), 'itv-report');

        if ($path === false) {
            throw new RuntimeException('No temporary file.');
        }

        try {
            $width = max(1, count($sheet->header), ...array_map(fn ($row) => count($row['cells']), $sheet->rows));
            $options = new Options();
            $options->setColumnWidthForRange(self::COLUMN_WIDTH, 1, $width);
            $writer = new Writer($options);
            $writer->openToFile($path);
            $writer->getCurrentSheet()->setSheetView((new SheetView())->withFreezeRow(2));
            $bold = (new Style())->withFontBold(true);

            $writer->addRow(new Row(array_map(fn (string $label) => new StringCell($label, $bold), $sheet->header)));

            foreach ($sheet->rows as $row) {
                $style = in_array($row['kind'], [Sheet::ROW_HEADER, Sheet::ROW_TOTAL], true) ? $bold : null;
                $writer->addRow(new Row(array_map(fn (SheetCell $c) => self::cell($c, $style), $row['cells'])));
            }

            $writer->close();
            $contents = file_get_contents($path);

            if ($contents === false) {
                throw new RuntimeException('The XLSX file cannot be read.');
            }

            return $contents;
        } finally {
            @unlink($path);
        }
    }

    private static function cell(SheetCell $cell, ?Style $style): Cell
    {
        switch ($cell->kind) {
            case SheetCell::NUMBER:
                $number = SheetNumber::native($cell->value);

                if ($number === null) {
                    return new StringCell($cell->value, $style);
                }

                $format = self::numberFormat($cell->value);

                return new NumericCell($number, $format === null ? $style :
                    ($style ?? new Style())->withFormat($format));

            case SheetCell::DATE:
            case SheetCell::DATETIME:
                try {
                    $value = new DateTimeImmutable($cell->value);
                } catch (Throwable) {
                    return new StringCell($cell->value, $style);
                }

                return new DateTimeCell($value, ($style ?? new Style())->withFormat($cell->kind === SheetCell::DATE ?
                    'yyyy-mm-dd' : 'yyyy-mm-dd hh:mm'));

            case SheetCell::TEXT:
                return new StringCell($cell->value, $style);
        }

        return new EmptyCell(null, $style);
    }

    /**
     * A number written with a fraction keeps at least two decimals in the view (money), all it has when more (at most
     * 15 significant digits, SheetNumber; external review 05.3 W7); an integer has the general format. The value of the
     * cell is not rounded.
     */
    private static function numberFormat(string $decimal): ?string
    {
        $dot = strpos($decimal, '.');

        if ($dot === false) {
            return null;
        }

        $scale = max(2, strlen(rtrim(substr($decimal, $dot + 1), '0')));

        return '#,##0.' . str_repeat('0', $scale);
    }
}
