<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\SecurityKey\Core;

use Espo\Modules\Itvolga\Tools\SecurityKey\Core\Cbor\ByteString;
use Espo\Modules\Itvolga\Tools\SecurityKey\Core\Cbor\CborDecoder;
use Espo\Modules\Itvolga\Tools\SecurityKey\Core\Cbor\CborMap;

/**
 * The two WebAuthn ceremonies of the second factor (WebAuthn L2 §7.1 and §7.2) under the owner's policy: any FIDO2
 * authenticator (attestation "none": the attestation statement is not checked and proves nothing), user presence
 * required (a touch), user verification not required (the password is the first factor). The challenge is the one the
 * server issued for this ceremony and has already been consumed by the caller; the result is all or nothing.
 */
final class Verifier
{
    public const MAX_ATTESTATION_BYTES = 16384;

    public function __construct(private RelyingParty $relyingParty) {}

    public function verifyRegistration(string $clientDataJson, string $attestationObject, string $challenge): RegisteredKey
    {
        ClientData::verify($clientDataJson, ClientData::CREATE, $challenge, $this->relyingParty->origin);

        if (strlen($attestationObject) > self::MAX_ATTESTATION_BYTES) {
            throw new VerificationFailed(VerificationFailed::TOO_LARGE);
        }

        $object = CborDecoder::decode($attestationObject);

        if (!$object instanceof CborMap) {
            throw new VerificationFailed(VerificationFailed::MALFORMED);
        }

        $format = $object->get('fmt');
        $statement = $object->get('attStmt');
        $authenticatorData = $object->get('authData');

        if (
            !is_string($format) || $format === '' || strlen($format) > 32 ||
            !$statement instanceof CborMap ||
            !$authenticatorData instanceof ByteString ||
            ($format === 'none' && $statement->count() !== 0)
        ) {
            throw new VerificationFailed(VerificationFailed::MALFORMED);
        }

        $data = AuthenticatorData::parse($authenticatorData->bytes);
        $this->checkRelyingPartyAndPresence($data);

        if ($data->credentialId === null || $data->publicKey === null) {
            throw new VerificationFailed(VerificationFailed::FLAGS);
        }

        return new RegisteredKey($data->credentialId, $data->publicKey, $data->signCount);
    }

    /**
     * @param string $userHandle The handle given to the authenticator at registration (the user id).
     * @return int The new signature counter to store.
     */
    public function verifyAssertion(
        Assertion $assertion,
        string $challenge,
        Credential $credential,
        string $userHandle,
    ): int {

        if (!hash_equals($credential->id, $assertion->credentialId)) {
            throw new VerificationFailed(VerificationFailed::CREDENTIAL);
        }

        if ($assertion->userHandle !== null && !hash_equals($userHandle, $assertion->userHandle)) {
            throw new VerificationFailed(VerificationFailed::USER_HANDLE);
        }

        $clientData = ClientData::verify(
            $assertion->clientDataJson,
            ClientData::GET,
            $challenge,
            $this->relyingParty->origin,
        );

        $data = AuthenticatorData::parse($assertion->authenticatorData);

        if ($data->has(AuthenticatorData::AT)) {
            throw new VerificationFailed(VerificationFailed::FLAGS);
        }

        $this->checkRelyingPartyAndPresence($data);

        if (!$credential->publicKey->verify($assertion->authenticatorData . $clientData->hash, $assertion->signature)) {
            throw new VerificationFailed(VerificationFailed::SIGNATURE);
        }

        self::checkCounter($credential->signCount, $data->signCount);

        return $data->signCount;
    }

    /**
     * WebAuthn §7.2 step 22: when either counter is not zero the received one must be above the stored one; otherwise
     * the key may have been cloned. Authenticators without a counter always send zero.
     */
    public static function checkCounter(int $stored, int $received): void
    {
        if (($stored !== 0 || $received !== 0) && $received <= $stored) {
            throw new VerificationFailed(VerificationFailed::COUNTER);
        }
    }

    private function checkRelyingPartyAndPresence(AuthenticatorData $data): void
    {
        if (!hash_equals($this->relyingParty->idHash(), $data->rpIdHash)) {
            throw new VerificationFailed(VerificationFailed::RP_ID);
        }

        if (!$data->has(AuthenticatorData::UP)) {
            throw new VerificationFailed(VerificationFailed::USER_PRESENCE);
        }
    }
}
