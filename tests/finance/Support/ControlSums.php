<?php

declare(strict_types=1);

namespace Itvolga\Tests\Finance\Support;

use Espo\Modules\Itvolga\Tools\Finance\Decimal;
use Espo\Modules\Itvolga\Tools\Finance\Line;
use Espo\Modules\Itvolga\Tools\Finance\Payment\SourceAllocation;
use RuntimeException;

/**
 * Monetary control sums of the source (scripts/audit/sql/35_control_sums_private.sql), computed two ways:
 * by MySQL on the server (private TSV) and by the finance core from the private numeric snapshot.
 *
 * Rows are canonical strings: key columns as is, numbers in the shortest decimal form. Only an HMAC of each group
 * (key outside Git) is committed — the anonymised control sums of the source; the sums themselves stay private.
 */
final class ControlSums
{
    /** group → number of key columns (the rest are numbers) */
    public const GROUPS = ['doc_sums' => 3, 'line_sums' => 1, 'payment_sums' => 3, 'alloc_sums' => 3, 'coverage_sums' => 2];

    public const DOCUMENT_MODULES = ['Invoice', 'Act', 'Quotes', 'SalesOrder'];

    /**
     * @return array<string, list<string>> group → canonical rows
     */
    public static function fromServer(string $file): array
    {
        $kinds = PrivateTsv::read($file);
        $rows = [];

        foreach ($kinds['doc_sums'] ?? [] as $r) {
            $rows['doc_sums'][] = [$r['m'], self::year($r['y']), $r['taxtype'], $r['n'], $r['subtotal'], $r['pre_tax'], $r['total'], self::blank($r['balance'])];
        }

        foreach ($kinds['line_sums'] ?? [] as $r) {
            if (in_array($r['setype'], self::DOCUMENT_MODULES, true)) {
                $rows['line_sums'][] = [$r['setype'], $r['n'], $r['qty'], $r['gross'], $r['disc'], $r['margin']];
            }
        }

        foreach ($kinds['payment_sums'] ?? [] as $r) {
            $rows['payment_sums'][] = [self::year($r['y']), $r['pay_type'], self::blank($r['spstatus']), $r['n'], $r['amount']];
        }

        foreach ($kinds['alloc_sums'] ?? [] as $r) {
            $rows['alloc_sums'][] = [$r['target_type'], $r['pay_type'], self::blank($r['spstatus']), $r['n'], $r['amount']];
        }

        foreach ($kinds['coverage_sums'] ?? [] as $r) {
            $rows['coverage_sums'][] = [$r['m'], self::blank($r['st']), $r['n'], $r['total'], $r['paid']];
        }

        return self::canonicalGroups($rows);
    }

    /**
     * @param array<int, SourceAllocation> $allocations payment id → allocation (D-11 candidate target is used,
     *        exactly as the server query does)
     * @return array<string, list<string>>
     */
    public static function fromSnapshot(SourceSnapshot $snapshot, array $allocations): array
    {
        $acc = [];
        $add = static function (string $group, array $key, array $values) use (&$acc): void {
            $id = implode("\t", $key);
            $acc[$group][$id] ??= ['key' => $key, 'n' => 0, 'sums' => array_fill(0, count($values), null)];
            $acc[$group][$id]['n']++;

            foreach ($values as $i => $value) {
                if ($value !== null) {
                    $acc[$group][$id]['sums'][$i] = ($acc[$group][$id]['sums'][$i] ?? Decimal::zero())->add($value);
                }
            }
        };

        $paid = [];

        foreach ($snapshot->payments as $payment) {
            $allocation = $allocations[(int) $payment['payid']];
            $amount = Decimal::of($payment['amount']);
            $add('payment_sums', [$payment['y'], $payment['pay_type'], $payment['status']], [$amount]);
            $add('alloc_sums', [$allocation->candidateType ?? '(none)', $payment['pay_type'], $payment['status']], [$amount]);

            // Paid = incoming, status Executed or empty (Q-37), D-11 candidate target — as coverage_sums on the server.
            if ($payment['pay_type'] === 'Приход' && in_array($payment['status'], ['Executed', ''], true) && $allocation->candidateId !== null) {
                $paid[$allocation->candidateId] = ($paid[$allocation->candidateId] ?? Decimal::zero())->add($amount);
            }
        }

        foreach ($snapshot->documents as $id => $doc) {
            $h = $doc['header'];
            $balance = $doc['module'] === 'Invoice' ? Decimal::of($h['balance']) : null;
            $add('doc_sums', [$doc['module'], $h['y'], $h['taxtype']],
                [Decimal::of($h['subtotal']), Decimal::of($h['pre_tax_total']), Decimal::of($h['total']), $balance]);

            if (in_array($doc['module'], ['Invoice', 'SalesOrder'], true)) {
                $add('coverage_sums', [$doc['module'], $h['status']], [Decimal::of($h['total']), $paid[$id] ?? Decimal::zero()]);
            }

            foreach ($doc['lines'] as $row) {
                $line = SourceRows::line($row);
                $add('line_sums', [$doc['module']], [$line->quantity, $line->gross(), $line->discountAmount, $line->margin ?? Decimal::zero()]);
            }
        }

        $rows = [];

        foreach ($acc as $group => $entries) {
            foreach ($entries as $entry) {
                $rows[$group][] = array_merge($entry['key'], [(string) $entry['n']],
                    array_map(static fn (?Decimal $sum) => $sum === null ? '' : $sum->toString(), $entry['sums']));
            }
        }

        return self::canonicalGroups($rows);
    }

    /**
     * @param list<string> $rows canonical rows of one group
     */
    public static function digest(string $key, string $group, array $rows): string
    {
        return hash_hmac('sha256', $group . "\n" . implode("\n", $rows), $key);
    }

    /**
     * @param array<string, list<list<string>>> $groups
     * @return array<string, list<string>>
     */
    private static function canonicalGroups(array $groups): array
    {
        $result = [];

        foreach (self::GROUPS as $group => $keyColumns) {
            $rows = [];

            foreach ($groups[$group] ?? [] as $row) {
                $cells = [];

                foreach (array_values($row) as $i => $cell) {
                    $cells[] = $i < $keyColumns || $cell === '' ? $cell : Decimal::of($cell)->toString();
                }

                $rows[] = implode('|', $cells);
            }

            sort($rows, SORT_STRING);

            if (count($rows) !== count(array_unique($rows))) {
                throw new RuntimeException("Duplicate control rows in $group.");
            }

            $result[$group] = $rows;
        }

        return $result;
    }

    private static function year(string $value): string
    {
        return $value === 'NULL' ? 'null' : $value;
    }

    private static function blank(string $value): string
    {
        return $value === 'NULL' ? '' : $value;
    }
}
