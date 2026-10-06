<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\SecurityKey;

use Espo\Core\Field\DateTime;
use Espo\Entities\TwoFactorCode;
use Espo\Entities\User;
use Espo\Entities\UserData;
use Espo\Modules\Itvolga\Tools\FinanceDocument\RowLock;
use Espo\Modules\Itvolga\Tools\SecurityKey\Core\Base64Url;
use Espo\Modules\Itvolga\Tools\SecurityKey\Core\VerificationFailed;
use Espo\ORM\EntityManager;
use Espo\ORM\Query\UpdateBuilder;
use Espo\Tools\User\UserDataProvider;

/**
 * One-time WebAuthn challenges in the core `TwoFactorCode` records (D-128): 32 random bytes per user and purpose
 * (sign-in or setup; the method names keep them apart from the core e-mail and SMS codes), a new one deactivating the
 * previous one — under the lock of the user's UserData row, so two first steps at once leave one live challenge. A
 * challenge is consumed before the response is looked at — any attempt, good or bad, burns it — by a
 * conditional update that only one request can win (`isActive = true` in the WHERE, one row affected). The core
 * cleanup job removes old records.
 */
class Challenges
{
    public const LOGIN = 'ItvolgaSecurityKey';
    public const SETUP = 'ItvolgaSecurityKeySetup';

    /** Seconds a challenge is valid: a sign-in follows at once, a setup may register several keys. */
    private const LIFETIME = [
        self::LOGIN => 300,
        self::SETUP => 900,
    ];

    public function __construct(
        private EntityManager $entityManager,
        private UserDataProvider $userDataProvider,
        private RowLock $rowLock,
    ) {}

    /**
     * @param self::LOGIN|self::SETUP $purpose
     * @return string The challenge bytes.
     */
    public function issue(User $user, string $purpose): string
    {
        $challenge = random_bytes(32);
        // The row to lock exists from here on (the core creates it on first use).
        $this->userDataProvider->get($user->getId());

        $this->entityManager->getTransactionManager()->run(function () use ($user, $purpose, $challenge): void {
            $this->rowLock->query(UserData::ENTITY_TYPE)->where(['userId' => $user->getId()])->findOne();

            $this->entityManager->getQueryExecutor()->execute(
                UpdateBuilder::create()
                    ->in(TwoFactorCode::ENTITY_TYPE)
                    ->where(['userId' => $user->getId(), 'method' => $purpose, 'isActive' => true])
                    ->set(['isActive' => false])
                    ->build()
            );

            $this->entityManager->createEntity(TwoFactorCode::ENTITY_TYPE, [
                'code' => Base64Url::encode($challenge),
                'userId' => $user->getId(),
                'method' => $purpose,
                'attemptsLeft' => 1,
            ]);
        });

        return $challenge;
    }

    /**
     * @param self::LOGIN|self::SETUP $purpose
     * @return ?string The challenge bytes; null when there is none, it expired or another request took it.
     */
    public function consume(User $user, string $purpose): ?string
    {
        /** @var ?TwoFactorCode $record */
        $record = $this->entityManager
            ->getRDBRepository(TwoFactorCode::ENTITY_TYPE)
            ->where(['userId' => $user->getId(), 'method' => $purpose, 'isActive' => true])
            ->order('createdAt', 'DESC')
            ->findOne();

        if (!$record) {
            return null;
        }

        $taken = $this->entityManager->getQueryExecutor()->execute(
            UpdateBuilder::create()
                ->in(TwoFactorCode::ENTITY_TYPE)
                ->where(['id' => $record->getId(), 'isActive' => true])
                ->set(['isActive' => false, 'attemptsLeft' => 0])
                ->build()
        );

        if ($taken->rowCount() !== 1) {
            return null;
        }

        $validUntil = $record->getCreatedAt()->modify('+' . self::LIFETIME[$purpose] . ' seconds');

        if ($validUntil->isLessThan(DateTime::createNow())) {
            return null;
        }

        try {
            return Base64Url::decode($record->getCode(), 32);
        } catch (VerificationFailed) {
            return null;
        }
    }
}
