<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Finance\Payment;

use Espo\Modules\Itvolga\Tools\Finance\Decimal;
use Espo\Modules\Itvolga\Tools\Finance\Editing\Limits;
use Espo\Modules\Itvolga\Tools\Finance\Editing\Values;
use Espo\Modules\Itvolga\Tools\Finance\Exceptions\InvalidValue;
use Espo\Modules\Itvolga\Tools\Finance\Exceptions\OverAllocation;
use Espo\Modules\Itvolga\Tools\Finance\Exceptions\RuleNotSupported;
use Espo\Modules\Itvolga\Tools\Finance\Scale;

/**
 * Edit rule of a payment's allocation table (stage 04.4, owner decisions 2026-10-02): the table is given complete and
 * replaces the stored one — a row with an id keeps that stored row, a row without one is new (or keeps the stored row
 * of the same document, so a repeated save never duplicates), a stored row that is missing is removed (cancelled).
 * One row per document: a second row for the same document is refused, the payment moves to another document by
 * editing the row's target. Every row is positive and in kopecks; together they never exceed the payment
 * (AllocationCalculator::remainder); an outgoing payment has no rows (D-49, Q-36). Overpaying a document is allowed
 * (D-49): nothing here looks at the documents' totals.
 */
final class AllocationEditor
{
    public const AMOUNT_LIMIT = [25, 8];

    public function __construct(private readonly AllocationCalculator $calculator = new AllocationCalculator()) {}

    /**
     * @param list<AllocationInput> $stored rows of the saved payment in their order ([] for a new payment)
     * @param ?list<AllocationInput> $input the complete table of the save, null when it is not given (rows kept)
     * @param bool $newPayment ids of the input are dropped (a copied or prefilled form has no stored rows)
     */
    public function plan(
        mixed $amount,
        Direction $direction,
        array $stored,
        ?array $input,
        bool $newPayment = false,
    ): AllocationPlan {
        $amount = $this->paymentAmount($amount);

        if ($newPayment && $input !== null) {
            $input = array_map(static fn (AllocationInput $row) => $row->withId(null), $input);
        }

        $rows = $input === null ? $stored : $this->match($stored, $input);
        $storedById = [];
        $storedOrder = [];

        foreach ($stored as $index => $row) {
            $storedById[(string) $row->id] = $row;
            $storedOrder[(string) $row->id] = $index + 1;
        }

        $planned = [];
        $targets = [];

        foreach ($rows as $index => $row) {
            $line = $index + 1;

            if (isset($targets[$row->targetKey()])) {
                throw new InvalidValue("Row $line: the document is already in the table.", 'allocationDuplicateTarget',
                    $line);
            }

            $targets[$row->targetKey()] = true;
            $previous = $row->id !== null ? $storedById[$row->id] : null;
            $planned[] = new PlannedAllocation($row, $line, $previous,
                $row->id !== null ? $storedOrder[$row->id] : null);
        }

        if ($direction === Direction::Outgoing && $planned !== []) {
            throw new RuleNotSupported('outgoingAllocation', 'D-49',
                'An outgoing payment is not allocated to documents.', null, 'direction');
        }

        try {
            $remainder = $this->calculator->remainder($amount,
                array_map(static fn (PlannedAllocation $row) => $row->input->amount, $planned));
        } catch (OverAllocation) {
            // Messages of the core carry amounts: only the kind of refusal leaves this class.
            throw new InvalidValue('Allocations exceed the payment.',
                $input === null ? 'amountBelowAllocated' : 'overAllocation', null, 'amount');
        }

        $kept = array_flip(array_filter(array_map(static fn (PlannedAllocation $row) => $row->input->id, $planned)));
        $removed = array_values(array_filter($stored, static fn (AllocationInput $row) => !isset($kept[$row->id])));

        return new AllocationPlan($planned, $removed, $this->affected($planned, $removed), $amount->sub($remainder),
            $remainder);
    }

    /**
     * Payment amount: required, not negative (the direction carries the sign), in kopecks, fits DECIMAL(25,8).
     */
    public function paymentAmount(mixed $value): Decimal
    {
        if ($value === null || $value === '') {
            throw new InvalidValue('Payment amount is required.', 'required', null, 'amount');
        }

        $amount = $value instanceof Decimal ? $value : Values::decimal($value, 'amount', null);
        Limits::check($amount, self::AMOUNT_LIMIT, 'amount');

        if ($amount->significantScale() > Scale::MONEY) {
            throw new InvalidValue('Payment amount has fractions of a kopeck.', 'tooManyDecimals', null, 'amount');
        }

        if ($amount->isNegative()) {
            throw new InvalidValue('Payment amount is negative.', 'negativeValue', null, 'amount');
        }

        return $amount;
    }

    /**
     * Ids of the input must be stored rows of this payment, each at most once. A row without an id keeps the stored
     * row of the same document that no other input row claims.
     *
     * @param list<AllocationInput> $stored
     * @param list<AllocationInput> $input
     * @return list<AllocationInput>
     */
    private function match(array $stored, array $input): array
    {
        $ids = [];

        foreach ($stored as $row) {
            $ids[(string) $row->id] = $row;
        }

        $claimed = [];

        foreach ($input as $index => $row) {
            if ($row->id === null) {
                continue;
            }

            if (!isset($ids[$row->id]) || isset($claimed[$row->id])) {
                throw new InvalidValue('Row ' . ($index + 1) . ': not a row of this payment.', 'unknownAllocation',
                    $index + 1);
            }

            $claimed[$row->id] = true;
        }

        $byTarget = [];

        foreach ($stored as $row) {
            if (!isset($claimed[$row->id])) {
                $byTarget[$row->targetKey()] ??= $row->id;
            }
        }

        return array_map(static function (AllocationInput $row) use (&$byTarget): AllocationInput {
            if ($row->id !== null || !isset($byTarget[$row->targetKey()])) {
                return $row;
            }

            $id = $byTarget[$row->targetKey()];
            unset($byTarget[$row->targetKey()]);

            return $row->withId($id);
        }, $input);
    }

    /**
     * Documents whose counted sum changes: targets of new and removed rows, both targets of a moved row, the target of
     * a row with another amount. A changed order changes nothing in the documents.
     *
     * @param list<PlannedAllocation> $planned
     * @param list<AllocationInput> $removed
     * @return list<string>
     */
    private function affected(array $planned, array $removed): array
    {
        $keys = array_map(static fn (AllocationInput $row) => $row->targetKey(), $removed);

        foreach ($planned as $row) {
            if ($row->isNew() || $row->targetChanged() || $row->amountChanged()) {
                $keys[] = $row->input->targetKey();
            }

            if ($row->targetChanged()) {
                $keys[] = $row->previous?->targetKey();
            }
        }

        return AllocationPlan::sortedKeys(array_filter($keys));
    }
}
