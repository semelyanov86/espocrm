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
 * Paid = allocations of incoming payments in status Executed or with an empty status (old records made before the
 * status existed; owner decision Q-37); planned, cancelled, delayed and outgoing payments never count (D-49).
 */
final class AllocationCalculator
{
    /** @var list<string> */
    public const COUNTED_STATUSES = ['Executed', ''];

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
            $this->requireAllocation($allocation);
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
        $excluded = Decimal::zero();
        $counted = 0;

        foreach ($shares as $share) {
            $this->requireAllocation($share->amount);

            if ($share->direction === Direction::Incoming && in_array($share->status, self::COUNTED_STATUSES, true)) {
                $paid = $paid->add($share->amount);
                $counted++;
            } else {
                $excluded = $excluded->add($share->amount);
            }
        }

        return new Settlement($total, $paid, $total->sub($paid), $this->state($total, $paid), $counted, $excluded);
    }

    /**
     * Settlement of a document from its stored paid sum (computed by settle() from the allocations): when only the
     * total changes (an item edit), the paid sum stays and the balance and state follow the new total.
     */
    public function fromPaid(Decimal $total, Decimal $paid): Settlement
    {
        $this->requireMoney($paid, 'Paid sum');

        if ($paid->isNegative()) {
            throw new InvalidValue('Paid sum is never negative.');
        }

        return new Settlement($total, $paid, $total->sub($paid), $this->state($total, $paid), null, null);
    }

    private function state(Decimal $total, Decimal $paid): SettlementState
    {
        return match (true) {
            $paid->isZero() => SettlementState::Unpaid,
            $paid->compare($total) < 0 => SettlementState::Partial,
            $paid->compare($total) === 0 => SettlementState::Paid,
            default => SettlementState::Overpaid,
        };
    }

    /**
     * Every allocation, wherever it comes from, is positive and in kopecks (D-49).
     */
    private function requireAllocation(Decimal $amount): void
    {
        $this->requireMoney($amount, 'Allocation amount');

        if (!$amount->isPositive()) {
            throw new InvalidValue('Allocation amount must be positive.');
        }
    }

    private function requireMoney(Decimal $value, string $name): void
    {
        if ($value->significantScale() > Scale::MONEY) {
            throw new InvalidValue("$name has fractions of a kopeck: {$value->toString()}.");
        }
    }
}
