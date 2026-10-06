<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\SecurityKey\Core;

use JsonException;

/**
 * clientDataJSON (WebAuthn §5.8.1) checked against the ceremony: the type, the challenge (bytes, constant time), the
 * exact origin, not cross-origin and no top origin (the CRM is never embedded). The JSON is parsed, never compared with
 * a template: browsers add members (Chrome: "other_keys_can_be_added_here"). The hash is of the raw bytes.
 */
final class ClientData
{
    public const CREATE = 'webauthn.create';
    public const GET = 'webauthn.get';

    public const MAX_BYTES = 4096;

    private function __construct(public readonly string $hash) {}

    public static function verify(string $json, string $type, string $challenge, string $origin): self
    {
        if (strlen($json) > self::MAX_BYTES) {
            throw new VerificationFailed(VerificationFailed::TOO_LARGE);
        }

        try {
            $data = json_decode($json, false, 4, JSON_THROW_ON_ERROR);
        } catch (JsonException) {
            throw new VerificationFailed(VerificationFailed::MALFORMED);
        }

        if (!$data instanceof \stdClass) {
            throw new VerificationFailed(VerificationFailed::MALFORMED);
        }

        if (($data->type ?? null) !== $type) {
            throw new VerificationFailed(VerificationFailed::TYPE);
        }

        try {
            $received = Base64Url::decode($data->challenge ?? null, 64);
        } catch (VerificationFailed) {
            throw new VerificationFailed(VerificationFailed::CHALLENGE);
        }

        if (!hash_equals($challenge, $received)) {
            throw new VerificationFailed(VerificationFailed::CHALLENGE);
        }

        if (($data->origin ?? null) !== $origin) {
            throw new VerificationFailed(VerificationFailed::ORIGIN);
        }

        if (
            (property_exists($data, 'crossOrigin') && $data->crossOrigin !== false) ||
            property_exists($data, 'topOrigin')
        ) {
            throw new VerificationFailed(VerificationFailed::CROSS_ORIGIN);
        }

        return new self(hash('sha256', $json, true));
    }
}
