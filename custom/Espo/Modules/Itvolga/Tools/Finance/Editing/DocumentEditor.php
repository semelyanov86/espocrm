<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Finance\Editing;

use Espo\Modules\Itvolga\Tools\Finance\DocumentCalculator;
use Espo\Modules\Itvolga\Tools\Finance\Exceptions\InvalidValue;

/**
 * Decides what a document save does with its lines and totals (Quote, SalesOrder, Invoice; later Act).
 *
 * A new document is always calculated by DocumentCalculator (D-47). A saved one is recalculated only when a
 * calculation input changes: a header input (tax mode, discount, shipping, adjustment), a line added or removed, or a
 * line quantity, price, discount, tax rate or purchase cost. Other edits — status, dates, a line's product, description
 * or position — keep the stored totals and line amounts. This one rule serves both kinds of documents (owner decision
 * 2026-10-01): an imported document keeps the Vtiger totals (D-05) until its calculation inputs are edited; then it
 * is recalculated like a new one (historical 18 % lines are refused, D-21) and the caller keeps the originals.
 */
final class DocumentEditor
{
    public function __construct(
        private readonly DocumentCalculator $calculator = new DocumentCalculator(),
    ) {}

    /**
     * @param ?list<LineInput> $lines the complete line table in order; null — the stored lines, unchanged
     */
    public function plan(?StoredDocument $stored, HeaderInputs $header, ?array $lines): EditPlan
    {
        if ($stored === null) {
            // Ids of a copied document (duplicate, «Создать заказ») belong to another document.
            $lines = array_map(static fn (LineInput $line) => $line->withId(null), $lines ?? []);
            $removedIds = [];
            $changed = true;
        } else {
            $lines ??= $stored->lines;
            $removedIds = $this->checkIds($stored, $lines);
            $changed = !$header->equals($stored->header) || $removedIds !== [] || $this->linesChanged($stored, $lines);
        }

        if (!$changed) {
            $planned = [];

            foreach (array_values($lines) as $index => $line) {
                $planned[] = new PlannedLine($line, $index + 1, null, null);
            }

            return new EditPlan(false, null, $planned, [], false);
        }

        $this->checkInputLimits($header, $lines);
        $totals = $this->calculator->calculate($header->toDocument(array_values($lines)));
        $planned = [];

        foreach (array_values($lines) as $index => $line) {
            $n = $index + 1;
            Limits::check($totals->lineAmounts[$index], Limits::LINE['amount'], 'amount', $n);
            Limits::check($totals->lineMargins[$index], Limits::LINE['margin'], 'margin', $n);
            $planned[] = new PlannedLine($line, $n, $totals->lineAmounts[$index], $totals->lineMargins[$index]);
        }

        Limits::check($totals->subtotal, Limits::TOTALS['subtotal'], 'subtotal');
        Limits::check($totals->preTaxTotal, Limits::TOTALS['preTaxTotal'], 'preTaxTotal');
        Limits::check($totals->grandTotal, Limits::TOTALS['grandTotal'], 'grandTotal');

        return new EditPlan(true, $totals, $planned, $removedIds, $stored?->hasSourceTotals ?? false);
    }

    /**
     * @param list<LineInput> $lines
     * @return list<string> ids of stored lines that are no longer in the table
     */
    private function checkIds(StoredDocument $stored, array $lines): array
    {
        $storedIds = array_map(static fn (LineInput $line) => (string) $line->id, $stored->lines);
        $seen = [];

        foreach (array_values($lines) as $index => $line) {
            if ($line->id === null) {
                continue;
            }

            if (!in_array($line->id, $storedIds, true) || isset($seen[$line->id])) {
                // An item of another document or one listed twice: never moved or copied silently.
                throw new InvalidValue('Line ' . ($index + 1) . ': unknown item.', 'unknownLine', $index + 1, 'id');
            }

            $seen[$line->id] = true;
        }

        return array_values(array_filter($storedIds, static fn (string $id) => !isset($seen[$id])));
    }

    /**
     * @param list<LineInput> $lines
     */
    private function linesChanged(StoredDocument $stored, array $lines): bool
    {
        $keys = [];

        foreach ($stored->lines as $line) {
            $keys[(string) $line->id] = $line->calculationKey();
        }

        foreach ($lines as $line) {
            if ($line->id === null || $keys[$line->id] !== $line->calculationKey()) {
                return true;
            }
        }

        return false;
    }

    /**
     * @param list<LineInput> $lines
     */
    private function checkInputLimits(HeaderInputs $header, array $lines): void
    {
        foreach (HeaderInputs::DECIMALS as $field) {
            Limits::check($header->value($field), Limits::HEADER[$field], $field);
        }

        foreach (array_values($lines) as $index => $line) {
            foreach (LineInput::DECIMALS as $field) {
                Limits::check($line->value($field), Limits::LINE[$field], $field, $index + 1);
            }
        }
    }
}
