<?php

declare(strict_types=1);

namespace Itvolga\Tests\Finance\Support;

use Espo\Modules\Itvolga\Tools\Finance\Decimal;
use Espo\Modules\Itvolga\Tools\Finance\Payment\Direction;
use Espo\Modules\Itvolga\Tools\Finance\Payment\SourcePayment;
use Espo\Modules\Itvolga\Tools\Finance\Source\SourceDocument;

/**
 * Private numeric snapshot of live documents, lines and payments (scripts/audit/sql/47_finance_snapshot_private.sql).
 * Lives outside Git; nothing from it is printed.
 */
final class SourceSnapshot
{
    /**
     * @param array<int, array{module: string, header: array<string, string>, lines: list<array<string, string>>}> $documents
     * @param list<array<string, string>> $payments
     * @param array<int, list<int>> $links payment id → live invoices linked through vtiger_crmentityrel
     */
    private function __construct(
        public readonly array $documents,
        public readonly array $payments,
        public readonly array $links,
    ) {}

    public static function load(string $file): self
    {
        $kinds = PrivateTsv::read($file);
        $documents = [];

        foreach ($kinds['doc'] ?? [] as $row) {
            $documents[(int) $row['id']] = ['module' => $row['m'], 'header' => $row, 'lines' => []];
        }

        foreach ($kinds['line'] ?? [] as $row) {
            $documents[(int) $row['id']]['lines'][] = $row;
        }

        $links = [];

        foreach ($kinds['rel'] ?? [] as $row) {
            $links[(int) $row['payid']][] = (int) $row['invoiceid'];
        }

        return new self($documents, $kinds['pay'] ?? [], $links);
    }

    public function sourceDocument(int $id): SourceDocument
    {
        $doc = $this->documents[$id];

        return SourceRows::document($doc['header'], $doc['lines']);
    }

    /**
     * @param array<string, string> $row
     */
    public function sourcePayment(array $row): SourcePayment
    {
        $id = (int) $row['payid'];

        return new SourcePayment(
            $id,
            Direction::fromSource($row['pay_type']),
            $row['status'],
            Decimal::of($row['amount']),
            (int) $row['related_to'],
            $row['related_type'],
            $row['related_deleted'] === '1',
            $this->links[$id] ?? [],
        );
    }
}
