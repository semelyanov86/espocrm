<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Finance\Payment;

use Espo\Modules\Itvolga\Tools\Finance\Decimal;

/**
 * Allocation of one source payment. `candidate*` is the target that D-11 names literally (related_to, otherwise the
 * link); it is set even when nothing is allocated (Q-36, Unresolved), so reports can show the source reference.
 */
final class SourceAllocation
{
    /**
     * @param list<int> $conflictInvoiceIds invoices of the link that disagree with related_to (report only)
     */
    public function __construct(
        public readonly AllocationCategory $category,
        public readonly AllocationDecision $decision,
        public readonly ?string $candidateType,
        public readonly ?int $candidateId,
        public readonly ?Decimal $amount,
        public readonly array $conflictInvoiceIds = [],
        public readonly ?string $reason = null,
    ) {}
}
