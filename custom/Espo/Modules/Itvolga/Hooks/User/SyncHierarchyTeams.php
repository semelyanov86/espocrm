<?php

namespace Espo\Modules\Itvolga\Hooks\User;

use Espo\Core\Hook\Hook\AfterSave;
use Espo\Entities\User;
use Espo\Modules\Itvolga\Tools\Acl\HierarchyTeams;
use Espo\ORM\Entity;
use Espo\ORM\Repository\Option\SaveOptions;

/**
 * Membership in hierarchy teams follows the user's roles and activity immediately (D-39): a user who loses the
 * superior role, or is deactivated, loses access to the subordinates' records at once.
 *
 * @implements AfterSave<User>
 */
class SyncHierarchyTeams implements AfterSave
{
    public static int $order = 50;

    public function __construct(private HierarchyTeams $tool) {}

    public function afterSave(Entity $entity, SaveOptions $options): void
    {
        if (!in_array($entity->getType(), [User::TYPE_REGULAR, User::TYPE_ADMIN], true)) {
            return;
        }

        if (
            !$entity->isNew() &&
            !$entity->isAttributeChanged('rolesIds') &&
            !$entity->isAttributeChanged('isActive') &&
            !$entity->isAttributeChanged('teamsIds')
        ) {
            return;
        }

        $this->tool->syncUser($entity);
    }
}
