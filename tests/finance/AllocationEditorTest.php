<?php

declare(strict_types=1);

namespace Itvolga\Tests\Finance;

use Espo\Modules\Itvolga\Tools\Finance\Decimal;
use Espo\Modules\Itvolga\Tools\Finance\Exceptions\InvalidValue;
use Espo\Modules\Itvolga\Tools\Finance\Exceptions\RuleNotSupported;
use Espo\Modules\Itvolga\Tools\Finance\Payment\AllocationEditor;
use Espo\Modules\Itvolga\Tools\Finance\Payment\AllocationInput;
use Espo\Modules\Itvolga\Tools\Finance\Payment\AllocationPlan;
use Espo\Modules\Itvolga\Tools\Finance\Payment\Direction;

/**
 * Edit rule of a payment's allocation table (stage 04.4, owner decisions 2026-10-02): the complete table replaces the
 * stored one; one row per document (a repeated application is refused, a re-save never duplicates); a payment moves to
 * another document by editing the row; a removed row is a cancelled allocation; Σ rows ≤ payment (D-49); outgoing
 * payments have no rows; overpaying a document is not this rule's business.
 */
final class AllocationEditorTest extends TestCase
{
    private const TARGETS = ['invoiceId' => 'Invoice', 'salesOrderId' => 'SalesOrder'];

    private AllocationEditor $editor;

    public function setUp(): void
    {
        $this->editor = new AllocationEditor();
    }

    public function testNewTableAndRemainder(): void
    {
        $plan = $this->editor->plan('10000.00', Direction::Incoming, [], [
            self::row(['invoiceId' => 'i1', 'amount' => '6000']),
            self::row(['salesOrderId' => 's1', 'amount' => '1500.50']),
        ], true);

        $this->assertSame(['Invoice:i1', 'SalesOrder:s1'], array_map(fn ($r) => $r->input->targetKey(), $plan->rows));
        $this->assertSame([1, 2], array_map(fn ($r) => $r->order, $plan->rows));
        $this->assertDecimal('7500.5', $plan->allocated);
        $this->assertDecimal('2499.5', $plan->remainder);
        $this->assertSame(['Invoice:i1', 'SalesOrder:s1'], $plan->affected);
        $this->assertTrue($plan->changed());

        // A prefilled or copied form: ids of another payment are dropped, not reused.
        $copy = $this->editor->plan('100', Direction::Incoming, [], [self::row(['id' => 'x', 'invoiceId' => 'i1', 'amount' => '100'])], true);
        $this->assertSame(null, $copy->rows[0]->input->id);
        $this->assertDecimal('0', $copy->remainder);
    }

    public function testRepeatedSaveChangesNothing(): void
    {
        $stored = self::stored();

        // The same table in another notation, with ids and without: nothing to write, no document affected.
        foreach ([
            [self::row(['id' => 'a1', 'invoiceId' => 'i1', 'amount' => '6000.00000000']), self::row(['id' => 'a2', 'salesOrderId' => 's1', 'amount' => '1500.5'])],
            [self::row(['invoiceId' => 'i1', 'amount' => '6000']), self::row(['salesOrderId' => 's1', 'amount' => '1500.50'])],
        ] as $index => $input) {
            $plan = $this->editor->plan('10000', Direction::Incoming, $stored, $input);
            $this->assertTrue(!$plan->changed(), "$index: unchanged");
            $this->assertSame([], $plan->affected, "$index: no document affected");
            $this->assertSame(['a1', 'a2'], array_map(fn ($r) => $r->input->id, $plan->rows), "$index: stored rows kept");
        }

        $omitted = $this->editor->plan('10000', Direction::Incoming, $stored, null);
        $this->assertTrue(!$omitted->changed(), 'a save without the table keeps it');
    }

