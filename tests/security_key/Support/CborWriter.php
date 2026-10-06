<?php

declare(strict_types=1);

namespace Itvolga\Tests\SecurityKey\Support;

/**
 * A minimal CBOR encoder for building test inputs, independent of the decoder under test. Items are composed from
 * already encoded parts, so malformed structures (repeated keys, wrong types) can be built on purpose.
 */
final class CborWriter
{
    public static function head(int $major, int $argument): string
    {
        $type = $major << 5;

        return match (true) {
            $argument < 24 => chr($type | $argument),
            $argument < 0x100 => chr($type | 24) . chr($argument),
            $argument < 0x10000 => chr($type | 25) . pack('n', $argument),
            $argument <= 0xFFFFFFFF => chr($type | 26) . pack('N', $argument),
            default => chr($type | 27) . pack('J', $argument),
        };
    }

    public static function int(int $value): string
    {
        return $value >= 0 ? self::head(0, $value) : self::head(1, -1 - $value);
    }

    public static function bytes(string $bytes): string
    {
        return self::head(2, strlen($bytes)) . $bytes;
    }

    public static function text(string $text): string
    {
        return self::head(3, strlen($text)) . $text;
    }

    public static function array(string ...$items): string
    {
        return self::head(4, count($items)) . implode('', $items);
    }

    /**
     * @param list<array{string, string}> $pairs Encoded keys and values.
     */
    public static function map(array $pairs): string
    {
        return self::head(5, count($pairs)) . implode('', array_map(static fn (array $pair) => $pair[0] . $pair[1], $pairs));
    }
}
