<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Finance\Editing;

/**
 * A saved document as the editor needs it: header inputs, lines in order (with their item ids) and whether its
 * stored totals are still the ones of the source system (imported and never recalculated, D-05).
 */
final class StoredDocument
{
    /**
     * @param list<LineInput> $lines
     */
    public function __construct(
        public readonly HeaderInputs $header,
        public readonly array $lines,
        public readonly bool $hasSourceTotals,
    ) {}
}
