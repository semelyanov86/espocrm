<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Finance\Payment;

enum AllocationDecision: string
{
    /** Create PaymentAllocation(payment, target, amount = payment amount) — D-11. */
    case Allocate = 'allocate';
    /** Nothing to allocate. */
    case None = 'none';
    /** No confirmed rule: import reports the payment and waits for a decision (reason names the question). */
    case Unresolved = 'unresolved';
}