    public function testMoveEditRemoveAndReorder(): void
    {
        $stored = self::stored();

        $moved = $this->editor->plan('10000', Direction::Incoming, $stored, [
            self::row(['id' => 'a1', 'invoiceId' => 'i2', 'amount' => '6000']),
            self::row(['id' => 'a2', 'salesOrderId' => 's1', 'amount' => '1500.50']),
        ]);
        $this->assertTrue($moved->rows[0]->targetChanged(), 'moved to another invoice, row kept');
        $this->assertSame('a1', $moved->rows[0]->input->id);
        $this->assertSame(['Invoice:i1', 'Invoice:i2'], $moved->affected);
        $this->assertSame(['Invoice:i1', 'Invoice:i2', 'SalesOrder:s1'], $moved->documents());

        $edited = $this->editor->plan('10000', Direction::Incoming, $stored, [
            self::row(['id' => 'a1', 'invoiceId' => 'i1', 'amount' => '8499.50']),
            self::row(['id' => 'a2', 'salesOrderId' => 's1', 'amount' => '1500.50']),
        ]);
        $this->assertTrue($edited->rows[0]->amountChanged());
        $this->assertSame(['Invoice:i1'], $edited->affected);
        $this->assertDecimal('0', $edited->remainder);

        $removed = $this->editor->plan('10000', Direction::Incoming, $stored, [self::row(['id' => 'a2', 'salesOrderId' => 's1', 'amount' => '1500.50'])]);
        $this->assertSame(['a1'], array_map(fn ($r) => $r->id, $removed->removed), 'a missing row is cancelled');
        $this->assertSame(['Invoice:i1'], $removed->affected);
        $this->assertDecimal('8499.5', $removed->remainder, 'the cancelled share returns to the payment');

        $all = $this->editor->plan('10000', Direction::Incoming, $stored, []);
        $this->assertSame(2, count($all->removed));
        $this->assertDecimal('10000', $all->remainder);

        $reordered = $this->editor->plan('10000', Direction::Incoming, $stored, [
            self::row(['id' => 'a2', 'salesOrderId' => 's1', 'amount' => '1500.50']),
            self::row(['id' => 'a1', 'invoiceId' => 'i1', 'amount' => '6000']),
        ]);
        $this->assertTrue($reordered->changed(), 'order is stored');
        $this->assertSame([], $reordered->affected, 'order changes no settlement');

        // Remove and add the same document again: the stored row of that document is kept, not duplicated.
        $readded = $this->editor->plan('10000', Direction::Incoming, $stored, [
            self::row(['salesOrderId' => 's1', 'amount' => '1500.50']),
            self::row(['invoiceId' => 'i1', 'amount' => '100']),
        ]);
        $this->assertSame(['a2', 'a1'], array_map(fn ($r) => $r->input->id, $readded->rows));
        $this->assertSame([], $readded->removed);
    }

    public function testRefusals(): void
    {
        $stored = self::stored();
        $cases = [
            'second row for the same document' => [fn () => $this->editor->plan('10000', Direction::Incoming, [], [
                self::row(['invoiceId' => 'i1', 'amount' => '1']), self::row(['invoiceId' => 'i1', 'amount' => '2'])]), 'allocationDuplicateTarget', 2, null],
            'id of another payment' => [fn () => $this->editor->plan('10000', Direction::Incoming, $stored, [
                self::row(['id' => 'zz', 'invoiceId' => 'i1', 'amount' => '1'])]), 'unknownAllocation', 1, null],
            'id used twice' => [fn () => $this->editor->plan('10000', Direction::Incoming, $stored, [
                self::row(['id' => 'a1', 'invoiceId' => 'i1', 'amount' => '1']), self::row(['id' => 'a1', 'invoiceId' => 'i2', 'amount' => '1'])]), 'unknownAllocation', 2, null],
            'one kopeck over the payment' => [fn () => $this->editor->plan('10000', Direction::Incoming, [], [
                self::row(['invoiceId' => 'i1', 'amount' => '6000']), self::row(['invoiceId' => 'i2', 'amount' => '4000.01'])]), 'overAllocation', null, 'amount'],
            'payment lowered below its rows' => [fn () => $this->editor->plan('7500.49', Direction::Incoming, $stored, null), 'amountBelowAllocated', null, 'amount'],
            'negative payment' => [fn () => $this->editor->plan('-1', Direction::Incoming, [], []), 'negativeValue', null, 'amount'],
            'payment with a fraction of a kopeck' => [fn () => $this->editor->plan('1.005', Direction::Incoming, [], []), 'tooManyDecimals', null, 'amount'],
            'payment as float' => [fn () => $this->editor->plan(1.5, Direction::Incoming, [], []), 'float', null, 'amount'],
            'no payment amount' => [fn () => $this->editor->plan('', Direction::Incoming, [], []), 'required', null, 'amount'],
            'payment too large' => [fn () => $this->editor->plan(str_repeat('9', 18), Direction::Incoming, [], []), 'tooLarge', null, 'amount'],
        ];

        foreach ($cases as $name => [$call, $key, $line, $field]) {
            $e = $this->assertThrows(InvalidValue::class, $call);
            $this->assertSame($key, $e->key, "$name: key");
            $this->assertSame($line, $e->documentLine, "$name: line");
            $this->assertSame($field, $e->field, "$name: field");
            $this->assertTrue(!preg_match('/\d{3}/', $e->getMessage()), "$name: no amount in the message");
        }

        // An outgoing payment has no rows (D-49, Q-36), also when it is switched to outgoing with rows kept.
        foreach ([
            fn () => $this->editor->plan('100', Direction::Outgoing, [], [self::row(['invoiceId' => 'i1', 'amount' => '100'])]),
            fn () => $this->editor->plan('10000', Direction::Outgoing, $stored, null),
        ] as $call) {
            $e = $this->assertThrows(RuleNotSupported::class, $call);
            $this->assertSame('outgoingAllocation', $e->rule);
        }

        $cleared = $this->editor->plan('10000', Direction::Outgoing, $stored, []);
        $this->assertSame(2, count($cleared->removed), 'switching to outgoing together with clearing the table is allowed');
        $this->assertDecimal('0', $this->editor->plan('0', Direction::Incoming, [], [])->remainder, 'a zero payment without rows');
    }

