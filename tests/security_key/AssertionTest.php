<?php

declare(strict_types=1);

namespace Itvolga\Tests\SecurityKey;

use Espo\Modules\Itvolga\Tools\SecurityKey\Core\Assertion;
use Espo\Modules\Itvolga\Tools\SecurityKey\Core\Base64Url;
use Espo\Modules\Itvolga\Tools\SecurityKey\Core\Credential;
use Espo\Modules\Itvolga\Tools\SecurityKey\Core\RelyingParty;
use Espo\Modules\Itvolga\Tools\SecurityKey\Core\Verifier;
use Espo\Modules\Itvolga\Tools\SecurityKey\Core\VerificationFailed as F;
use Itvolga\Tests\SecurityKey\Support\SoftAuthenticator as A;

final class AssertionTest extends SecurityKeyTestCase
{
    private const USER_HANDLE = 'user-id-1';

    private Verifier $verifier;
    private string $challenge;

    public function setUp(): void
    {
        $this->verifier = new Verifier(RelyingParty::fromSiteUrl(self::ORIGIN, null, 'CRM'));
        $this->challenge = random_bytes(32);
    }

    public function testEachAlgorithmSignsIn(): void
    {
        foreach ([A::ES256, A::EDDSA, A::RS256] as $algorithm) {
            [$authenticator, $credential] = $this->registered($algorithm);

            $this->assertSame(1, $this->signIn($authenticator, $credential, 1), "alg $algorithm");
        }
    }

    public function testThroughTheHeaderCode(): void
    {
        [$authenticator, $credential] = $this->registered(A::ES256);
        $code = A::code($authenticator->assertion(self::RP_ID, self::ORIGIN, $this->challenge, 5, [
            'userHandle' => self::USER_HANDLE,
        ]));

        $this->assertSame(5, $this->verifier->verifyAssertion(
            Assertion::fromCode($code),
            $this->challenge,
            $credential,
            self::USER_HANDLE,
        ));
    }

    public function testSignatureCoversAuthenticatorAndClientData(): void
    {
        [$a, $credential] = $this->registered(A::ES256);

        $this->assertRefused(F::SIGNATURE, fn () => $this->signIn($a, $credential, 1, ['tamper' => true]));

        $assertion = $a->assertion(self::RP_ID, self::ORIGIN, $this->challenge, 1);
        // Another valid client data (other member order) under the signature of the original one.
        $assertion['clientDataJSON'] = (string) json_encode(array_reverse(json_decode($assertion['clientDataJSON'], true)), JSON_UNESCAPED_SLASHES);
        $this->assertRefused(F::SIGNATURE, fn () => $this->check($assertion, $credential), 'client data swapped');

        $assertion = $a->assertion(self::RP_ID, self::ORIGIN, $this->challenge, 1);
        $assertion['authenticatorData'][32] = chr(0x05);
        $this->assertRefused(F::SIGNATURE, fn () => $this->check($assertion, $credential), 'flags changed');

        // The stored id with another stored public key: the signature is not of that key.
        [, $other] = $this->registered(A::RS256);
        $this->assertRefused(F::SIGNATURE, fn () => $this->signIn($a, new Credential(
            $credential->id, $other->publicKey, 0, null, [], '2026-10-06 00:00:00', null,
        ), 1), 'other key');
    }

    public function testCeremonyChecks(): void
    {
        [$a, $c] = $this->registered(A::ES256);

        $this->assertRefused(F::CREDENTIAL, fn () => $this->signIn($a, $c, 1, ['credentialId' => random_bytes(48)]));
        $this->assertRefused(F::USER_HANDLE, fn () => $this->signIn($a, $c, 1, ['userHandle' => 'other-user']));
        $this->assertRefused(F::TYPE, fn () => $this->signIn($a, $c, 1, ['type' => 'webauthn.create']));
        $this->assertRefused(F::CHALLENGE, fn () => $this->signIn($a, $c, 1, ['challenge' => random_bytes(32)]));
        $this->assertRefused(F::ORIGIN, fn () => $this->signIn($a, $c, 1, ['origin' => 'https://crm.example.test:8443']));
        $this->assertRefused(F::CROSS_ORIGIN, fn () => $this->signIn($a, $c, 1, ['topOrigin' => 'https://evil.test']));
        $this->assertRefused(F::RP_ID, fn () => $this->signIn($a, $c, 1, ['rpId' => 'example.test']));
        $this->assertRefused(F::USER_PRESENCE, fn () => $this->signIn($a, $c, 1, ['flags' => 0x04]));
        $this->assertRefused(F::FLAGS, fn () => $this->signIn($a, $c, 1, [
            'flags' => 0x41,
            'trailing' => $a->attestedCredentialData(),
        ]), 'attested data');
        $this->assertRefused(F::MALFORMED, fn () => $this->signIn($a, $c, 1, ['flags' => 0x41]), 'AT without data');
        $this->assertRefused(F::MALFORMED, fn () => $this->signIn($a, $c, 1, ['trailing' => "\x00"]));

        // No user handle (keys that are not discoverable) is fine; user verification is not required.
        $this->assertSame(2, $this->signIn($a, $c, 2, ['userHandle' => null, 'flags' => 0x01]));
    }

