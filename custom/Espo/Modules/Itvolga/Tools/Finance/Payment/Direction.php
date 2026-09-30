<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Finance\Payment;

use Espo\Modules\Itvolga\Tools\Finance\Exceptions\InvalidValue;

/**
 * Payment direction (sp_payments.pay_type). The amount is never negative; the direction carries the sign.
 */
enum Direction: string
{
    case Incoming = 'incoming';
    case Outgoing = 'outgoing';

    public static function fromSource(string $payType): self
    {
        return match ($payType) {
            'Приход' => self::Incoming,
            'Expense' => self::Outgoing,
            default => throw new InvalidValue("Unknown payment type '$payType'."),
        };
    }
}
