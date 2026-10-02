<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\FinanceDocument;

/**
 * Numbering of records created in EspoCRM (finance documents, payments): prefix + counter without padding; the first
 * number is the Vtiger cur_id at the audit snapshot (finance-contract.md §6).
 */
final class NumberSeries
{
    public function __construct(
        public readonly string $entityType,
        public readonly string $prefix,
        public readonly int $firstNumber,
    ) {}
}
