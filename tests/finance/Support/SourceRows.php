<?php

declare(strict_types=1);

namespace Itvolga\Tests\Finance\Support;

use Espo\Modules\Itvolga\Tools\Finance\Document;
use Espo\Modules\Itvolga\Tools\Finance\Line;
use Espo\Modules\Itvolga\Tools\Finance\Source\SourceDocument;

/**
 * Builds core objects from rows shaped like the source tables (column names of vtiger_inventoryproductrel and the
 * document headers). Shared by the synthetic fixtures and the private snapshot; 'NULL' and null mean SQL NULL.
 */
final class SourceRows
{
    /**
     * @param array<string, mixed> $header taxtype, region, subtotal, pre_tax_total, total and optional adjustments
     * @param list<array<string, mixed>> $lines
     */
    public static function document(array $header, array $lines): SourceDocument
    {
        $document = Document::of(
            (string) $header['taxtype'],
            array_map(self::line(...), $lines),
            self::value($header, 'discount_amount'),
            self::value($header, 'discount_percent'),
            self::value($header, 's_h_amount'),
            self::value($header, 's_h_percent'),
            self::value($header, 'adjustment'),
        );
        $region = self::value($header, 'region');

        return SourceDocument::of(
            $document,
            $region === null || $region === 'null' ? null : (int) $region,
            self::value($header, 'subtotal'),
            self::value($header, 'pre_tax_total'),
            self::value($header, 'total'),
        );
    }

    /**
     * @param array<string, mixed> $row
     */
    public static function line(array $row): Line
    {
        return Line::fromSource(
            self::value($row, 'quantity'),
            self::value($row, 'listprice'),
            self::value($row, 'discount_amount'),
            self::value($row, 'discount_percent'),
            self::value($row, 'tax1'),
            self::value($row, 'tax2'),
            self::value($row, 'tax3'),
            self::value($row, 'purchase_cost'),
            self::value($row, 'margin'),
        );
    }

    /**
     * @param array<string, mixed> $row
     */
    public static function value(array $row, string $key): mixed
    {
        $value = $row[$key] ?? null;

        return $value === 'NULL' ? null : $value;
    }
}
