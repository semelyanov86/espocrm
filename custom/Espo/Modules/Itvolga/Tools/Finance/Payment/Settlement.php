<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Finance\Payment;

use Espo\Modules\Itvolga\Tools\Finance\Decimal;

/**
 * Payment state of a document computed from its allocations. A control value for reports and the card (D-26):
 * the document status is never derived from it.
 */
final class Settlement
{
    public function __construct(
        public readonly Decimal $total,
        /** Sum of counted allocations (incoming, status Executed). */
        public readonly Decimal $paid,
        /** total − paid; negative when overpaid. */
        public readonly Decimal $balance,
        public readonly SettlementState $state,
        public readonly int $countedPayments,
        /** Incoming allocations with an empty status: not counted until Q-37 is decided. */
        public readonly Decimal $unknownStatusAmount,
        /** Allocations that never count: outgoing, planned, cancelled, delayed. */
        public readonly Decimal $excludedAmount,
    ) {}
}
