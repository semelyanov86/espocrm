<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Telephony;

use RuntimeException;

/**
 * A failed AMI exchange. The reason is a stable code; the message carries neither the secret nor the action.
 */
final class AmiError extends RuntimeException
{
    public const CONNECT = 'connect_failed';
    public const AUTH = 'auth_failed';
    public const TIMEOUT = 'timeout';
    public const CLOSED = 'closed';
    public const PROTOCOL = 'protocol';
    public const DENIED = 'denied';

    public function __construct(public readonly string $reason)
    {
        parent::__construct('AMI: ' . $reason);
    }
}
