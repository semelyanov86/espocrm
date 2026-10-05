<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Export;

use RuntimeException;

/**
 * CSV of a flat sheet (D-117): UTF-8 with a byte order mark (a spreadsheet opens Cyrillic right), the delimiter of the
 * user's export settings, quotes as RFC 4180, CRLF. Numbers are decimal strings with a dot, dates ISO; texts — also
 * the header and the notes — are protected against formulas (CellText::safe).
 */
final class CsvWriter
{
    public const BOM = "\xEF\xBB\xBF";

    public static function write(Sheet $sheet, string $delimiter): string
    {
        $stream = fopen('php://temp', 'w+');

        if ($stream === false) {
            throw new RuntimeException('No temporary stream.');
        }

        try {
            self::line($stream, array_map(fn (string $t) => CellText::safe($t), $sheet->header), $delimiter);

            foreach ($sheet->rows as $row) {
                self::line($stream, array_map(fn (SheetCell $c) => $c->kind === SheetCell::TEXT ?
                    CellText::safe($c->value) : $c->value, $row['cells']), $delimiter);
            }

            rewind($stream);

            return self::BOM . stream_get_contents($stream);
        } finally {
            fclose($stream);
        }
    }

    /**
     * @param resource $stream
     * @param list<string> $values
     */
    private static function line($stream, array $values, string $delimiter): void
    {
        fputcsv($stream, $values, $delimiter, '"', '', "\r\n");
    }

    /**
     * The delimiter of a setting: the core keeps a tab as the two characters «\t».
     */
    public static function delimiter(?string $setting): string
    {
        $value = str_replace('\t', "\t", $setting ?? '');

        return in_array($value, [',', ';', "\t", '|'], true) ? $value : ',';
    }
}