    public function testRowRefusals(): void
    {
        $cases = [
            'no document' => [['amount' => '1'], 'allocationTargetRequired', null],
            'both documents' => [['invoiceId' => 'i1', 'salesOrderId' => 's1', 'amount' => '1'], 'allocationTargetExclusive', 'salesOrder'],
            'document id of another type' => [['invoiceId' => 5, 'amount' => '1'], 'badAllocation', null],
            'bad row id' => [['id' => '', 'invoiceId' => 'i1', 'amount' => '1'], 'badAllocation', null],
            'no amount' => [['invoiceId' => 'i1'], 'required', 'amount'],
            'zero' => [['invoiceId' => 'i1', 'amount' => '0.00'], 'allocationNotPositive', 'amount'],
            'negative' => [['invoiceId' => 'i1', 'amount' => '-1'], 'allocationNotPositive', 'amount'],
            'fraction of a kopeck' => [['invoiceId' => 'i1', 'amount' => '1.005'], 'tooManyDecimals', 'amount'],
            'float' => [['invoiceId' => 'i1', 'amount' => 1.5], 'float', 'amount'],
            'not a number' => [['invoiceId' => 'i1', 'amount' => '1,5'], 'notDecimal', 'amount'],
        ];

        foreach ($cases as $name => [$raw, $key, $field]) {
            $e = $this->assertThrows(InvalidValue::class, fn () => AllocationInput::fromArray($raw, 3, self::TARGETS));
            $this->assertSame($key, $e->key, "$name: key");
            $this->assertSame(3, $e->documentLine, "$name: row");
            $this->assertSame($field, $e->field, "$name: field");
        }

        // Planned, cancelled and delayed payments may be allocated: only the settlement leaves them out (D-49).
        $this->assertDecimal('0', $this->editor->plan('100', Direction::Incoming, [], [self::row(['invoiceId' => 'i1', 'amount' => '100'])])->remainder);
        $this->assertSame(['Invoice:a', 'Invoice:b', 'SalesOrder:a'], AllocationPlan::sortedKeys(['SalesOrder:a', 'Invoice:b', 'Invoice:a', 'Invoice:b']));
    }

    /**
     * @return list<AllocationInput> a1 → invoice i1 6000, a2 → sales order s1 1500.50
     */
    private static function stored(): array
    {
        return [
            new AllocationInput('a1', 'Invoice', 'i1', Decimal::of('6000.00000000')),
            new AllocationInput('a2', 'SalesOrder', 's1', Decimal::of('1500.50000000')),
        ];
    }

    /**
     * @param array<string, mixed> $raw
     */
    private static function row(array $raw): AllocationInput
    {
        static $line = 0;

        return AllocationInput::fromArray($raw, ++$line, self::TARGETS);
    }
}
