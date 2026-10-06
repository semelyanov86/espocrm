<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\SecurityKey\Core\Cbor;

/**
 * A CBOR byte string (major type 2), kept apart from a text string (major type 3): COSE and attestation fields are
 * typed, and a text where bytes are due is refused.
 */
final class ByteString
{
    public function __construct(public readonly string $bytes) {}
}
