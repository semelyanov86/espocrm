<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\SecurityKey\Core\Cbor;

use Espo\Modules\Itvolga\Tools\SecurityKey\Core\VerificationFailed;

/**
 * The CBOR subset of WebAuthn (RFC 8949; attestation objects, COSE keys, extension maps): unsigned and negative
 * integers, byte and text strings, arrays, maps with integer or text keys, false/true/null. Everything else is refused
 * rather than skipped: indefinite lengths, tags, floats, other simple values, reserved additional information, a length
 * beyond the input, a repeated map key, nesting deeper than MAX_DEPTH, more than MAX_ITEMS entries in one container and
 * an integer beyond the PHP range. Non-shortest integer encodings are accepted: the signed bytes are the raw input.
 */
final class CborDecoder
{
    public const MAX_DEPTH = 8;
    public const MAX_ITEMS = 64;

    /**
     * Decodes the whole input as one item; trailing bytes are refused.
     */
    public static function decode(string $bytes): mixed
    {
        $offset = 0;
        $value = self::item($bytes, $offset, 0);

        if ($offset !== strlen($bytes)) {
            throw self::malformed();
        }

        return $value;
    }

    /**
     * Decodes one item starting at the offset and moves the offset past it (a COSE key inside authenticator data is
     * followed by other bytes).
     */
    public static function decodeItem(string $bytes, int &$offset): mixed
    {
        return self::item($bytes, $offset, 0);
    }

    private static function item(string $bytes, int &$offset, int $depth): mixed
    {
        if ($depth > self::MAX_DEPTH) {
            throw self::malformed();
        }

        $initial = ord(self::take($bytes, $offset, 1));
        $major = $initial >> 5;
        $info = $initial & 0x1f;

        if ($major === 7) {
            return match ($info) {
                20 => false,
                21 => true,
                22 => null,
                default => throw self::malformed(),
            };
        }

        $argument = self::argument($bytes, $offset, $info);

        switch ($major) {
            case 0:
                return $argument;

            case 1:
                return -1 - $argument;

            case 2:
                return new ByteString(self::take($bytes, $offset, $argument));

            case 3:
                $text = self::take($bytes, $offset, $argument);

                if (!mb_check_encoding($text, 'UTF-8')) {
                    throw self::malformed();
                }

                return $text;

            case 4:
                self::checkCount($argument);
                $list = [];

                for ($i = 0; $i < $argument; $i++) {
                    $list[] = self::item($bytes, $offset, $depth + 1);
                }

                return $list;

            case 5:
                self::checkCount($argument);
                $map = new CborMap();

                for ($i = 0; $i < $argument; $i++) {
                    $key = self::item($bytes, $offset, $depth + 1);

                    if (!is_int($key) && !is_string($key)) {
                        throw self::malformed();
                    }

                    if (!$map->add($key, self::item($bytes, $offset, $depth + 1))) {
                        throw self::malformed();
                    }
                }

                return $map;

            default:
                // Tags (major type 6).
                throw self::malformed();
        }
    }

    private static function argument(string $bytes, int &$offset, int $info): int
    {
        if ($info < 24) {
            return $info;
        }

        $value = match ($info) {
            24 => ord(self::take($bytes, $offset, 1)),
            25 => unpack('n', self::take($bytes, $offset, 2))[1],
            26 => unpack('N', self::take($bytes, $offset, 4))[1],
            27 => unpack('J', self::take($bytes, $offset, 8))[1],
            // 28-30 are reserved, 31 is an indefinite length.
            default => throw self::malformed(),
        };

        // A 64-bit argument above PHP_INT_MAX unpacks as a negative number.
        if (!is_int($value) || $value < 0) {
            throw self::malformed();
        }

        return $value;
    }

    private static function take(string $bytes, int &$offset, int $length): string
    {
        if ($length > strlen($bytes) - $offset) {
            throw self::malformed();
        }

        $part = substr($bytes, $offset, $length);
        $offset += $length;

        return $part;
    }

    private static function checkCount(int $count): void
    {
        if ($count > self::MAX_ITEMS) {
            throw self::malformed();
        }
    }

    private static function malformed(): VerificationFailed
    {
        return new VerificationFailed(VerificationFailed::MALFORMED);
    }
}
