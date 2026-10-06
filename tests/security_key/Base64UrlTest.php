<?php

declare(strict_types=1);

namespace Itvolga\Tests\SecurityKey;

use Espo\Modules\Itvolga\Tools\SecurityKey\Core\Base64Url;
use Espo\Modules\Itvolga\Tools\SecurityKey\Core\VerificationFailed as F;

final class Base64UrlTest extends SecurityKeyTestCase
{
    public function testRoundTripWithoutPadding(): void
    {
        foreach (['', 'a', 'ab', 'abc', "\xff\xfe\xfd\x00", random_bytes(32)] as $bytes) {
            $text = Base64Url::encode($bytes);
            $this->assertTrue(!str_contains($text, '=') && !str_contains($text, '+') && !str_contains($text, '/'));
            $this->assertSame($bytes, Base64Url::decode($text, 64));
        }

        $this->assertSame('_-8', Base64Url::encode("\xff\xef"));
    }

    public function testRefusesOtherAlphabetsPaddingAndImpossibleLengths(): void
    {
        foreach (['YQ==', 'a+b/', 'YW Jj', 'Y', "YWJj\n", 'ä'] as $text) {
            $this->assertRefused(F::MALFORMED, fn () => Base64Url::decode($text, 64), $text);
        }

        $this->assertRefused(F::MALFORMED, fn () => Base64Url::decode(null, 64));
        $this->assertRefused(F::MALFORMED, fn () => Base64Url::decode(123, 64));
    }

    public function testRefusesNonCanonicalTrailingBits(): void
    {
        // "YWI" is the canonical form of "ab"; PHP's decoder would also accept "YWJ".
        $this->assertSame('ab', Base64Url::decode('YWI', 8));
        $this->assertRefused(F::MALFORMED, fn () => Base64Url::decode('YWJ', 8));
    }

    public function testLimitIsCheckedBeforeDecoding(): void
    {
        $this->assertSame(32, strlen(Base64Url::decode(Base64Url::encode(random_bytes(32)), 32)));
        $this->assertRefused(F::TOO_LARGE, fn () => Base64Url::decode(Base64Url::encode(random_bytes(33)), 32));
    }
}
