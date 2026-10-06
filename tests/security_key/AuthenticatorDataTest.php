<?php

declare(strict_types=1);

namespace Itvolga\Tests\SecurityKey;

use Espo\Modules\Itvolga\Tools\SecurityKey\Core\AuthenticatorData as D;
use Espo\Modules\Itvolga\Tools\SecurityKey\Core\VerificationFailed as F;
use Itvolga\Tests\SecurityKey\Support\CborWriter as W;
use Itvolga\Tests\SecurityKey\Support\SoftAuthenticator;

final class AuthenticatorDataTest extends SecurityKeyTestCase
{
    public function testAssertionDataWithFullCounterRange(): void
    {
        $data = D::parse(self::head(D::UP | D::UV, 0xFFFFFFFF));

        $this->assertSame(hash('sha256', self::RP_ID, true), $data->rpIdHash);
        $this->assertSame(0xFFFFFFFF, $data->signCount);
        $this->assertTrue($data->has(D::UP) && $data->has(D::UV) && !$data->has(D::AT));
        $this->assertSame(null, $data->credentialId);
    }

    public function testAttestedCredentialData(): void
    {
        $authenticator = SoftAuthenticator::create(SoftAuthenticator::ES256);
        $data = D::parse(self::attested($authenticator->credentialId, $authenticator->coseKey()));

        $this->assertSame($authenticator->credentialId, $data->credentialId);
        $this->assertSame(-7, $data->publicKey?->algorithm);
    }

    public function testExtensionsMapAfterTheKey(): void
    {
        $authenticator = SoftAuthenticator::create(SoftAuthenticator::EDDSA);
        $extensions = W::map([[W::text('credProtect'), W::int(1)]]);

        D::parse(self::attested($authenticator->credentialId, $authenticator->coseKey(), D::ED) . $extensions);
        D::parse(self::head(D::UP | D::ED, 1) . $extensions);

        $this->assertRefused(F::MALFORMED, fn () => D::parse(self::head(D::UP | D::ED, 1)), 'ED without map');
        $this->assertRefused(F::MALFORMED, fn () => D::parse(self::head(D::UP | D::ED, 1) . W::int(1)), 'ED not a map');
        $this->assertRefused(F::MALFORMED, fn () => D::parse(self::head(D::UP, 1) . $extensions), 'map without ED');
    }

    public function testRefusesBrokenLengths(): void
    {
        $authenticator = SoftAuthenticator::create(SoftAuthenticator::ES256);
        $key = $authenticator->coseKey();

        $this->assertRefused(F::MALFORMED, fn () => D::parse(substr(self::head(D::UP, 1), 0, 36)), 'short');
        $this->assertRefused(F::MALFORMED, fn () => D::parse(self::head(D::UP, 1) . "\x00"), 'trailing');
        $this->assertRefused(F::MALFORMED, fn () => D::parse(self::attested('', $key)), 'empty id');
        $this->assertRefused(F::MALFORMED, fn () => D::parse(self::attested(random_bytes(1024), $key)), 'id 1024');
        $this->assertRefused(F::MALFORMED, fn () => D::parse(self::attested('id', $key) . "\x00"), 'trailing key');
        $this->assertRefused(F::MALFORMED, fn () => D::parse(self::attested('id', substr($key, 0, -3))), 'cut key');
        $this->assertRefused(F::MALFORMED, fn () => D::parse(self::attested('id', W::array())), 'key not a map');
        $this->assertRefused(F::MALFORMED, fn () => D::parse(self::head(D::UP | D::AT, 1) . str_repeat("\x00", 17)), 'AT cut');
        $this->assertRefused(
            F::MALFORMED,
            fn () => D::parse(self::head(D::UP | D::AT, 1) . str_repeat("\x00", 16) . pack('n', 40) . 'short'),
            'id beyond input',
        );
        $this->assertRefused(F::TOO_LARGE, fn () => D::parse(self::head(D::UP, 1) . str_repeat("\x00", D::MAX_BYTES)));
    }

    public function testBackupStateNeedsBackupEligibility(): void
    {
        D::parse(self::head(D::UP | D::BE | D::BS, 1));
        $this->assertRefused(F::FLAGS, fn () => D::parse(self::head(D::UP | D::BS, 1)));
    }

    private static function head(int $flags, int $signCount): string
    {
        return hash('sha256', self::RP_ID, true) . chr($flags) . pack('N', $signCount);
    }

    private static function attested(string $credentialId, string $coseKey, int $flags = 0): string
    {
        return self::head(D::UP | D::AT | $flags, 0) . str_repeat("\x00", 16) .
            pack('n', strlen($credentialId)) . $credentialId . $coseKey;
    }
}
