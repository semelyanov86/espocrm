<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\SecurityKey;

use Espo\Core\Field\DateTime;
use Espo\Core\Utils\Log;
use Espo\Entities\User;
use Espo\Entities\UserData;
use Espo\Modules\Itvolga\Tools\FinanceDocument\RowLock;
use Espo\Modules\Itvolga\Tools\SecurityKey\Core\Credential;
use Espo\Modules\Itvolga\Tools\SecurityKey\Core\VerificationFailed;
use Espo\Modules\Itvolga\Tools\SecurityKey\Core\Verifier;
use Espo\ORM\EntityManager;
use Espo\Tools\User\UserDataProvider;
use RuntimeException;
use stdClass;

/**
 * The user's security keys: a JSON list in `UserData.cSecurityKeys` (D-128), next to the core's TOTP secret. The
 * record has no API of its own; the list is written only by a verified setup (the whole set is replaced) and by a
 * successful sign-in (the counter and the last use, under the row lock); the UserData hook empties it when the user
 * leaves the method.
 */
class Credentials
{
    public const FIELD = 'cSecurityKeys';
    public const MAX_KEYS = 5;

    public function __construct(
        private EntityManager $entityManager,
        private UserDataProvider $userDataProvider,
        private RowLock $rowLock,
        private Log $log,
    ) {}

    public function isMethodEnabled(User $user): bool
    {
        $userData = $this->find($user);

        return $userData !== null &&
            $userData->getAuth2FA() &&
            $userData->getAuth2FAMethod() === SecurityKeyLogin::NAME;
    }

    /**
     * @return list<Credential> Unreadable entries are left out (and logged).
     */
    public function list(User $user): array
    {
        return $this->parse($this->find($user)?->get(self::FIELD), $user);
    }

    public function get(User $user, string $credentialId): ?Credential
    {
        foreach ($this->list($user) as $credential) {
            if (hash_equals($credential->id, $credentialId)) {
                return $credential;
            }
        }

        return null;
    }

    /**
     * @param list<Credential> $credentials
     */
    public function replace(User $user, array $credentials): void
    {
        $userData = $this->userDataProvider->get($user->getId()) ?? throw new RuntimeException('No user data.');

        $userData->set(self::FIELD, self::toStored($credentials));
        $this->entityManager->saveEntity($userData);
    }

    /**
     * Stores the counter of a successful sign-in, checking it again against the value committed now: of two
     * requests signed with the same counter only one passes.
     */
    public function recordUse(User $user, string $credentialId, int $signCount): bool
    {
        return $this->entityManager->getTransactionManager()->run(function () use ($user, $credentialId, $signCount) {
            $userData = $this->rowLock->query(UserData::ENTITY_TYPE)->where(['userId' => $user->getId()])->findOne();
            $credentials = $this->parse($userData?->get(self::FIELD), $user);

            foreach ($credentials as $i => $credential) {
                if (!hash_equals($credential->id, $credentialId)) {
                    continue;
                }

                try {
                    Verifier::checkCounter($credential->signCount, $signCount);
                } catch (VerificationFailed) {
                    $this->log->warning("Security key: sign-in of user {$user->getId()} refused (counter, concurrent).");

                    return false;
                }

                assert($userData !== null);
                $credentials[$i] = $credential->withUse($signCount, DateTime::createNow()->toString());
                $userData->set(self::FIELD, self::toStored($credentials));
                $this->entityManager->saveEntity($userData);

                return true;
            }

            return false;
        });
    }

    private function find(User $user): ?UserData
    {
        /** @var ?UserData */
        return $this->entityManager
            ->getRDBRepository(UserData::ENTITY_TYPE)
            ->where(['userId' => $user->getId()])
            ->findOne();
    }

    /**
     * @return list<Credential>
     */
    private function parse(mixed $stored, User $user): array
    {
        $credentials = [];

        foreach (is_array($stored) ? $stored : [] as $i => $item) {
            try {
                $credentials[] = Credential::fromArray($item instanceof stdClass ? (array) $item : []);
            } catch (VerificationFailed $e) {
                $this->log->error("Security key: stored key $i of user {$user->getId()} is unreadable ({$e->reason}).");
            }
        }

        return $credentials;
    }

    /**
     * @param list<Credential> $credentials
     * @return list<stdClass>
     */
    private static function toStored(array $credentials): array
    {
        return array_map(static fn (Credential $credential) => (object) $credential->toArray(), $credentials);
    }
}
