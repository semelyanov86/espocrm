<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Export;

use DateTimeImmutable;
use DateTimeZone;
use Throwable;

/**
 * The flat table of a report result for CSV and XLSX (D-117): one header row, every row of the same width, so a file
 * can be filtered and summed in a spreadsheet.
 *
 *  - tabular: the columns and the calculations; after a blank row the totals as a block «column | function | value |
 *    currency»;
 *  - summaries: the levels of the groups and the aggregates, a row per group in tree order with the keys of its
 *    parents repeated (deeper levels empty), then the total row;
 *  - summaries with details: «group | aggregates | columns»: a group row carries the aggregates, its record rows the
 *    group key and the columns; then the total row;
 *  - matrix: the row group, then «<column value> — <aggregate>» for every shown column and «<total> — <aggregate>»;
 *    the last row holds the column totals and the grand total.
 *
 * Values are raw: numbers as decimal strings (`v`), dates ISO, date-times in the given time zone; enums, links, flags
 * and texts as shown (`f`). Every money column, aggregate or total is followed by a currency column (the code), also
 * when a value is empty, so the columns do not depend on the data; mixed currencies leave the value empty and mark the
 * currency cell. Notes of the limits close the sheet.
 */
final class FlatSheet
{
    private const NUMERIC_TYPES = ['int', 'float', 'decimal', 'currency', 'autoincrement'];

    private function __construct(
        private readonly OutputWords $words,
        private readonly DateTimeZone $timeZone,
    ) {}

    /**
     * @param array<string, mixed> $result a result of ReportRunner (all rows)
     * @param list<string> $notes notes of the limits in the user's language
     */
    public static function build(array $result, OutputWords $words, DateTimeZone $timeZone, array $notes = []): Sheet
    {
        $sheet = new self($words, $timeZone);

        [$header, $rows] = match ($result['type'] ?? null) {
            'tabular' => $sheet->tabular($result),
            'summaries' => $sheet->summaries($result),
            'summariesWithDetails' => $sheet->withDetails($result),
            'matrix' => $sheet->matrix($result),
            default => [[], []],
        };

        if ($notes !== []) {
            $rows[] = self::row(Sheet::ROW_BLANK, []);

            foreach ($notes as $note) {
                $rows[] = self::row(Sheet::ROW_NOTE, [SheetCell::text($note)]);
            }
        }

        return new Sheet($header, $rows);
    }

    /**
     * @param list<SheetCell> $cells
     * @return array{kind: string, cells: list<SheetCell>}
     */
    private static function row(string $kind, array $cells): array
    {
        return ['kind' => $kind, 'cells' => $cells];
    }

    /**
     * @return array{list<string>, list<array{kind: string, cells: list<SheetCell>}>}
     */
    private function tabular(array $result): array
    {
        $columns = $result['columns'] ?? [];
        $header = [];

        foreach ($columns as $column) {
            array_push($header, $column['label'], ...($this->isMoney($column['fieldType'] ?? null) ?
                [$this->words->currency] : []));
        }

        foreach ($result['calculations'] ?? [] as $calculation) {
            $header[] = $calculation['label'];
        }

        $rows = [];

        foreach ($result['rows'] ?? [] as $row) {
            $cells = [];

            foreach ($columns as $i => $column) {
                array_push($cells, ...$this->value($row['cells'][$i] ?? null, $column['fieldType'] ?? null));
            }

            foreach ($row['calc'] ?? [] as $cell) {
                $cells[] = $this->number($cell);
            }

            $rows[] = self::row(Sheet::ROW_DATA, $cells);
        }

        $totals = [];

        foreach ($columns as $column) {
            foreach ($result['totals'][$column['key']] ?? [] as $function => $cell) {
                $totals[] = [$column['label'], $function, $cell, $this->isMoney($column['fieldType'] ?? null)];
            }
        }

        foreach ($result['calculations'] ?? [] as $calculation) {
            foreach ($result['calculationTotals'][$calculation['key']] ?? [] as $function => $cell) {
                $totals[] = [$calculation['label'], $function, $cell, false];
            }
        }

        if ($totals !== []) {
            $rows[] = self::row(Sheet::ROW_BLANK, []);
            $rows[] = self::row(Sheet::ROW_HEADER, array_map(fn (string $t) => SheetCell::text($t),
                [$this->words->column, $this->words->function, $this->words->value, $this->words->currency]));

            foreach ($totals as [$label, $function, $cell, $money]) {
                [$value, $currency] = $this->money($cell);
                $rows[] = self::row(Sheet::ROW_TOTAL, [SheetCell::text($label),
                    SheetCell::text($this->words->function($function)), $value,
                    $money ? $currency : SheetCell::empty()]);
            }
        }

        return [$header, $rows];
    }

