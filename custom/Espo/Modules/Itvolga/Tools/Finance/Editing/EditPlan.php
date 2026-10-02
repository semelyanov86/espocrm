<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Finance\Editing;

use Espo\Modules\Itvolga\Tools\Finance\Totals;

/**
 * What a document save does with its lines and totals (DocumentEditor).
 */
final class EditPlan
{
    /**
     * @param list<PlannedLine> $lines the lines that remain, in order
     * @param list<string> $removedIds items to delete
     */
    public function __construct(
        /** Totals and line amounts were computed by DocumentCalculator; false keeps the stored ones. */
        public readonly bool $recalculated,
        public readonly ?Totals $totals,
        public readonly array $lines,
        public readonly array $removedIds,
        /** The stored totals were the source system's and are replaced now: keep the originals (owner decision). */
        public readonly bool $replacesSourceTotals,
    ) {}
}
