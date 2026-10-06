<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\SecurityKey;

use Espo\Core\Authentication\TwoFactor\Exceptions\NotConfigured;
use Espo\Core\Authentication\TwoFactor\UserSetup;
use Espo\Core\Exceptions\BadRequest;
use Espo\Core\Field\DateTime;
use Espo\Core\Utils\Log;
use Espo\Entities\User;
use Espo\Modules\Itvolga\Tools\SecurityKey\Core\AuthenticatorData;
use Espo\Modules\Itvolga\Tools\SecurityKey\Core\Base64Url;
use Espo\Modules\Itvolga\Tools\SecurityKey\Core\ClientData;
use Espo\Modules\Itvolga\Tools\SecurityKey\Core\Credential;
use Espo\Modules\Itvolga\Tools\SecurityKey\Core\PublicKey;
use Espo\Modules\Itvolga\Tools\SecurityKey\Core\VerificationFailed;
use Espo\Modules\Itvolga\Tools\SecurityKey\Core\Verifier;
use stdClass;

/**
 * Setting up the security-key method through the core UserSecurity path (D-128): `getData` gives the browser the
 * creation options with a setup challenge; the user registers one to MAX_KEYS keys with it (primary and backup) and
 * the security modal saves them in one request, where `verifyData` consumes the challenge, verifies every key and
 * replaces the user's whole set. Adding a key later is the core Reset (its save turns 2FA off, and the UserData hook
 * drops the old keys) and registering the set again.
 */
class SecurityKeyUserSetup implements UserSetup
{
    /** The model attribute the setup modal sends the registered keys in. */
    public const KEYS = 'itvolgaSecurityKeys';

    public function __construct(
        private Credentials $credentials,
        private Challenges $challenges,
        private RelyingPartyProvider $relyingPartyProvider,
        private Log $log,
    ) {}

    public function getData(User $user): stdClass
    {
        $relyingParty = $this->relyingPartyProvider->get();
        $challenge = $this->challenges->issue($user, Challenges::SETUP);
        $userName = (string) $user->getUserName();

        return (object) [
            'publicKey' => [
                'rp' => ['id' => $relyingParty->id, 'name' => $relyingParty->name],
                // The user handle is the internal user id: stable, no personal data.
                'user' => [
                    'id' => Base64Url::encode($user->getId()),
                    'name' => $userName,
                    'displayName' => (string) ($user->get('name') ?: $userName),
                ],
                'challenge' => Base64Url::encode($challenge),
                'pubKeyCredParams' => array_map(
                    static fn (int $algorithm) => ['type' => 'public-key', 'alg' => $algorithm],
                    PublicKey::supportedAlgorithms(),
                ),
                'timeout' => SecurityKeyLogin::TIMEOUT,
                'attestation' => 'none',
                'authenticatorSelection' => [
                    'residentKey' => 'discouraged',
                    'requireResidentKey' => false,
                    'userVerification' => 'discouraged',
                ],
                'excludeCredentials' => [],
            ],
            'maxKeys' => Credentials::MAX_KEYS,
        ];
    }

    /**
     * @throws BadRequest Not a list of 1 to MAX_KEYS registrations.
     */
    public function verifyData(User $user, stdClass $payloadData): bool
    {
        $items = $payloadData->{self::KEYS} ?? null;

        if (!is_array($items) || $items === [] || count($items) > Credentials::MAX_KEYS) {
            throw new BadRequest('Security key: 1-' . Credentials::MAX_KEYS . ' keys expected.');
        }

        try {
            $relyingParty = $this->relyingPartyProvider->get();
        } catch (NotConfigured $e) {
            $this->log->error($e->getMessage());

            return false;
        }

        $challenge = $this->challenges->consume($user, Challenges::SETUP);

        if ($challenge === null) {
            $this->log->info("Security key: setup of user {$user->getId()} without a live challenge.");

            return false;
        }

        $verifier = new Verifier($relyingParty);
        $now = DateTime::createNow()->toString();
        $credentials = [];

        try {
            foreach ($items as $item) {
                if (!$item instanceof stdClass) {
                    throw new VerificationFailed(VerificationFailed::MALFORMED);
                }

                $key = $verifier->verifyRegistration(
                    Base64Url::decode($item->clientDataJSON ?? null, ClientData::MAX_BYTES),
                    Base64Url::decode($item->attestationObject ?? null, Verifier::MAX_ATTESTATION_BYTES),
                    $challenge,
                );
                $id = Base64Url::decode($item->id ?? null, AuthenticatorData::MAX_CREDENTIAL_ID_BYTES);

                // The id the browser reported is the one in the authenticator data, and each key comes once.
                if (!hash_equals($key->credentialId, $id) || isset($credentials[$id])) {
                    throw new VerificationFailed(VerificationFailed::CREDENTIAL);
                }

                $credentials[$id] = new Credential(
                    id: $id,
                    publicKey: $key->publicKey,
                    signCount: $key->signCount,
                    name: Credential::normalizeName($item->name ?? null),
                    transports: Credential::normalizeTransports($item->transports ?? []),
                    createdAt: $now,
                    lastUsedAt: null,
                );
            }
        } catch (VerificationFailed $e) {
            $this->log->notice("Security key: setup of user {$user->getId()} refused ({$e->reason}).");

            return false;
        }

        $this->credentials->replace($user, array_values($credentials));

        return true;
    }
}