    /**
     * @return array{list<string>, list<array{kind: string, cells: list<SheetCell>}>}
     */
    private function summaries(array $result): array
    {
        $groups = $result['groups'] ?? [];
        $aggregates = $result['aggregates'] ?? [];
        $header = [...array_map(fn ($g) => $g['label'], $groups), ...$this->aggregateHeader($aggregates)];
        $rows = [];
        $levels = count($groups);

        $walk = function (array $nodes, array $path) use (&$walk, &$rows, $groups, $aggregates, $levels): void {
            foreach ($nodes as $node) {
                $keys = [...$path, $this->groupKey($node['key'] ?? null, $groups[count($path)] ?? [])];
                $cells = [...$keys, ...array_fill(0, $levels - count($keys), SheetCell::empty())];
                $rows[] = self::row(Sheet::ROW_DATA, [...$cells, ...$this->aggregateCells($node['values'] ?? [],
                    $aggregates)]);
                $walk($node['children'] ?? [], $keys);
            }
        };

        $walk($result['tree'] ?? [], []);
        $rows[] = self::row(Sheet::ROW_TOTAL, [SheetCell::text($this->words->total),
            ...array_fill(0, max(0, $levels - 1), SheetCell::empty()),
            ...$this->aggregateCells($result['grandTotal']['values'] ?? [], $aggregates)]);

        return [$header, $rows];
    }

    /**
     * @return array{list<string>, list<array{kind: string, cells: list<SheetCell>}>}
     */
    private function withDetails(array $result): array
    {
        $group = $result['groups'][0] ?? [];
        $aggregates = $result['aggregates'] ?? [];
        $columns = $result['columns'] ?? [];
        $columnHeader = [];

        foreach ($columns as $column) {
            array_push($columnHeader, $column['label'], ...($this->isMoney($column['fieldType'] ?? null) ?
                [$this->words->currency] : []));
        }

        $header = [$group['label'] ?? '', ...$this->aggregateHeader($aggregates), ...$columnHeader];
        $aggregateWidth = count($this->aggregateHeader($aggregates));
        $columnWidth = count($columnHeader);
        $rows = [];

        foreach ($result['tree'] ?? [] as $node) {
            $key = $this->groupKey($node['key'] ?? null, $group);
            $rows[] = self::row(Sheet::ROW_DATA, [$key, ...$this->aggregateCells($node['values'] ?? [], $aggregates),
                ...array_fill(0, $columnWidth, SheetCell::empty())]);

            foreach ($node['rows'] ?? [] as $record) {
                $cells = [];

                foreach ($columns as $i => $column) {
                    array_push($cells, ...$this->value($record['cells'][$i] ?? null, $column['fieldType'] ?? null));
                }

                $rows[] = self::row(Sheet::ROW_DATA, [$key, ...array_fill(0, $aggregateWidth, SheetCell::empty()),
                    ...$cells]);
            }
        }

        $rows[] = self::row(Sheet::ROW_TOTAL, [SheetCell::text($this->words->total),
            ...$this->aggregateCells($result['grandTotal']['values'] ?? [], $aggregates),
            ...array_fill(0, $columnWidth, SheetCell::empty())]);

        return [$header, $rows];
    }

    /**
     * @return array{list<string>, list<array{kind: string, cells: list<SheetCell>}>}
     */
    private function matrix(array $result): array
    {
        $groups = $result['groups'] ?? [];
        $aggregates = $result['aggregates'] ?? [];
        $matrix = $result['matrix'] ?? ['rows' => [], 'columns' => [], 'cells' => []];
        $header = [$groups[0]['label'] ?? ''];
        $single = count($aggregates) === 1;

        foreach ([...array_map(fn ($c) => $c['key']['f'] ?? '', $matrix['columns']), $this->words->total] as $title) {
            foreach ($aggregates as $aggregate) {
                $header[] = $single ? $title : $title . ' — ' . $aggregate['label'];

                if ($this->isMoney($aggregate['fieldType'] ?? null)) {
                    $header[] = $this->words->currency;
                }
            }
        }

        $rows = [];

        foreach ($matrix['rows'] as $r => $row) {
            $cells = [$this->groupKey($row['key'] ?? null, $groups[0] ?? [])];

            foreach (array_keys($matrix['columns']) as $c) {
                $cell = $matrix['cells'][$r][$c] ?? null;
                array_push($cells, ...$this->aggregateCells($cell['values'] ?? array_fill(0, count($aggregates), null),
                    $aggregates));
            }

            $rows[] = self::row(Sheet::ROW_DATA, [...$cells, ...$this->aggregateCells($row['values'] ?? [],
                $aggregates)]);
        }

        $total = [SheetCell::text($this->words->total)];

        foreach ($matrix['columns'] as $column) {
            array_push($total, ...$this->aggregateCells($column['values'] ?? [], $aggregates));
        }

        $rows[] = self::row(Sheet::ROW_TOTAL, [...$total,
            ...$this->aggregateCells($result['grandTotal']['values'] ?? [], $aggregates)]);

        return [$header, $rows];
    }