    public function testSignatureCounter(): void
    {
        $cases = [
            // stored, received, accepted
            [0, 0, true],
            [0, 7, true],
            [7, 8, true],
            [7, 0xFFFFFFFF, true],
            [7, 7, false],
            [7, 6, false],
            [7, 0, false],
        ];

        foreach ($cases as [$stored, $received, $accepted]) {
            [$a, $credential] = $this->registered(A::ES256, $stored);
            $sign = fn () => $this->signIn($a, $credential, $received);

            if ($accepted) {
                $this->assertSame($received, $sign(), "$stored -> $received");
            } else {
                $this->assertRefused(F::COUNTER, $sign, "$stored -> $received");
            }
        }
    }

    public function testHeaderCodeShape(): void
    {
        [$a] = $this->registered(A::ES256);
        $parts = $a->assertion(self::RP_ID, self::ORIGIN, $this->challenge, 1);
        $members = json_decode((string) Base64Url::decode(A::code($parts), 8192), true);
        $code = static fn (mixed $data) => Base64Url::encode((string) json_encode($data));

        Assertion::fromCode($code(array_reverse($members)));

        $this->assertRefused(F::MALFORMED, fn () => Assertion::fromCode('not base64url!'));
        $this->assertRefused(F::MALFORMED, fn () => Assertion::fromCode(Base64Url::encode('{"id":')));
        $this->assertRefused(F::MALFORMED, fn () => Assertion::fromCode($code([1, 2, 3])));
        $this->assertRefused(F::MALFORMED, fn () => Assertion::fromCode($code(['type' => 'public-key'] + $members)));
        $this->assertRefused(F::MALFORMED, fn () => Assertion::fromCode($code(array_diff_key($members, ['userHandle' => 1]))));
        $this->assertRefused(F::MALFORMED, fn () => Assertion::fromCode($code(['signature' => 12] + $members)));
        $this->assertRefused(F::MALFORMED, fn () => Assertion::fromCode($code(['id' => ['nested']] + $members)));
        $this->assertRefused(F::TOO_LARGE, fn () => Assertion::fromCode(str_repeat('A', Assertion::MAX_CODE_LENGTH + 1)));
    }

    /**
     * @return array{A, Credential}
     */
    private function registered(int $algorithm, int $signCount = 0): array
    {
        $authenticator = A::create($algorithm);
        $response = $authenticator->attestation(self::RP_ID, self::ORIGIN, $this->challenge);
        $key = $this->verifier->verifyRegistration(
            $response['clientDataJSON'],
            $response['attestationObject'],
            $this->challenge,
        );

        return [
            $authenticator,
            new Credential($key->credentialId, $key->publicKey, $signCount, 'Ключ', ['usb'], '2026-10-06 00:00:00', null),
        ];
    }

    /**
     * @param array<string, mixed> $o
     */
    private function signIn(A $authenticator, Credential $credential, int $signCount, array $o = []): int
    {
        $o += ['userHandle' => self::USER_HANDLE];

        return $this->check($authenticator->assertion(self::RP_ID, self::ORIGIN, $this->challenge, $signCount, $o), $credential);
    }

    /**
     * @param array{id: string, clientDataJSON: string, authenticatorData: string, signature: string, userHandle: ?string} $assertion
     */
    private function check(array $assertion, Credential $credential): int
    {
        return $this->verifier->verifyAssertion(
            Assertion::fromCode(A::code($assertion)),
            $this->challenge,
            $credential,
            self::USER_HANDLE,
        );
    }
}
