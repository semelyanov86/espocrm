<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Export;

/**
 * The result of a report as on the screen, for the PDF and the print view (D-119): the server mirror of
 * client/custom/modules/itvolga/src/report/result-table.js without links, drill-down buttons and the pager — tabular
 * rows with the totals in the footer, summaries as nested group rows, summaries with details as group headers over
 * their records, the matrix with its two-level header and the row, column and grand totals. A change of the screen
 * table is made in both files.
 *
 * Every text is escaped here; the template prints the ready HTML as data (never as template text), so a value cannot
 * become markup or a template expression.
 */
final class ScreenHtml
{
    public const PORTRAIT = 'Portrait';
    public const LANDSCAPE = 'Landscape';
    private const WIDE_AGGREGATES = 7;
    private const WIDE_COLUMNS = 10;

    private int $cells = 0;

    private function __construct(private readonly OutputWords $words) {}

    /**
     * The page: title, meta lines, notes of the limits and the table (or «no data»).
     *
     * @param array<string, mixed> $result
     * @param list<string> $meta
     * @param list<string> $notes
     */
    public static function body(string $title, array $meta, array $notes, array $result, OutputWords $words): string
    {
        $html = '<h1>' . self::e($title) . '</h1>';

        if ($meta !== []) {
            $html .= '<div class="meta">' . implode(' · ', array_map(fn ($m) => self::e($m), $meta)) . '</div>';
        }

        foreach ($notes as $note) {
            $html .= '<div class="note">' . self::e($note) . '</div>';
        }

        return $html . self::table($result, $words);
    }

    /**
     * A complete document for the browser print (no scripts, no external resources).
     */
    public static function document(string $title, string $body, string $css, string $orientation,
        string $language): string
    {
        $size = $orientation === self::LANDSCAPE ? 'A4 landscape' : 'A4 portrait';

        return '<!DOCTYPE html><html lang="' . self::e($language) . '"><head><meta charset="utf-8"><title>' .
            self::e($title) . "</title><style>@page { size: $size; margin: 10mm; }\n" . $css .
            '</style></head><body>' . $body . '</body></html>';
    }

    /**
     * @param array<string, mixed> $result
     */
    public static function table(array $result, OutputWords $words): string
    {
        return (new self($words))->render($result)[0];
    }

    /**
     * Number of cells of the table — the budget of a PDF (Dompdf time and memory grow with it).
     *
     * @param array<string, mixed> $result
     */
    public static function cellCount(array $result): int
    {
        return (new self(new OutputWords()))->render($result)[1];
    }

    /**
     * Landscape for a matrix and for wide tables (the reference rule: more than 7 aggregates or more than 10 columns
     * with the calculations).
     *
     * @param array<string, mixed> $result
     */
    public static function orientation(array $result): string
    {
        $wide = ($result['type'] ?? null) === 'matrix' ||
            count($result['aggregates'] ?? []) > self::WIDE_AGGREGATES ||
            count($result['columns'] ?? []) + count($result['calculations'] ?? []) > self::WIDE_COLUMNS;

        return $wide ? self::LANDSCAPE : self::PORTRAIT;
    }

    /**
     * @param array<string, mixed> $result
     * @return array{string, int}
     */
    private function render(array $result): array
    {
        $this->cells = 0;

        $html = match ($result['type'] ?? null) {
            'tabular' => $this->tabular($result),
            'summaries', 'summariesWithDetails' => $this->grouped($result),
            'matrix' => $this->matrix($result),
            default => null,
        };

        return [$html ?? '<p class="no-data">' . self::e($this->words->noData) . '</p>', $this->cells];
    }

    private static function e(mixed $text): string
    {
        return htmlspecialchars((string) $text, ENT_QUOTES | ENT_SUBSTITUTE | ENT_HTML5, 'UTF-8');
    }

    /**
     * @param array<string, mixed> $options class, colspan, rowspan
     */
    private function cell(string $tag, ?string $text, array $options = []): string
    {
        $this->cells++;
        $attributes = '';

        if (!empty($options['class'])) {
            $attributes .= ' class="' . self::e($options['class']) . '"';
        }

        foreach (['colspan', 'rowspan'] as $span) {
            if (($options[$span] ?? 1) > 1) {
                $attributes .= " $span=\"" . (int) $options[$span] . '"';
            }
        }

        return "<$tag$attributes>" . self::e($text ?? '') . "</$tag>";
    }

