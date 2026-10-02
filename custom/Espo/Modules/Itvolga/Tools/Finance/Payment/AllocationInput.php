<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Finance\Payment;

use Espo\Modules\Itvolga\Tools\Finance\Decimal;
use Espo\Modules\Itvolga\Tools\Finance\Editing\Limits;
use Espo\Modules\Itvolga\Tools\Finance\Editing\Values;
use Espo\Modules\Itvolga\Tools\Finance\Exceptions\InvalidValue;
use Espo\Modules\Itvolga\Tools\Finance\Scale;

/**
 * One row of a payment's allocation table: the share of the payment given to exactly one document (an invoice or a
 * sales order). The amount is positive and in kopecks (D-49). Refusals carry the row and the field, never the value.
 */
final class AllocationInput
{
    /** Decimal inputs of a row (checked for floats on the raw API input as well). */
    public const DECIMALS = ['amount'];
    /** DECIMAL(25,8) of PaymentAllocation.amount. */
    public const AMOUNT_LIMIT = [25, 8];

    public function __construct(
        public readonly ?string $id,
        public readonly string $targetType,
        public readonly string $targetId,
        public readonly Decimal $amount,
    ) {}

    /**
     * @param array<string, mixed> $raw {id?, invoiceId?, salesOrderId?, amount}; other keys (names) are ignored
     * @param array<string, string> $targets target id attribute => document entity type (invoiceId => Invoice)
     */
    public static function fromArray(array $raw, int $row, array $targets): self
    {
        $id = $raw['id'] ?? null;

        if ($id !== null && (!is_string($id) || $id === '')) {
            throw new InvalidValue("Row $row: bad id.", 'badAllocation', $row);
        }

        $chosen = [];

        foreach ($targets as $attribute => $entityType) {
            $value = $raw[$attribute] ?? null;

            if ($value === null || $value === '') {
                continue;
            }

            if (!is_string($value)) {
                throw new InvalidValue("Row $row: bad document id.", 'badAllocation', $row);
            }

            $chosen[] = [$entityType, $value, substr($attribute, 0, -2)];
        }

        if ($chosen === []) {
            throw new InvalidValue("Row $row: no document.", 'allocationTargetRequired', $row);
        }

        if (count($chosen) > 1) {
            throw new InvalidValue("Row $row: several documents.", 'allocationTargetExclusive', $row,
                $chosen[1][2]);
        }

        $value = $raw['amount'] ?? null;

        if ($value === null || $value === '') {
            throw new InvalidValue("Row $row: amount is required.", 'required', $row, 'amount');
        }

        $amount = Values::decimal($value, 'amount', $row);
        Limits::check($amount, self::AMOUNT_LIMIT, 'amount', $row);

        if ($amount->significantScale() > Scale::MONEY) {
            throw new InvalidValue("Row $row: fractions of a kopeck.", 'tooManyDecimals', $row, 'amount');
        }

        if (!$amount->isPositive()) {
            throw new InvalidValue("Row $row: allocation must be positive.", 'allocationNotPositive', $row, 'amount');
        }

        return new self($id, $chosen[0][0], $chosen[0][1], $amount);
    }

    public function targetKey(): string
    {
        return $this->targetType . ':' . $this->targetId;
    }

    public function withId(?string $id): self
    {
        return new self($id, $this->targetType, $this->targetId, $this->amount);
    }
}
