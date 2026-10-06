<?php

declare(strict_types=1);

namespace Itvolga\Tests\SecurityKey;

use Espo\Modules\Itvolga\Tools\SecurityKey\Core\Credential;
use Espo\Modules\Itvolga\Tools\SecurityKey\Core\Cbor\CborDecoder;
use Espo\Modules\Itvolga\Tools\SecurityKey\Core\Cbor\CborMap;
use Espo\Modules\Itvolga\Tools\SecurityKey\Core\PublicKey;
use Espo\Modules\Itvolga\Tools\SecurityKey\Core\VerificationFailed as F;
use Itvolga\Tests\SecurityKey\Support\SoftAuthenticator as A;

final class CredentialTest extends SecurityKeyTestCase
{
    public function testStoredFormRoundTrip(): void
    {
        foreach ([A::ES256, A::EDDSA, A::RS256] as $algorithm) {
            $credential = $this->credential($algorithm, 0xFFFFFFFF);
            // Through JSON, as stored in the database.
            $row = json_decode((string) json_encode($credential->toArray()), true);
            $back = Credential::fromArray($row);

            $this->assertSame($credential->toArray(), $back->toArray(), "alg $algorithm");
        }
    }

    public function testWithUseKeepsTheRest(): void
    {
        $used = $this->credential(A::ES256, 3)->withUse(4, '2026-10-06 12:00:00');

        $this->assertSame(4, $used->signCount);
        $this->assertSame('2026-10-06 12:00:00', $used->lastUsedAt);
        $this->assertSame('Основной', $used->name);
    }

    public function testCorruptRowsAreRefused(): void
    {
        $row = $this->credential(A::ES256, 1)->toArray();

        foreach ([
            'id' => [F::MALFORMED, ['id' => 'not base64url!']],
            'algorithm as text' => [F::MALFORMED, ['algorithm' => '-7']],
            'negative counter' => [F::MALFORMED, ['signCount' => -1]],
            'counter over 32 bits' => [F::MALFORMED, ['signCount' => 0xFFFFFFFF + 1]],
            'createdAt' => [F::MALFORMED, ['createdAt' => null]],
            'lastUsedAt' => [F::MALFORMED, ['lastUsedAt' => 5]],
            'name' => [F::MALFORMED, ['name' => ['x']]],
            'key of another algorithm' => [F::KEY, ['algorithm' => -8]],
            'RSA algorithm, EC key' => [F::KEY, ['algorithm' => -257]],
            'unsupported algorithm' => [F::ALGORITHM, ['algorithm' => -35]],
        ] as $case => [$reason, $change]) {
            $this->assertRefused($reason, fn () => Credential::fromArray(array_merge($row, $change)), $case);
        }
    }

    public function testNamesAndTransportsAreNormalized(): void
    {
        $this->assertSame(null, Credential::normalizeName(null));
        $this->assertSame(null, Credential::normalizeName("  \t "));
        $this->assertSame('Запасной ключ', Credential::normalizeName(" Запасной\u{200B} ключ\x07 "));
        $this->assertSame(100, mb_strlen((string) Credential::normalizeName(str_repeat('я', 100))));
        $this->assertRefused(F::MALFORMED, fn () => Credential::normalizeName(str_repeat('я', 101)));
        $this->assertRefused(F::MALFORMED, fn () => Credential::normalizeName(5));
        $this->assertRefused(F::MALFORMED, fn () => Credential::normalizeName("\xff"));

        $this->assertSame(['usb', 'nfc'], Credential::normalizeTransports(['nfc', 'usb', 'usb', 'radio', 7, ['x']]));
        $this->assertSame([], Credential::normalizeTransports('usb'));
    }

    private function credential(int $algorithm, int $signCount): Credential
    {
        $authenticator = A::create($algorithm);
        $cose = CborDecoder::decode($authenticator->coseKey());
        assert($cose instanceof CborMap);

        return new Credential(
            $authenticator->credentialId,
            PublicKey::fromCose($cose),
            $signCount,
            'Основной',
            ['usb', 'nfc'],
            '2026-10-06 00:00:00',
            null,
        );
    }
}
