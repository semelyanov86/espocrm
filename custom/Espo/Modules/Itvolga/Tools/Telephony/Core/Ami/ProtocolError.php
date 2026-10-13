<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Telephony\Core\Ami;

use RuntimeException;

/**
 * A broken AMI stream or a refused action. The reason is a stable code; the message never carries the bytes, so the
 * exception may be logged as is.
 */
final class ProtocolError extends RuntimeException
{
    public const MESSAGE_TOO_LARGE = 'messageTooLarge';
    public const BUFFER_TOO_LARGE = 'bufferTooLarge';
    public const BAD_HEADER = 'badHeader';

    public function __construct(public readonly string $reason)
    {
        parent::__construct('AMI protocol: ' . $reason);
    }
}
