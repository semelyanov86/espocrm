<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\SecurityKey\Core;

use RuntimeException;

/**
 * A refused security-key response or stored key. The reason is a stable code; the message never carries the input
 * (bytes, JSON, ids), so the exception may be logged as is.
 */
final class VerificationFailed extends RuntimeException
{
    public const MALFORMED = 'malformed';
    public const TOO_LARGE = 'tooLarge';
    public const TYPE = 'type';
    public const CHALLENGE = 'challenge';
    public const ORIGIN = 'origin';
    public const CROSS_ORIGIN = 'crossOrigin';
    public const RP_ID = 'rpId';
    public const USER_PRESENCE = 'userPresence';
    public const FLAGS = 'flags';
    public const ALGORITHM = 'algorithm';
    public const KEY = 'key';
    public const CREDENTIAL = 'credential';
    public const USER_HANDLE = 'userHandle';
    public const SIGNATURE = 'signature';
    public const COUNTER = 'counter';

    public function __construct(public readonly string $reason)
    {
        parent::__construct('Security key: ' . $reason);
    }
}
