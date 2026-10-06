<?php

declare(strict_types=1);

namespace Itvolga\Tests\SecurityKey;

use Espo\Modules\Itvolga\Tools\SecurityKey\Core\Base64Url;
use Espo\Modules\Itvolga\Tools\SecurityKey\Core\ClientData;
use Espo\Modules\Itvolga\Tools\SecurityKey\Core\VerificationFailed as F;

final class ClientDataTest extends SecurityKeyTestCase
{
    private string $challenge;

    public function setUp(): void
    {
        $this->challenge = random_bytes(32);
    }

    public function testAcceptsTheCeremonyAndHashesTheRawBytes(): void
    {
        // Members in another order, extra members and escaped slashes: parsed, not compared with a template.
        $json = '{"origin":"https:\/\/crm.example.test","extra":{"a":1},"type":"webauthn.get","challenge":"' .
            Base64Url::encode($this->challenge) . '"}';

        $this->assertSame(hash('sha256', $json, true), $this->verify($json)->hash);
        $this->verify($this->json(['crossOrigin' => false]));
    }

    public function testType(): void
    {
        $this->assertRefused(F::TYPE, fn () => $this->verify($this->json(['type' => 'webauthn.create'])));
        $this->assertRefused(F::TYPE, fn () => $this->verify($this->json(['type' => null])));
    }

    public function testChallenge(): void
    {
        $other = $this->challenge;
        $other[0] = chr(ord($other[0]) ^ 1);

        $this->assertRefused(F::CHALLENGE, fn () => $this->verify($this->json(['challenge' => Base64Url::encode($other)])));
        $this->assertRefused(F::CHALLENGE, fn () => $this->verify($this->json([
            'challenge' => Base64Url::encode(substr($this->challenge, 0, 31)),
        ])));
        $this->assertRefused(F::CHALLENGE, fn () => $this->verify($this->json([
            'challenge' => base64_encode($this->challenge),
        ])), 'standard base64 with padding');
        $this->assertRefused(F::CHALLENGE, fn () => $this->verify($this->json(['challenge' => 5])));
    }

    public function testOriginIsExact(): void
    {
        foreach ([
            'http://crm.example.test',
            'https://crm.example.test/',
            'https://crm.example.test:443',
            'https://CRM.example.test',
            'https://evil.crm.example.test',
            'https://crm.example.test.evil',
            null,
        ] as $origin) {
            $this->assertRefused(F::ORIGIN, fn () => $this->verify($this->json(['origin' => $origin])), (string) $origin);
        }
    }

    public function testCrossOriginAndTopOrigin(): void
    {
        $this->assertRefused(F::CROSS_ORIGIN, fn () => $this->verify($this->json(['crossOrigin' => true])));
        $this->assertRefused(F::CROSS_ORIGIN, fn () => $this->verify($this->json(['crossOrigin' => 'false'])));
        $this->assertRefused(F::CROSS_ORIGIN, fn () => $this->verify($this->json(['topOrigin' => self::ORIGIN])));
    }

    public function testMalformedAndOversized(): void
    {
        foreach (['', 'null', '[]', '"x"', '{"type":', '{"type":"webauthn.get"} x'] as $json) {
            $this->assertRefused(F::MALFORMED, fn () => $this->verify($json), $json);
        }

        $this->assertRefused(F::MALFORMED, fn () => $this->verify($this->json(['deep' => [[[[1]]]]])), 'too deep');
        $this->assertRefused(F::TOO_LARGE, fn () => $this->verify($this->json(['pad' => str_repeat('a', 4096)])));
    }

    private function verify(string $json): ClientData
    {
        return ClientData::verify($json, ClientData::GET, $this->challenge, self::ORIGIN);
    }

    /**
     * @param array<string, mixed> $override
     */
    private function json(array $override = []): string
    {
        return (string) json_encode(array_merge([
            'type' => ClientData::GET,
            'challenge' => Base64Url::encode($this->challenge),
            'origin' => self::ORIGIN,
        ], $override));
    }
}
