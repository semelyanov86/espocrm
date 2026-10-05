<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Export;

/**
 * A flat table of a report result (FlatSheet): one header row and rows of typed cells. A row has a kind the XLSX writer
 * styles (a header row of the totals block, a total row); an empty row separates blocks; notes of the limits close it.
 */
final class Sheet
{
    public const ROW_DATA = 'data';
    public const ROW_HEADER = 'header';
    public const ROW_TOTAL = 'total';
    public const ROW_BLANK = 'blank';
    public const ROW_NOTE = 'note';

    /**
     * @param list<string> $header
     * @param list<array{kind: string, cells: list<SheetCell>}> $rows
     */
    public function __construct(
        public readonly array $header,
        public readonly array $rows,
    ) {}
}
