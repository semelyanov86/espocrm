<?php

declare(strict_types=1);

namespace Itvolga\Tests\Finance;

use Espo\Modules\Itvolga\Tools\Finance\Decimal;
use Espo\Modules\Itvolga\Tools\Finance\Exceptions\InvalidValue;
use Espo\Modules\Itvolga\Tools\Finance\Exceptions\OverAllocation;
use Espo\Modules\Itvolga\Tools\Finance\Payment\AllocationCalculator;
use Espo\Modules\Itvolga\Tools\Finance\Payment\AllocationCategory;
use Espo\Modules\Itvolga\Tools\Finance\Payment\AllocationDecision;
use Espo\Modules\Itvolga\Tools\Finance\Payment\AllocationShare;
use Espo\Modules\Itvolga\Tools\Finance\Payment\Direction;
use Espo\Modules\Itvolga\Tools\Finance\Payment\SettlementState;
use Espo\Modules\Itvolga\Tools\Finance\Payment\SourceAllocationResolver;
use Espo\Modules\Itvolga\Tools\Finance\Payment\SourcePayment;

/**
 * Payment allocation: D-11 on every shape of the live data (33_allocation_check.sql), control sums of allocations
 * and the paid/balance state of a document.
 */
final class AllocationTest extends TestCase
{
    public function testSourceShapesFollowD11(): void
    {
        $resolver = new SourceAllocationResolver();
        // [payment, category, decision, target type, target id, conflicts]
        $cases = [
            'related_to and the same link' => [$this->payment(relatedTo: 101, links: [101]), AllocationCategory::BothSameInvoice, AllocationDecision::Allocate, 'Invoice', 101, []],
            'related_to only' => [$this->payment(relatedTo: 101), AllocationCategory::RelatedToInvoiceOnly, AllocationDecision::Allocate, 'Invoice', 101, []],
            'conflict: related_to wins' => [$this->payment(relatedTo: 101, links: [102]), AllocationCategory::ConflictRelOtherInvoice, AllocationDecision::Allocate, 'Invoice', 101, [102]],
            'sales order' => [$this->payment(relatedTo: 201, type: 'SalesOrder'), AllocationCategory::RelatedToSalesOrder, AllocationDecision::Allocate, 'SalesOrder', 201, []],
            'link only, incoming' => [$this->payment(links: [103]), AllocationCategory::RelOnly, AllocationDecision::Allocate, 'Invoice', 103, []],
            'nothing' => [$this->payment(), AllocationCategory::Unallocated, AllocationDecision::None, null, null, []],
            'link only, outgoing (Q-36: not allocated)' => [$this->payment(direction: Direction::Outgoing, links: [103]), AllocationCategory::RelOnly, AllocationDecision::None, 'Invoice', 103, []],
            'related_to deleted' => [$this->payment(relatedTo: 101, deleted: true), AllocationCategory::Other, AllocationDecision::Unresolved, null, null, []],
            'related_to deleted and a link (the link does not replace it)' => [$this->payment(relatedTo: 101, deleted: true, links: [102]), AllocationCategory::Other, AllocationDecision::Unresolved, null, null, []],
            'related_to non-document' => [$this->payment(relatedTo: 301, type: 'Accounts'), AllocationCategory::Other, AllocationDecision::Unresolved, null, null, []],
            'two links, no related_to' => [$this->payment(links: [104, 103]), AllocationCategory::Other, AllocationDecision::Unresolved, 'Invoice', 103, []],
            'two links next to related_to' => [$this->payment(relatedTo: 101, links: [101, 102]), AllocationCategory::Other, AllocationDecision::Unresolved, 'Invoice', 101, []],
            'sales order and a link' => [$this->payment(relatedTo: 201, type: 'SalesOrder', links: [101]), AllocationCategory::Other, AllocationDecision::Unresolved, 'SalesOrder', 201, []],
            'outgoing with related_to' => [$this->payment(direction: Direction::Outgoing, relatedTo: 101), AllocationCategory::Other, AllocationDecision::Unresolved, 'Invoice', 101, []],
            'zero payment' => [$this->payment(relatedTo: 101, amount: '0.00000000', status: ''), AllocationCategory::RelatedToInvoiceOnly, AllocationDecision::Unresolved, 'Invoice', 101, []],
        ];

        foreach ($cases as $name => [$payment, $category, $decision, $type, $id, $conflicts]) {
            $allocation = $resolver->resolve($payment);
            $this->assertSame($category, $allocation->category, "$name: category");
            $this->assertSame($decision, $allocation->decision, "$name: decision");
            $this->assertSame($type, $allocation->candidateType, "$name: target type");
            $this->assertSame($id, $allocation->candidateId, "$name: target id");
            $this->assertSame($conflicts, $allocation->conflictInvoiceIds, "$name: conflicts");

            if ($decision === AllocationDecision::Allocate) {
                // The source never splits a payment: the allocation is the whole amount.
                $this->assertTrue($allocation->amount !== null && $allocation->amount->equals($payment->amount), "$name: amount");
            } else {
                $this->assertSame(null, $allocation->amount, "$name: no amount without an allocation");
            }

            if ($decision === AllocationDecision::Unresolved) {
                $this->assertTrue($allocation->reason !== null && $allocation->reason !== '', "$name: reason");
            }
        }

        $this->assertTrue(str_contains((string) $resolver->resolve($this->payment(direction: Direction::Outgoing, links: [103]))->reason, 'Q-36'), 'outgoing link names Q-36');
        $this->assertSame(null, $resolver->resolve($this->payment())->reason, 'no reason when nothing references a document');
        $this->assertSame(Direction::Incoming, Direction::fromSource('Приход'));
        $this->assertSame(Direction::Outgoing, Direction::fromSource('Expense'));
        $this->assertThrows(InvalidValue::class, fn () => Direction::fromSource('Refund'));
    }

