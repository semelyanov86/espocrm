<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\SecurityKey\Core;

/**
 * Base64url without padding (RFC 4648 §5), the encoding of every binary WebAuthn value on the wire. Decoding is strict:
 * the alphabet only, no padding, a size limit checked before decoding, and only the canonical form (PHP's decoder
 * also accepts non-zero trailing bits — "YWJ" and "YWI" both give "ab" — so the result is encoded back and compared).
 */
final class Base64Url
{
    public static function encode(string $bytes): string
    {
        return rtrim(strtr(base64_encode($bytes), '+/', '-_'), '=');
    }

    public static function decode(mixed $text, int $maxBytes): string
    {
        if (!is_string($text) || preg_match('/^[A-Za-z0-9_-]*$/D', $text) !== 1 || strlen($text) % 4 === 1) {
            throw new VerificationFailed(VerificationFailed::MALFORMED);
        }

        if (intdiv(strlen($text) * 3, 4) > $maxBytes) {
            throw new VerificationFailed(VerificationFailed::TOO_LARGE);
        }

        $bytes = base64_decode(strtr($text, '-_', '+/'), true);

        if ($bytes === false || self::encode($bytes) !== $text) {
            throw new VerificationFailed(VerificationFailed::MALFORMED);
        }

        return $bytes;
    }
}
