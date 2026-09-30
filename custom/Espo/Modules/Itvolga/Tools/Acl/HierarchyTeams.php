<?php

namespace Espo\Modules\Itvolga\Tools\Acl;

use Espo\Core\ORM\Entity as CoreEntity;
use Espo\Core\Utils\Metadata;
use Espo\Entities\Role;
use Espo\Entities\Team;
use Espo\Entities\User;
use Espo\ORM\EntityManager;

/**
 * Hierarchy teams of `app.itvolgaAcl.hierarchyTeams` (decision D-39): the Vtiger role hierarchy and sharing rules
 * reproduced with EspoCRM teams.
 *
 * - Records: a record of a listed entity type assigned to a user holding one of `assignedUserRoles` carries the team,
 *   any other record does not. Only hierarchy teams are managed; group teams and other teams are left as they are.
 * - Members: active users holding one of `memberRoles` are members of the team, nobody else.
 */
class HierarchyTeams
{
    /** @var array<string, string[]> */
    private array $userRoleNames = [];
    /** @var array<string, ?string> */
    private array $teamIds = [];

    public function __construct(
        private Metadata $metadata,
        private EntityManager $entityManager,
    ) {}

    /**
     * @return array<int, array{team: string, memberRoles: string[], assignedUserRoles: string[], entityTypes: string[]}>
     */
    public function getRules(?string $entityType = null): array
    {
        $rules = $this->metadata->get(['app', 'itvolgaAcl', 'hierarchyTeams']) ?? [];

        if ($entityType === null) {
            return $rules;
        }

        return array_values(array_filter($rules, fn ($r) => in_array($entityType, $r['entityTypes'] ?? [], true)));
    }

    public function applyToRecord(CoreEntity $entity): void
    {
        $roleNames = $this->getUserRoleNames($entity->get('assignedUserId'));

        foreach ($this->getRules($entity->getEntityType()) as $rule) {
            $teamId = $this->getTeamId($rule['team']);

            if (!$teamId) {
                continue;
            }

            if (array_intersect($roleNames, $rule['assignedUserRoles'] ?? [])) {
                $entity->addLinkMultipleId('teams', $teamId);

                continue;
            }

            $entity->removeLinkMultipleId('teams', $teamId);
        }
    }

    /**
     * @return string[] Changes made.
     */
    public function syncUser(User $user): array
    {
        $changes = [];
        $roleNames = $user->isActive() ? $this->getRoleNames($user->getLinkMultipleIdList('roles')) : [];
        $this->userRoleNames[$user->getId()] = $roleNames;

        foreach ($this->getRules() as $rule) {
            $team = $this->getTeam($rule['team']);

            if (!$team) {
                continue;
            }

            $relation = $this->entityManager->getRelation($user, 'teams');
            $shouldBeMember = (bool) array_intersect($roleNames, $rule['memberRoles'] ?? []);
            $isMember = $relation->isRelated($team);

            if ($shouldBeMember && !$isMember) {
                $relation->relate($team);
                $changes[] = "member + {$user->getUserName()} → {$rule['team']}";
            }

            if (!$shouldBeMember && $isMember) {
                $relation->unrelate($team);
                $changes[] = "member - {$user->getUserName()} → {$rule['team']}";
            }
        }

        return $changes;
    }

    /**
     * @return string[] Changes made.
     */
    public function syncAllUsers(): array
    {
        $changes = [];
        $users = $this->entityManager->getRDBRepositoryByClass(User::class)
            ->where(['type' => [User::TYPE_REGULAR, User::TYPE_ADMIN]])
            ->find();

        foreach ($users as $user) {
            $changes = array_merge($changes, $this->syncUser($user));
        }

        return $changes;
    }

    /**
     * @param string[] $roleIds
     * @return string[]
     */
    private function getRoleNames(array $roleIds): array
    {
        if (!$roleIds) {
            return [];
        }

        $names = [];

        foreach ($this->entityManager->getRDBRepositoryByClass(Role::class)->where(['id' => $roleIds])->find() as $role) {
            $names[] = (string) $role->get('name');
        }

        return $names;
    }

    /**
     * @return string[]
     */
    private function getUserRoleNames(?string $userId): array
    {
        if (!$userId) {
            return [];
        }

        if (!array_key_exists($userId, $this->userRoleNames)) {
            $user = $this->entityManager->getRDBRepositoryByClass(User::class)->getById($userId);

            $this->userRoleNames[$userId] = $user && $user->isActive() ?
                $this->getRoleNames($user->getLinkMultipleIdList('roles')) : [];
        }

        return $this->userRoleNames[$userId];
    }

    private function getTeam(string $name): ?Team
    {
        return $this->entityManager->getRDBRepositoryByClass(Team::class)->where(['name' => $name])->findOne();
    }

    private function getTeamId(string $name): ?string
    {
        if (!array_key_exists($name, $this->teamIds)) {
            $this->teamIds[$name] = $this->getTeam($name)?->getId();
        }

        return $this->teamIds[$name];
    }
}
