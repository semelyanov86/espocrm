<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Finance\Payment;

use Espo\Modules\Itvolga\Tools\Finance\Decimal;

/**
 * One allocation of a payment to a document, with the payment's direction and status.
 */
final class AllocationShare
{
    public function __construct(
        public readonly Decimal $amount,
        public readonly Direction $direction,
        public readonly string $status,
    ) {}

    public static function of(mixed $amount, Direction $direction, string $status): self
    {
        return new self(Decimal::of($amount), $direction, $status);
    }
}