    /**
     * @param ?array<string, mixed> $value a result cell
     */
    private function value(?array $value, bool $numeric): string
    {
        $classes = array_filter([$numeric ? 'r' : null, !empty($value['mixed']) ? 'w' : null]);

        return $this->cell('td', (string) ($value['f'] ?? ''), ['class' => implode(' ', $classes)]);
    }

    /**
     * @param list<string> $labels
     * @param list<bool> $numeric
     */
    private function headerRow(array $labels, array $numeric): string
    {
        $html = '<tr>';

        foreach ($labels as $i => $label) {
            $html .= $this->cell('th', $label, ['class' => !empty($numeric[$i]) ? 'r' : '']);
        }

        return $html . '</tr>';
    }

    private function tabular(array $result): ?string
    {
        if (($result['rows'] ?? []) === []) {
            return null;
        }

        $columns = $result['columns'];
        $calculations = $result['calculations'] ?? [];
        $html = '<table class="report"><thead>' .
            $this->headerRow([...array_column($columns, 'label'), ...array_column($calculations, 'label')],
                [...array_map(fn ($c) => !empty($c['numeric']), $columns), ...array_map(fn () => true, $calculations)]) .
            '</thead><tbody>';

        foreach ($result['rows'] as $row) {
            $html .= '<tr>';

            foreach ($columns as $i => $column) {
                $html .= $this->value($row['cells'][$i] ?? null, !empty($column['numeric']));
            }

            foreach ($row['calc'] ?? [] as $value) {
                $html .= $this->value($value, true);
            }

            $html .= '</tr>';
        }

        return $html . '</tbody>' . $this->tabularTotals($result) . '</table>';
    }

    private function tabularTotals(array $result): string
    {
        $totals = $result['totals'] ?? [];
        $calculationTotals = $result['calculationTotals'] ?? [];
        $functions = array_values(array_filter(['SUM', 'AVG', 'MIN', 'MAX'], fn ($fn) =>
            array_filter($totals, fn ($t) => isset($t[$fn])) !== [] ||
            array_filter($calculationTotals, fn ($t) => isset($t[$fn])) !== []));

        if ($functions === []) {
            return '';
        }

        $html = '<tfoot>';
        $capped = !empty($result['limits']['calculationsCapped']);

        foreach ($functions as $fn) {
            $html .= '<tr>';

            foreach ($result['columns'] as $i => $column) {
                $total = $totals[$column['key']][$fn] ?? null;

                if ($i === 0 && $total === null) {
                    $html .= $this->cell('th', $this->words->function($fn));

                    continue;
                }

                $html .= $this->value($total, true);
            }

            foreach ($result['calculations'] ?? [] as $calculation) {
                $total = $calculationTotals[$calculation['key']][$fn] ?? null;
                $html .= $this->cell('td', (string) ($total['f'] ?? ''),
                    ['class' => 'r' . ($capped && $total !== null ? ' w' : '')]);
            }

            $html .= '</tr>';
        }

        return $html . '</tfoot>';
    }

