<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Export;

/**
 * Notes of the limits a result hit, as the screen shows them (result-table.js limitNotes): the row limit of the
 * report, the group limit, the cap of a run, the matrix columns, the capped calculation totals. A file of the variant
 * «all» still says when a cap cut it (D-120).
 */
final class LimitNotes
{
    /**
     * @param array<string, mixed> $result
     * @param array<string, string> $templates limitedRows, limitedGroups, limitedCap, limitedColumns, calculationsCapped
     *   (Report.labels, «{n}» — the number)
     * @return list<string>
     */
    public static function of(array $result, array $templates): array
    {
        $limits = $result['limits'] ?? [];
        $notes = [];
        $add = function (string $key, mixed $n) use (&$notes, $templates): void {
            $notes[] = str_replace('{n}', (string) $n, $templates[$key] ?? $key);
        };

        if (!empty($limits['rowLimitHit'])) {
            $add('limitedRows', $limits['rowLimit'] ?? '');
        }

        if (!empty($limits['groupLimitHit'])) {
            $add('limitedGroups', $limits['groupLimit'] ?? '');
        }

        if (!empty($limits['capHit'])) {
            $add('limitedCap', $limits['maxRows'] ?? '');
        }

        if (!empty($limits['matrixColumnsHit'])) {
            $add('limitedColumns', $limits['maxMatrixColumns'] ?? '');
        }

        if (!empty($limits['calculationsCapped'])) {
            $add('calculationsCapped', $limits['maxRows'] ?? '');
        }

        return $notes;
    }
}
