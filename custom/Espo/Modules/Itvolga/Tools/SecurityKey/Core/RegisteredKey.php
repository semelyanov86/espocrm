<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\SecurityKey\Core;

/**
 * A verified registration: the new credential id, its public key and the initial signature counter.
 */
final class RegisteredKey
{
    public function __construct(
        public readonly string $credentialId,
        public readonly PublicKey $publicKey,
        public readonly int $signCount,
    ) {}
}