    private function grouped(array $result): ?string
    {
        if (($result['tree'] ?? []) === []) {
            return null;
        }

        $groups = $result['groups'];
        $aggregates = $result['aggregates'] ?? [];
        $levels = count($groups);
        $details = $result['type'] === 'summariesWithDetails';
        $columns = $details ? ($result['columns'] ?? []) : [];

        $html = '<table class="report"><thead>' . ($details ?
            $this->headerRow(array_column($columns, 'label'), array_map(fn ($c) => !empty($c['numeric']), $columns)) :
            $this->headerRow([...array_column($groups, 'label'), ...array_column($aggregates, 'label')],
                [...array_fill(0, $levels, false), ...array_fill(0, count($aggregates), true)])) . '</thead><tbody>';

        $summary = fn (array $values) => implode('; ', array_map(fn ($a, $i) => $a['label'] . ' ' .
            ($values[$i]['f'] ?? ''), $aggregates, array_keys($aggregates)));

        $addNode = function (array $node, int $level) use (&$addNode, &$html, $levels, $details, $columns, $groups,
            $aggregates, $summary): void {
            if ($details) {
                $text = ($groups[0]['label'] ?? '') . ' = ' . ($node['key']['f'] ?? '') . ' (' . ($node['count'] ?? 0) .
                    ')' . ($aggregates !== [] ? ': ' . $summary($node['values'] ?? []) : '');
                $html .= '<tr class="group">' . $this->cell('th', $text, ['colspan' => max(1, count($columns))]) .
                    '</tr>';

                foreach ($node['rows'] ?? [] as $row) {
                    $html .= '<tr>';

                    foreach ($columns as $i => $column) {
                        $html .= $this->value($row['cells'][$i] ?? null, !empty($column['numeric']));
                    }

                    $html .= '</tr>';
                }

                return;
            }

            $html .= '<tr' . ($level === 0 && $levels > 1 ? ' class="group"' : '') . '>';

            for ($i = 0; $i < $levels; $i++) {
                $html .= $i === $level ? $this->value($node['key'] ?? null, false) : $this->cell('td', '');
            }

            foreach ($node['values'] ?? [] as $value) {
                $html .= $this->value($value, true);
            }

            $html .= '</tr>';

            foreach ($node['children'] ?? [] as $child) {
                $addNode($child, $level + 1);
            }
        };

        foreach ($result['tree'] as $node) {
            $addNode($node, 0);
        }

        $grand = $result['grandTotal'] ?? ['count' => 0, 'values' => []];
        $label = $this->words->total . ' (' . ($grand['count'] ?? 0) . ')';
        $html .= '</tbody><tfoot><tr>';

        if ($details) {
            $html .= $this->cell('th', $label . ($aggregates !== [] ? ': ' . $summary($grand['values'] ?? []) : ''),
                ['colspan' => max(1, count($columns))]);
        } else {
            $html .= $this->cell('th', $label, ['colspan' => $levels]);

            foreach ($grand['values'] ?? [] as $value) {
                $html .= $this->value($value, true);
            }
        }

        return $html . '</tr></tfoot></table>';
    }

    private function matrix(array $result): ?string
    {
        $matrix = $result['matrix'] ?? [];

        if (($matrix['rows'] ?? []) === []) {
            return null;
        }

        $aggregates = $result['aggregates'] ?? [];
        $span = count($aggregates);
        $groups = $result['groups'];
        $html = '<table class="report"><thead><tr>' .
            $this->cell('th', ($groups[0]['label'] ?? '') . ' \\ ' . ($groups[1]['label'] ?? ''),
                ['rowspan' => $span > 1 ? 2 : 1]);

        foreach ($matrix['columns'] as $column) {
            $html .= $this->cell('th', (string) ($column['key']['f'] ?? ''), ['class' => 'c', 'colspan' => $span]);
        }

        $html .= $this->cell('th', $this->words->total, ['class' => 'c', 'colspan' => $span]) . '</tr>';

        if ($span > 1) {
            $html .= '<tr>';

            foreach ([...$matrix['columns'], null] as $ignored) {
                foreach ($aggregates as $aggregate) {
                    $html .= $this->cell('th', $aggregate['label'], ['class' => 'r']);
                }
            }

            $html .= '</tr>';
        }

        $html .= '</thead><tbody>';

        foreach ($matrix['rows'] as $r => $row) {
            $html .= '<tr>' . $this->value($row['key'] ?? null, false);

            foreach (array_keys($matrix['columns']) as $c) {
                $cell = $matrix['cells'][$r][$c] ?? null;

                for ($i = 0; $i < $span; $i++) {
                    $html .= $this->value($cell['values'][$i] ?? null, true);
                }
            }

            foreach ($row['values'] ?? [] as $value) {
                $html .= $this->value($value, true);
            }

            $html .= '</tr>';
        }

        $html .= '</tbody><tfoot><tr>' . $this->cell('th', $this->words->total);

        foreach ($matrix['columns'] as $column) {
            foreach ($column['values'] ?? [] as $value) {
                $html .= $this->value($value, true);
            }
        }

        foreach ($result['grandTotal']['values'] ?? [] as $value) {
            $html .= $this->value($value, true);
        }

        return $html . '</tr></tfoot></table>';
    }
}
