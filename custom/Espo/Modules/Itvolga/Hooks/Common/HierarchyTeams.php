<?php

namespace Espo\Modules\Itvolga\Hooks\Common;

use Espo\Core\Hook\Hook\BeforeSave;
use Espo\Core\ORM\Entity as CoreEntity;
use Espo\Core\Utils\Metadata;
use Espo\Entities\Team;
use Espo\Entities\User;
use Espo\ORM\Entity;
use Espo\ORM\EntityManager;
use Espo\ORM\Repository\Option\SaveOptions;

/**
 * Keeps the hierarchy teams of `app.itvolgaAcl.hierarchyTeams` on records whose assigned user changes:
 * a record assigned to a user of one of `assignedUserRoles` gets the team, otherwise the team is removed.
 * Only hierarchy teams are touched; group teams and any other teams stay as they are.
 *
 * @implements BeforeSave<Entity>
 */
class HierarchyTeams implements BeforeSave
{
    public static int $order = 20;

    /** @var array<string, string[]> */
    private array $userRoleNames = [];
    /** @var array<string, ?string> */
    private array $teamIds = [];

    public function __construct(
        private Metadata $metadata,
        private EntityManager $entityManager,
    ) {}

    public function beforeSave(Entity $entity, SaveOptions $options): void
    {
        if (!$entity instanceof CoreEntity) {
            return;
        }

        $rules = array_filter(
            $this->metadata->get(['app', 'itvolgaAcl', 'hierarchyTeams']) ?? [],
            fn ($rule) => in_array($entity->getEntityType(), $rule['entityTypes'] ?? [], true)
        );

        if (!$rules || !$entity->hasAttribute('assignedUserId') || !$entity->hasAttribute('teamsIds')) {
            return;
        }

        if (!$entity->isNew() && !$entity->isAttributeChanged('assignedUserId')) {
            return;
        }

        $roleNames = $this->getUserRoleNames($entity->get('assignedUserId'));

        foreach ($rules as $rule) {
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
     * @return string[]
     */
    private function getUserRoleNames(?string $userId): array
    {
        if (!$userId) {
            return [];
        }

        if (!array_key_exists($userId, $this->userRoleNames)) {
            $user = $this->entityManager->getRDBRepositoryByClass(User::class)->getById($userId);
            $names = [];

            if ($user) {
                foreach ($this->entityManager->getRelation($user, 'roles')->find() as $role) {
                    $names[] = (string) $role->get('name');
                }
            }

            $this->userRoleNames[$userId] = $names;
        }

        return $this->userRoleNames[$userId];
    }

    private function getTeamId(string $name): ?string
    {
        if (!array_key_exists($name, $this->teamIds)) {
            $team = $this->entityManager->getRDBRepositoryByClass(Team::class)->where(['name' => $name])->findOne();

            $this->teamIds[$name] = $team?->getId();
        }

        return $this->teamIds[$name];
    }
}
