<?php

declare(strict_types=1);

namespace Itvolga\Tests\SecurityKey;

use Espo\Modules\Itvolga\Tools\SecurityKey\Core\Cbor\CborDecoder;
use Espo\Modules\Itvolga\Tools\SecurityKey\Core\Cbor\CborMap;
use Espo\Modules\Itvolga\Tools\SecurityKey\Core\PublicKey;
use Espo\Modules\Itvolga\Tools\SecurityKey\Core\VerificationFailed as F;
use Itvolga\Tests\SecurityKey\Support\CborWriter as W;
use Itvolga\Tests\SecurityKey\Support\SoftAuthenticator;

final class PublicKeyTest extends SecurityKeyTestCase
{
    public function testEachAlgorithmVerifiesItsSignatureOnly(): void
    {
        foreach ([SoftAuthenticator::ES256, SoftAuthenticator::EDDSA, SoftAuthenticator::RS256] as $algorithm) {
            $authenticator = SoftAuthenticator::create($algorithm);
            $key = PublicKey::fromCose(self::map($authenticator->coseKey()));
            $assertion = $authenticator->assertion(self::RP_ID, self::ORIGIN, random_bytes(32), 1);
            $signed = $assertion['authenticatorData'] . hash('sha256', $assertion['clientDataJSON'], true);

            $this->assertSame($algorithm, $key->algorithm);
            $this->assertTrue($key->verify($signed, $assertion['signature']), "alg $algorithm valid");
            $this->assertTrue(!$key->verify($signed . 'x', $assertion['signature']), "alg $algorithm other data");
            $this->assertTrue(!$key->verify($signed, ''), "alg $algorithm empty signature");
            $this->assertTrue(!$key->verify($signed, str_repeat("\x30", 64)), "alg $algorithm garbage signature");

            // The stored form gives the same key back.
            $this->assertTrue(PublicKey::fromStored($algorithm, $key->der)->verify($signed, $assertion['signature']));
            $this->assertSame(false, openssl_error_string(), 'OpenSSL error queue drained');
        }
    }

    public function testUnsupportedAlgorithms(): void
    {
        foreach ([-35, -36, -37, -257 - 1, 1] as $algorithm) {
            $this->assertRefused(F::ALGORITHM, fn () => PublicKey::fromCose(self::map(W::map([
                [W::int(1), W::int(2)],
                [W::int(3), W::int($algorithm)],
            ]))), "alg $algorithm");
        }

        $this->assertRefused(F::ALGORITHM, fn () => PublicKey::fromCose(self::map(W::map([[W::int(1), W::int(2)]]))));
        $this->assertRefused(F::ALGORITHM, fn () => PublicKey::fromStored(-35, 'x'));
    }

    public function testEc2KeysMustBeP256PointsOnTheCurve(): void
    {
        $x = random_bytes(32);
        $y = random_bytes(32);
        $ec2 = fn (array $o) => W::map([
            [W::int(1), W::int($o['kty'] ?? 2)],
            [W::int(3), W::int(-7)],
            [W::int(-1), W::int($o['crv'] ?? 1)],
            [W::int(-2), $o['x'] ?? W::bytes($x)],
            [W::int(-3), $o['y'] ?? W::bytes($y)],
        ]);

        // Random coordinates are not a point of P-256 (with overwhelming probability): OpenSSL refuses the import.
        $this->assertRefused(F::KEY, fn () => PublicKey::fromCose(self::map($ec2([]))), 'off the curve');
        $this->assertRefused(F::KEY, fn () => PublicKey::fromCose(self::map($ec2(['kty' => 1]))), 'kty');
        $this->assertRefused(F::KEY, fn () => PublicKey::fromCose(self::map($ec2(['crv' => 2]))), 'P-384');
        $this->assertRefused(F::KEY, fn () => PublicKey::fromCose(self::map($ec2(['x' => W::bytes(substr($x, 1))]))), 'x');
        $this->assertRefused(F::KEY, fn () => PublicKey::fromCose(self::map($ec2(['y' => W::text('y')]))), 'y text');
        $this->assertSame(false, openssl_error_string(), 'OpenSSL error queue drained');
    }

    public function testOkpKeysMustBeEd25519(): void
    {
        $okp = fn (int $crv, string $x) => W::map([
            [W::int(1), W::int(1)],
            [W::int(3), W::int(-8)],
            [W::int(-1), W::int($crv)],
            [W::int(-2), W::bytes($x)],
        ]);

        $this->assertSame(-8, PublicKey::fromCose(self::map($okp(6, random_bytes(32))))->algorithm);
        $this->assertRefused(F::KEY, fn () => PublicKey::fromCose(self::map($okp(7, random_bytes(57)))), 'Ed448');
        $this->assertRefused(F::KEY, fn () => PublicKey::fromCose(self::map($okp(6, random_bytes(31)))), 'short');
        $this->assertRefused(F::KEY, fn () => PublicKey::fromStored(-8, random_bytes(44)), 'stored without prefix');
    }

    public function testRsaKeysMustHaveSaneSizeAndExponent(): void
    {
        $rsa = fn (string $n, string $e) => W::map([
            [W::int(1), W::int(3)],
            [W::int(3), W::int(-257)],
            [W::int(-1), W::bytes($n)],
            [W::int(-2), W::bytes($e)],
        ]);
        $modulus = static fn (int $bits) => "\xc5" . random_bytes(intdiv($bits, 8) - 2) . "\x01";

        $this->assertRefused(F::KEY, fn () => PublicKey::fromCose(self::map($rsa($modulus(1024), "\x01\x00\x01"))), '1024');
        $this->assertRefused(F::KEY, fn () => PublicKey::fromCose(self::map($rsa($modulus(2048) . "\x00", "\x01\x00\x01"))), 'even');
        $this->assertRefused(F::KEY, fn () => PublicKey::fromCose(self::map($rsa($modulus(2048), "\x01\x00\x00"))), 'even e');
        $this->assertRefused(F::KEY, fn () => PublicKey::fromCose(self::map($rsa($modulus(2048), "\x01"))), 'e = 1');
        $this->assertRefused(F::KEY, fn () => PublicKey::fromCose(self::map($rsa("\x00\x00", "\x03"))), 'zero');

        $key = PublicKey::fromCose(self::map($rsa("\x00" . $modulus(2048), "\x01\x00\x01")));
        $this->assertSame(-257, $key->algorithm);
        $this->assertRefused(F::KEY, fn () => PublicKey::fromStored(-7, $key->der), 'RSA stored as ES256');
    }

    private static function map(string $cbor): CborMap
    {
        $map = CborDecoder::decode($cbor);
        assert($map instanceof CborMap);

        return $map;
    }
}
