<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Mailing;

use Espo\Entities\EmailAddress;
use Espo\Entities\Team;
use Espo\Entities\User;
use Espo\Modules\Itvolga\Tools\Report\Core\Mailing\MailingSettings;
use Espo\ORM\EntityManager;
use Espo\Repositories\EmailAddress as EmailAddressRepository;

/**
 * Who gets the letters of a mailing (D-122): users and the members of teams — active regular users and administrators
 * with an e-mail address — and the extra addresses, without repeats (regardless of the case). A user of «generate for»
 * must also be the only active user of his address: a saved letter is linked to every user of its address, and a
 * personal slice must not reach another one.
 */
final class Recipients
{
    public function __construct(private readonly EntityManager $entityManager) {}

    /**
     * @return list<string>
     */
    public function addresses(MailingSettings $settings): array
    {
        $users = [];

        foreach ($settings->users as $id) {
            $user = $this->entityManager->getRDBRepositoryByClass(User::class)->getById($id);

            if ($user) {
                $users[] = $user;
            }
        }

        foreach ($settings->teams as $id) {
            $team = $this->entityManager->getRDBRepositoryByClass(Team::class)->getById($id);

            if (!$team) {
                continue;
            }

            foreach ($this->entityManager->getRDBRepositoryByClass(Team::class)->getRelation($team, 'users')
                ->where(['isActive' => true])->find() as $member) {
                assert($member instanceof User);
                $users[] = $member;
            }
        }

        $addresses = [];

        foreach ($users as $user) {
            $address = self::address($user);

            if ($address !== null) {
                $addresses[mb_strtolower($address)] ??= $address;
            }
        }

        foreach ($settings->emails as $email) {
            $addresses[mb_strtolower($email)] ??= $email;
        }

        return array_values($addresses);
    }

    /**
     * The address of a «generate for» user, or why there is none: inactive, noEmail, sharedEmail.
     *
     * @return array{?User, ?string, ?string} user, address, skip reason
     */
    public function personal(string $userId): array
    {
        $user = $this->entityManager->getRDBRepositoryByClass(User::class)->getById($userId);

        if (!$user || !$user->isActive() || !($user->isRegular() || $user->isAdmin())) {
            return [null, null, 'inactive'];
        }

        $address = self::address($user);

        if ($address === null) {
            return [$user, null, 'noEmail'];
        }

        $repository = $this->entityManager->getRepository(EmailAddress::ENTITY_TYPE);
        assert($repository instanceof EmailAddressRepository);
        $record = $repository->getByAddress($address);

        if ($record && count($repository->getEntityListByAddressId($record->getId(), null, User::ENTITY_TYPE,
            true)) > 1) {
            return [$user, null, 'sharedEmail'];
        }

        return [$user, $address, null];
    }

    private static function address(User $user): ?string
    {
        if (!$user->isActive() || !($user->isRegular() || $user->isAdmin())) {
            return null;
        }

        $address = $user->get('emailAddress');

        return is_string($address) && $address !== '' ? $address : null;
    }
}