    public function testRemainderAndOverAllocation(): void
    {
        $calculator = new AllocationCalculator();

        $this->assertDecimal('5000', $calculator->remainder(Decimal::of('10000.00'), [Decimal::of('3000'), Decimal::of('2000.00')]));
        $this->assertDecimal('0', $calculator->remainder(Decimal::of('10000.00'), [Decimal::of('10000')]));
        $this->assertDecimal('10000', $calculator->remainder(Decimal::of('10000.00'), []));
        $this->assertThrows(OverAllocation::class, fn () => $calculator->remainder(Decimal::of('10000'), [Decimal::of('6000'), Decimal::of('4000.01')]));
        $this->assertThrows(InvalidValue::class, fn () => $calculator->remainder(Decimal::of('10000'), [Decimal::of('0')]), 'positive');
        $this->assertThrows(InvalidValue::class, fn () => $calculator->remainder(Decimal::of('10000'), [Decimal::of('-1')]), 'positive');
        $this->assertThrows(InvalidValue::class, fn () => $calculator->remainder(Decimal::of('10000'), [Decimal::of('0.005')]), 'kopeck');
        $this->assertThrows(InvalidValue::class, fn () => $calculator->remainder(Decimal::of('-5'), []), 'negative');

        // The same limits hold for settlement input: no fractions of a kopeck, no zero allocations.
        $this->assertThrows(InvalidValue::class, fn () => $calculator->settle(Decimal::of('1.00'), [AllocationShare::of('0.005', Direction::Incoming, 'Executed')]), 'kopeck');
        $this->assertThrows(InvalidValue::class, fn () => $calculator->settle(Decimal::of('1.00'), [AllocationShare::of('0', Direction::Incoming, 'Executed')]), 'positive');
        $this->assertThrows(InvalidValue::class, fn () => $calculator->settle(Decimal::of('1.00'), [AllocationShare::of('-1', Direction::Incoming, 'Executed')]), 'positive');
    }

    public function testSettlementOfADocument(): void
    {
        $calculator = new AllocationCalculator();
        $in = Direction::Incoming;
        $total = Decimal::of('10000.00000000');
        // [shares, state, paid, balance, counted, excluded]
        $cases = [
            'no payments' => [[], SettlementState::Unpaid, '0', '10000', 0, '0'],
            'paid exactly' => [[AllocationShare::of('10000.00', $in, 'Executed')], SettlementState::Paid, '10000', '0', 1, '0'],
            'partial' => [[AllocationShare::of('4000', $in, 'Executed')], SettlementState::Partial, '4000', '6000', 1, '0'],
            'two payments' => [[AllocationShare::of('4000', $in, 'Executed'), AllocationShare::of('6000', $in, 'Executed')], SettlementState::Paid, '10000', '0', 2, '0'],
            'overpaid' => [[AllocationShare::of('6000', $in, 'Executed'), AllocationShare::of('6000', $in, 'Executed')], SettlementState::Overpaid, '12000', '-2000', 2, '0'],
            'planned, cancelled, delayed, outgoing' => [[AllocationShare::of('1000', $in, 'Запланирован'), AllocationShare::of('2000', $in, 'Canceled'),
                AllocationShare::of('500', $in, 'Delayed'), AllocationShare::of('3000', Direction::Outgoing, 'Executed')], SettlementState::Unpaid, '0', '10000', 0, '6500'],
            'empty status counts as executed (Q-37)' => [[AllocationShare::of('4000', $in, ''), AllocationShare::of('6000', $in, 'Executed')], SettlementState::Paid, '10000', '0', 2, '0'],
        ];

        foreach ($cases as $name => [$shares, $state, $paid, $balance, $counted, $excluded]) {
            $settlement = $calculator->settle($total, $shares);
            $this->assertSame($state, $settlement->state, "$name: state");
            $this->assertDecimal($paid, $settlement->paid, "$name: paid");
            $this->assertDecimal($balance, $settlement->balance, "$name: balance");
            $this->assertSame($counted, $settlement->countedPayments, "$name: counted");
            $this->assertDecimal($excluded, $settlement->excludedAmount, "$name: excluded");
        }
    }

    /**
     * @param list<int> $links
     */
    private function payment(
        Direction $direction = Direction::Incoming,
        int $relatedTo = 0,
        string $type = 'Invoice',
        bool $deleted = false,
        array $links = [],
        string $amount = '12500.00000000',
        string $status = 'Executed',
    ): SourcePayment {
        return new SourcePayment(900, $direction, $status, Decimal::of($amount), $relatedTo, $relatedTo ? $type : '', $deleted, $links);
    }
}
