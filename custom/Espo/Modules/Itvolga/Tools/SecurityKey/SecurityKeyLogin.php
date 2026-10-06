<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\SecurityKey;

use Espo\Core\Api\Request;
use Espo\Core\Authentication\HeaderKey;
use Espo\Core\Authentication\Result;
use Espo\Core\Authentication\Result\Data as ResultData;
use Espo\Core\Authentication\Result\FailReason;
use Espo\Core\Authentication\TwoFactor\Exceptions\NotConfigured;
use Espo\Core\Authentication\TwoFactor\Login;
use Espo\Core\Utils\Log;
use Espo\Entities\User;
use Espo\Modules\Itvolga\Tools\SecurityKey\Core\Assertion;
use Espo\Modules\Itvolga\Tools\SecurityKey\Core\Base64Url;
use Espo\Modules\Itvolga\Tools\SecurityKey\Core\Credential;
use Espo\Modules\Itvolga\Tools\SecurityKey\Core\RelyingParty;
use Espo\Modules\Itvolga\Tools\SecurityKey\Core\VerificationFailed;
use Espo\Modules\Itvolga\Tools\SecurityKey\Core\Verifier;
use RuntimeException;

/**
 * The second login step with a security key (WebAuthn, D-128). The core calls it after the password is checked, on
 * both requests: without a code it issues a challenge and asks the browser for the module's security-key step; with
 * the code — the browser's signed answer in `Espo-Authorization-Code`, so the core's failed-code limit applies — it
 * consumes the challenge and verifies the answer. A user who has the method but no readable key gets a step that only
 * explains how to recover (the administrator turns 2FA off); the second factor is never skipped.
 */
class SecurityKeyLogin implements Login
{
    public const NAME = 'ItvolgaSecurityKey';
    public const VIEW = 'itvolga:views/login-security-key';
    /** Milliseconds the browser waits for the touch. */
    public const TIMEOUT = 120000;

    public function __construct(
        private Credentials $credentials,
        private Challenges $challenges,
        private RelyingPartyProvider $relyingPartyProvider,
        private Log $log,
    ) {}

    public function login(Result $result, Request $request): Result
    {
        $user = $result->getUser() ?? throw new RuntimeException('No user.');
        $code = $request->getHeader(HeaderKey::AUTHORIZATION_CODE);

        try {
            $relyingParty = $this->relyingPartyProvider->get();
        } catch (NotConfigured $e) {
            $this->log->error($e->getMessage());

            return Result::fail(FailReason::ERROR);
        }

        if ($code === null || $code === '') {
            return $this->begin($user, $relyingParty);
        }

        return $this->verify($user, $code, $relyingParty) ? $result : Result::fail(FailReason::CODE_NOT_VERIFIED);
    }

    private function begin(User $user, RelyingParty $relyingParty): Result
    {
        $credentials = $this->credentials->list($user);

        if ($credentials === []) {
            $this->log->warning("Security key: user {$user->getId()} has the method but no keys.");

            return Result::secondStepRequired($user, ResultData::createWithMessage('itvolgaSecurityKeyNone')
                ->withView(self::VIEW)
                ->withDataItem('state', 'noKeys'));
        }

        $challenge = $this->challenges->issue($user, Challenges::LOGIN);

        return Result::secondStepRequired($user, ResultData::createWithMessage('itvolgaSecurityKeyTouch')
            ->withView(self::VIEW)
            ->withDataItem('state', 'ready')
            ->withDataItem('publicKey', [
                'challenge' => Base64Url::encode($challenge),
                'rpId' => $relyingParty->id,
                'timeout' => self::TIMEOUT,
                'userVerification' => 'discouraged',
                'allowCredentials' => array_map(static fn (Credential $credential) => [
                    'type' => 'public-key',
                    'id' => Base64Url::encode($credential->id),
                    'transports' => $credential->transports,
                ], $credentials),
            ]));
    }

    private function verify(User $user, string $code, RelyingParty $relyingParty): bool
    {
        // Consumed first: a refused answer cannot be retried against the same challenge.
        $challenge = $this->challenges->consume($user, Challenges::LOGIN);

        if ($challenge === null) {
            $this->log->info("Security key: sign-in of user {$user->getId()} without a live challenge.");

            return false;
        }

        if (!$this->credentials->isMethodEnabled($user)) {
            return false;
        }

        try {
            $assertion = Assertion::fromCode($code);
            $credential = $this->credentials->get($user, $assertion->credentialId) ??
                throw new VerificationFailed(VerificationFailed::CREDENTIAL);
            $signCount = (new Verifier($relyingParty))
                ->verifyAssertion($assertion, $challenge, $credential, $user->getId());
        } catch (VerificationFailed $e) {
            $message = "Security key: sign-in of user {$user->getId()} refused ({$e->reason}).";

            if ($e->reason === VerificationFailed::COUNTER) {
                // A counter that did not grow may mean a cloned key.
                $this->log->warning($message);
            } else {
                $this->log->notice($message);
            }

            return false;
        }

        return $this->credentials->recordUse($user, $credential->id, $signCount);
    }
}
