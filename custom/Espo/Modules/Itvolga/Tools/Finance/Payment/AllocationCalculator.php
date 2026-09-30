<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Finance\Payment;

use Espo\Modules\Itvolga\Tools\Finance\Decimal;
use Espo\Modules\Itvolga\Tools\Finance\Exceptions\InvalidValue;
use Espo\Modules\Itvolga\Tools\Finance\Exceptions\OverAllocation;
use Espo\Modules\Itvolga\Tools\Finance\Scale;

/**
 * Sums of payment allocations: what is left of a payment, and how much of a document is paid.
 *
 * Paid = allocations of incoming payments in status Executed — the definition of the source audit
 * (finance-contract.md §8); planned, cancelled and outgoing payments never count; an empty status is kept apart (Q-37).
 */
final class AllocationCalculator
{
    public const COUNTED_STATUS = 'Executed';

    /**
     * Unallocated rest of a payment. Every allocation must be positive and in kopecks; together they may not exceed
     * the payment (a payment can be split between documents, not over-spent).
     *
     * @param iterable<Decimal> $allocations
     */
    public function remainder(Decimal $paymentAmount, iterable $allocations): Decimal
    {
        if ($paymentAmount->isNegative()) {
            throw new InvalidValue('Payment amount is never negative: the direction carries the sign.');
        }

        $this->requireMoney($paymentAmount, 'Payment amount');
        $allocated = Decimal::zero();

        foreach ($allocations as $allocation) {
            $this->requireMoney($allocation, 'Allocation amount');

            if (!$allocation->isPositive()) {
                throw new InvalidValue('Allocation amount must be positive.');
            }

            $allocated = $allocated->add($allocation);
        }

        if ($allocated->compare($paymentAmount) > 0) {
            throw new OverAllocation("Allocations {$allocated->toString()} exceed the payment {$paymentAmount->toString()}.");
        }

        return $paymentAmount->sub($allocated);
    }

    /**
     * @param iterable<AllocationShare> $shares
     */
    public function settle(Decimal $total, iterable $shares): Settlement
    {
        $paid = Decimal::zero();
        $unknown = Decimal::zero();
        $excluded = Decimal::zero();
        $counted = 0;

        foreach ($shares as $share) {
            if ($share->amount->isNegative()) {
                throw new InvalidValue('Allocation amount is never negative.');
            }

            if ($share->direction === Direction::Incoming && $share->status === self::COUNTED_STATUS) {
                $paid = $paid->add($share->amount);
                $counted++;
            } elseif ($share->direction === Direction::Incoming && $share->status === '') {
                $unknown = $unknown->add($share->amount);
            } else {
                $excluded = $excluded->add($share->amount);
            }
        }

        $state = match (true) {
            $counted === 0 || $paid->isZero() => SettlementState::Unpaid,
            $paid->compare($total) < 0 => SettlementState::Partial,
            $paid->compare($total) === 0 => SettlementState::Paid,
            default => SettlementState::Overpaid,
        };

        return new Settlement($total, $paid, $total->sub($paid), $state, $counted, $unknown, $excluded);
    }

    private function requireMoney(Decimal $value, string $name): void
    {
        if ($value->significantScale() > Scale::MONEY) {
            throw new InvalidValue("$name has fractions of a kopeck: {$value->toString()}.");
        }
    }
}
