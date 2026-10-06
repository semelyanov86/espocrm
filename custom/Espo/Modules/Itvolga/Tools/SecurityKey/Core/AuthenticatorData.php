<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\SecurityKey\Core;

use Espo\Modules\Itvolga\Tools\SecurityKey\Core\Cbor\CborDecoder;
use Espo\Modules\Itvolga\Tools\SecurityKey\Core\Cbor\CborMap;

/**
 * Authenticator data (WebAuthn §6.1): rpIdHash (32) | flags (1) | signCount (4, unsigned big-endian) | attested
 * credential data when AT is set — AAGUID (16), credential id length (2), credential id, COSE public key | extensions
 * map when ED is set. Every length is checked before it is read and nothing may follow the declared parts.
 */
final class AuthenticatorData
{
    public const UP = 0x01;
    public const UV = 0x04;
    public const BE = 0x08;
    public const BS = 0x10;
    public const AT = 0x40;
    public const ED = 0x80;

    public const MAX_BYTES = 16384;
    public const MAX_CREDENTIAL_ID_BYTES = 1023;

    private function __construct(
        public readonly string $raw,
        public readonly string $rpIdHash,
        public readonly int $flags,
        public readonly int $signCount,
        public readonly ?string $credentialId,
        public readonly ?PublicKey $publicKey,
    ) {}

    public static function parse(string $bytes): self
    {
        $length = strlen($bytes);

        if ($length > self::MAX_BYTES) {
            throw new VerificationFailed(VerificationFailed::TOO_LARGE);
        }

        if ($length < 37) {
            throw self::malformed();
        }

        $flags = ord($bytes[32]);
        $signCount = unpack('N', substr($bytes, 33, 4))[1];
        $offset = 37;
        $credentialId = null;
        $publicKey = null;

        // Backup state without backup eligibility is not a valid combination (WebAuthn L3 §6.1).
        if (($flags & self::BS) !== 0 && ($flags & self::BE) === 0) {
            throw new VerificationFailed(VerificationFailed::FLAGS);
        }

        if (($flags & self::AT) !== 0) {
            if ($length < $offset + 18) {
                throw self::malformed();
            }

            $idLength = unpack('n', substr($bytes, $offset + 16, 2))[1];
            $offset += 18;

            if ($idLength < 1 || $idLength > self::MAX_CREDENTIAL_ID_BYTES || $idLength > $length - $offset) {
                throw self::malformed();
            }

            $credentialId = substr($bytes, $offset, $idLength);
            $offset += $idLength;
            $coseKey = CborDecoder::decodeItem($bytes, $offset);

            if (!$coseKey instanceof CborMap) {
                throw self::malformed();
            }

            $publicKey = PublicKey::fromCose($coseKey);
        }

        if (($flags & self::ED) !== 0 && !CborDecoder::decodeItem($bytes, $offset) instanceof CborMap) {
            throw self::malformed();
        }

        if ($offset !== $length) {
            throw self::malformed();
        }

        return new self(
            raw: $bytes,
            rpIdHash: substr($bytes, 0, 32),
            flags: $flags,
            signCount: $signCount,
            credentialId: $credentialId,
            publicKey: $publicKey,
        );
    }

    public function has(int $flag): bool
    {
        return ($this->flags & $flag) === $flag;
    }

    private static function malformed(): VerificationFailed
    {
        return new VerificationFailed(VerificationFailed::MALFORMED);
    }
}
