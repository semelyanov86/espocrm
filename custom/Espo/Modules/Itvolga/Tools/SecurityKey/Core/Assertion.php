<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\SecurityKey\Core;

use JsonException;
use stdClass;

/**
 * The browser's answer to the sign-in challenge as it travels in the `Espo-Authorization-Code` header (the header the
 * core counts failed second-factor attempts by): base64url of a JSON object with the credential id, clientDataJSON,
 * authenticatorData, signature (each base64url) and the user handle (base64url or null). Sizes are bounded below the
 * default Apache header field limit (8190 bytes).
 */
final class Assertion
{
    public const MAX_CODE_LENGTH = 6144;

    private const MEMBERS = ['id', 'clientDataJSON', 'authenticatorData', 'signature', 'userHandle'];

    private function __construct(
        public readonly string $credentialId,
        public readonly string $clientDataJson,
        public readonly string $authenticatorData,
        public readonly string $signature,
        public readonly ?string $userHandle,
    ) {}

    public static function fromCode(string $code): self
    {
        if (strlen($code) > self::MAX_CODE_LENGTH) {
            throw new VerificationFailed(VerificationFailed::TOO_LARGE);
        }

        try {
            $data = json_decode(Base64Url::decode($code, self::MAX_CODE_LENGTH), false, 2, JSON_THROW_ON_ERROR);
        } catch (JsonException) {
            throw new VerificationFailed(VerificationFailed::MALFORMED);
        }

        $members = $data instanceof stdClass ? array_keys(get_object_vars($data)) : [];
        sort($members);
        $expected = self::MEMBERS;
        sort($expected);

        if ($members !== $expected) {
            throw new VerificationFailed(VerificationFailed::MALFORMED);
        }

        return new self(
            credentialId: Base64Url::decode($data->id, AuthenticatorData::MAX_CREDENTIAL_ID_BYTES),
            clientDataJson: Base64Url::decode($data->clientDataJSON, ClientData::MAX_BYTES),
            authenticatorData: Base64Url::decode($data->authenticatorData, AuthenticatorData::MAX_BYTES),
            signature: Base64Url::decode($data->signature, 1024),
            userHandle: $data->userHandle === null ? null : Base64Url::decode($data->userHandle, 64),
        );
    }
}
