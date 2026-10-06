<?php

declare(strict_types=1);

namespace Itvolga\Tests\SecurityKey;

use Espo\Modules\Itvolga\Tools\SecurityKey\Core\Cbor\ByteString;
use Espo\Modules\Itvolga\Tools\SecurityKey\Core\Cbor\CborDecoder;
use Espo\Modules\Itvolga\Tools\SecurityKey\Core\Cbor\CborMap;
use Espo\Modules\Itvolga\Tools\SecurityKey\Core\VerificationFailed as F;
use Itvolga\Tests\SecurityKey\Support\CborWriter as W;

final class CborDecoderTest extends SecurityKeyTestCase
{
    public function testRfc8949Examples(): void
    {
        // RFC 8949 Appendix A.
        $this->assertSame(0, CborDecoder::decode(self::bytes('00')));
        $this->assertSame(23, CborDecoder::decode(self::bytes('17')));
        $this->assertSame(24, CborDecoder::decode(self::bytes('18 18')));
        $this->assertSame(1000, CborDecoder::decode(self::bytes('19 03 e8')));
        $this->assertSame(1000000, CborDecoder::decode(self::bytes('1a 00 0f 42 40')));
        $this->assertSame(PHP_INT_MAX, CborDecoder::decode(self::bytes('1b 7f ff ff ff ff ff ff ff')));
        $this->assertSame(-1, CborDecoder::decode(self::bytes('20')));
        $this->assertSame(-1000, CborDecoder::decode(self::bytes('39 03 e7')));
        $this->assertSame(false, CborDecoder::decode(self::bytes('f4')));
        $this->assertSame(true, CborDecoder::decode(self::bytes('f5')));
        $this->assertSame(null, CborDecoder::decode(self::bytes('f6')));
        $this->assertSame('IETF', CborDecoder::decode(self::bytes('64 49 45 54 46')));
        $this->assertSame([1, [2, 3], [4, 5]], CborDecoder::decode(self::bytes('83 01 82 02 03 82 04 05')));

        $bytes = CborDecoder::decode(self::bytes('44 01 02 03 04'));
        $this->assertTrue($bytes instanceof ByteString && $bytes->bytes === "\x01\x02\x03\x04");

        $map = CborDecoder::decode(self::bytes('a2 01 02 03 04'));
        $this->assertTrue($map instanceof CborMap && $map->get(1) === 2 && $map->get(3) === 4 && $map->count() === 2);
    }

    public function testIntegerAndTextKeysStayApart(): void
    {
        $map = CborDecoder::decode(W::map([[W::int(1), W::text('int')], [W::text('1'), W::text('text')]]));
        assert($map instanceof CborMap);

        $this->assertSame('int', $map->get(1));
        $this->assertSame('text', $map->get('1'));
        $this->assertTrue(!$map->has(2) && $map->get(2) === null);
    }

    public function testRefusesWhatWebAuthnDoesNotUse(): void
    {
        $cases = [
            'indefinite bytes' => '5f 42 01 02 43 03 04 05 ff',
            'indefinite text' => '7f 65 73 74 72 65 61 64 6d 69 6e 67 ff',
            'indefinite array' => '9f 01 82 02 03 9f 04 05 ff ff',
            'indefinite map' => 'bf 61 61 01 61 62 9f 02 03 ff ff',
            'tag' => 'c1 1a 51 4b 67 b0',
            'float16' => 'f9 7c 00',
            'float32' => 'fa 47 c3 50 00',
            'float64' => 'fb 3f f1 99 99 99 99 99 9a',
            'undefined' => 'f7',
            'simple value' => 'f8 20',
            'reserved 28' => '1c',
            'reserved 30' => '5e',
            'beyond PHP_INT_MAX' => '1b 80 00 00 00 00 00 00 00',
            'negative beyond range' => '3b 80 00 00 00 00 00 00 00',
            'truncated argument' => '19 e8',
            'length beyond input' => '45 01 02 03 04',
            'text not UTF-8' => '62 c3 28',
            'empty input' => '',
        ];

        foreach ($cases as $name => $hex) {
            $this->assertRefused(F::MALFORMED, fn () => CborDecoder::decode(self::bytes($hex)), $name);
        }
    }

    public function testRefusesBrokenStructures(): void
    {
        $this->assertRefused(F::MALFORMED, fn () => CborDecoder::decode(W::int(1) . "\x00"), 'trailing byte');
        $this->assertRefused(F::MALFORMED, fn () => CborDecoder::decode(W::map([
            [W::int(1), W::int(2)],
            [W::int(1), W::int(3)],
        ])), 'repeated key');
        $this->assertRefused(F::MALFORMED, fn () => CborDecoder::decode(W::map([[W::array(), W::int(1)]])), 'array key');
        $this->assertRefused(F::MALFORMED, fn () => CborDecoder::decode(W::map([[W::bytes('k'), W::int(1)]])), 'bytes key');
        $this->assertRefused(F::MALFORMED, fn () => CborDecoder::decode(W::head(4, 3) . W::int(1)), 'short array');
        $this->assertRefused(F::MALFORMED, fn () => CborDecoder::decode(W::head(4, 0x7FFFFFFF)), 'huge count');
    }

    public function testDepthAndSizeLimits(): void
    {
        $nested = W::int(0);

        for ($i = 0; $i < CborDecoder::MAX_DEPTH; $i++) {
            $nested = W::array($nested);
        }

        CborDecoder::decode($nested);
        $this->assertRefused(F::MALFORMED, fn () => CborDecoder::decode(W::array($nested)), 'too deep');

        CborDecoder::decode(W::array(...array_fill(0, CborDecoder::MAX_ITEMS, W::int(0))));
        $this->assertRefused(
            F::MALFORMED,
            fn () => CborDecoder::decode(W::array(...array_fill(0, CborDecoder::MAX_ITEMS + 1, W::int(0)))),
            'too many items',
        );
    }

    /**
     * Bytes from hex pairs separated by spaces (as RFC 8949 Appendix A prints them).
     */
    private static function bytes(string $hex): string
    {
        return (string) hex2bin(str_replace(' ', '', $hex));
    }

    public function testDecodeItemMovesTheOffset(): void
    {
        $bytes = W::map([[W::int(1), W::int(2)]]) . 'tail';
        $offset = 0;
        $map = CborDecoder::decodeItem($bytes, $offset);

        $this->assertTrue($map instanceof CborMap);
        $this->assertSame('tail', substr($bytes, $offset));
    }
}
