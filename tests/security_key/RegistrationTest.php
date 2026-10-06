<?php

declare(strict_types=1);

namespace Itvolga\Tests\SecurityKey;

use Espo\Modules\Itvolga\Tools\SecurityKey\Core\RelyingParty;
use Espo\Modules\Itvolga\Tools\SecurityKey\Core\Verifier;
use Espo\Modules\Itvolga\Tools\SecurityKey\Core\VerificationFailed as F;
use Itvolga\Tests\SecurityKey\Support\CborWriter as W;
use Itvolga\Tests\SecurityKey\Support\SoftAuthenticator as A;

final class RegistrationTest extends SecurityKeyTestCase
{
    private Verifier $verifier;
    private string $challenge;

    public function setUp(): void
    {
        $this->verifier = new Verifier(RelyingParty::fromSiteUrl(self::ORIGIN, null, 'CRM'));
        $this->challenge = random_bytes(32);
    }

    public function testEachAlgorithmRegisters(): void
    {
        foreach ([A::ES256, A::EDDSA, A::RS256] as $algorithm) {
            $authenticator = A::create($algorithm);
            $key = $this->register($authenticator);

            $this->assertSame($authenticator->credentialId, $key->credentialId);
            $this->assertSame($algorithm, $key->publicKey->algorithm);
            $this->assertSame(0, $key->signCount);
        }

        $this->assertSame(7, $this->register(A::create(A::ES256), ['signCount' => 7])->signCount);
    }

    public function testUserVerificationIsNotRequiredButPresenceIs(): void
    {
        $this->register(A::create(A::ES256), ['flags' => 0x45]);
        $this->assertRefused(F::USER_PRESENCE, fn () => $this->register(A::create(A::ES256), ['flags' => 0x44]));
        $this->assertRefused(F::USER_PRESENCE, fn () => $this->register(A::create(A::ES256), ['flags' => 0x40]));
    }

    public function testCeremonyChecks(): void
    {
        $a = A::create(A::ES256);

        $this->assertRefused(F::TYPE, fn () => $this->register($a, ['type' => 'webauthn.get']));
        $this->assertRefused(F::CHALLENGE, fn () => $this->register($a, ['challenge' => random_bytes(32)]));
        $this->assertRefused(F::ORIGIN, fn () => $this->register($a, ['origin' => 'https://evil.example.test']));
        $this->assertRefused(F::CROSS_ORIGIN, fn () => $this->register($a, ['crossOrigin' => true]));
        $this->assertRefused(F::RP_ID, fn () => $this->register($a, ['rpId' => 'evil.example.test']));
        $this->assertRefused(F::FLAGS, fn () => $this->register($a, ['flags' => 0x01, 'attested' => false]), 'no AT');
        $this->assertRefused(F::MALFORMED, fn () => $this->register($a, ['flags' => 0x01]), 'attested data without AT');
    }

    public function testAttestationObjectShape(): void
    {
        $a = A::create(A::ES256);

        // Formats other than "none" are accepted without checking their statement (policy: any FIDO2 key).
        $this->register($a, ['fmt' => 'packed', 'attStmt' => W::map([[W::text('alg'), W::int(-7)]])]);

        $this->assertRefused(F::MALFORMED, fn () => $this->register($a, ['attStmt' => W::map([[W::text('x'), W::int(1)]])]));
        $this->assertRefused(F::MALFORMED, fn () => $this->register($a, ['attStmt' => W::array()]));
        $this->assertRefused(F::MALFORMED, fn () => $this->register($a, ['fmt' => '']));
        $this->assertRefused(F::MALFORMED, fn () => $this->register($a, ['trailing' => "\x00"]));
        $this->assertRefused(F::ALGORITHM, fn () => $this->register($a, ['coseKey' => W::map([
            [W::int(1), W::int(2)],
            [W::int(3), W::int(-35)],
        ])]));

        $response = $a->attestation(self::RP_ID, self::ORIGIN, $this->challenge);
        $verify = fn (string $object) => $this->verifier->verifyRegistration($response['clientDataJSON'], $object, $this->challenge);

        $this->assertRefused(F::MALFORMED, fn () => $verify(W::array()), 'not a map');
        $this->assertRefused(F::MALFORMED, fn () => $verify($response['attestationObject'] . "\x00"), 'trailing');
        $this->assertRefused(F::MALFORMED, fn () => $verify(W::map([
            [W::text('fmt'), W::text('none')],
            [W::text('attStmt'), W::map([])],
            [W::text('authData'), W::text('not bytes')],
        ])), 'authData as text');
        $this->assertRefused(F::TOO_LARGE, fn () => $verify(str_repeat("\x00", Verifier::MAX_ATTESTATION_BYTES + 1)));
    }

    /**
     * @param array<string, mixed> $o
     */
    private function register(A $authenticator, array $o = []): \Espo\Modules\Itvolga\Tools\SecurityKey\Core\RegisteredKey
    {
        $response = $authenticator->attestation(self::RP_ID, self::ORIGIN, $this->challenge, $o);

        return $this->verifier->verifyRegistration(
            $response['clientDataJSON'],
            $response['attestationObject'],
            $this->challenge,
        );
    }
}