    /**
     * @param list<array<string, mixed>> $aggregates
     * @return list<string>
     */
    private function aggregateHeader(array $aggregates): array
    {
        $header = [];

        foreach ($aggregates as $aggregate) {
            array_push($header, $aggregate['label'], ...($this->isMoney($aggregate['fieldType'] ?? null) ?
                [$this->words->currency] : []));
        }

        return $header;
    }

    /**
     * @param list<?array<string, mixed>> $values
     * @param list<array<string, mixed>> $aggregates
     * @return list<SheetCell>
     */
    private function aggregateCells(array $values, array $aggregates): array
    {
        $cells = [];

        foreach ($aggregates as $i => $aggregate) {
            $cell = $values[$i] ?? null;

            if ($this->isMoney($aggregate['fieldType'] ?? null)) {
                array_push($cells, ...$this->money($cell));

                continue;
            }

            $cells[] = $this->number($cell);
        }

        return $cells;
    }

    private function isMoney(?string $fieldType): bool
    {
        return $fieldType === 'currency';
    }

    /**
     * Cells of a value of a field: the value, and the currency after a money value.
     *
     * @param ?array<string, mixed> $cell
     * @return list<SheetCell>
     */
    private function value(?array $cell, ?string $fieldType): array
    {
        if ($this->isMoney($fieldType)) {
            return $this->money($cell);
        }

        if (in_array($fieldType, self::NUMERIC_TYPES, true)) {
            return [$this->number($cell)];
        }

        $raw = $cell['v'] ?? null;

        if (($fieldType === 'date' || $fieldType === 'datetime' || $fieldType === 'datetimeOptional') &&
            is_string($raw) && $raw !== '') {
            return [$this->dateCell($raw)];
        }

        return [SheetCell::text((string) ($cell['f'] ?? ''))];
    }

    /**
     * @param ?array<string, mixed> $cell
     * @return array{SheetCell, SheetCell} the amount and the currency
     */
    private function money(?array $cell): array
    {
        if (!empty($cell['mixed'])) {
            return [SheetCell::empty(), SheetCell::text($this->words->mixedCurrencies)];
        }

        return [$this->number($cell), SheetCell::text(is_string($cell['cur'] ?? null) ? $cell['cur'] : '')];
    }

    /**
     * @param ?array<string, mixed> $cell
     */
    private function number(?array $cell): SheetCell
    {
        $raw = $cell['v'] ?? null;

        if (is_int($raw)) {
            return SheetCell::number((string) $raw);
        }

        return is_string($raw) && $raw !== '' ? SheetCell::number($raw) : SheetCell::empty();
    }

    /**
     * A date as is; a date-time (UTC `Y-m-d H:i:s`) in the time zone of the file; a date-only value of an optional
     * date-time (10 characters) stays a date.
     */
    private function dateCell(string $raw): SheetCell
    {
        if (strlen($raw) === 10) {
            return SheetCell::date($raw);
        }

        try {
            $moment = new DateTimeImmutable($raw, new DateTimeZone('UTC'));
        } catch (Throwable) {
            return SheetCell::text($raw);
        }

        return SheetCell::dateTime($moment->setTimezone($this->timeZone)->format('Y-m-d H:i'));
    }

    /**
     * A group key: a day as an ISO date, another period as its label, a number raw, else the shown text (the empty
     * group shows its label).
     *
     * @param ?array<string, mixed> $key
     * @param array<string, mixed> $group
     */
    private function groupKey(?array $key, array $group): SheetCell
    {
        $raw = $key['v'] ?? null;

        if ($raw === null || $raw === '') {
            return SheetCell::text((string) ($key['f'] ?? ''));
        }

        $granularity = $group['granularity'] ?? null;

        if ($granularity === 'day' && is_string($raw) && strlen($raw) === 10) {
            return SheetCell::date($raw);
        }

        if ($granularity === null && in_array($group['fieldType'] ?? null, self::NUMERIC_TYPES, true)) {
            return $this->number($key);
        }

        return SheetCell::text((string) ($key['f'] ?? ''));
    }
}
