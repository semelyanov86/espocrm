<?php

namespace Espo\Modules\Itvolga\Hooks\Common;

use Espo\Core\Hook\Hook\BeforeSave;
use Espo\Core\ORM\Entity as CoreEntity;
use Espo\Modules\Itvolga\Tools\Acl\HierarchyTeams as HierarchyTeamsTool;
use Espo\ORM\Entity;
use Espo\ORM\Repository\Option\SaveOptions;

/**
 * Keeps the hierarchy teams (D-39) of records whose assigned user or teams change, whatever the write path
 * (form, mass update, import). Removing a hierarchy team by editing teams does not stick; linking/unlinking teams
 * through relationship endpoints is closed to non-admins (entityAcl links.teams.nonAdminReadOnly).
 *
 * @implements BeforeSave<Entity>
 */
class HierarchyTeams implements BeforeSave
{
    public static int $order = 20;

    public function __construct(private HierarchyTeamsTool $tool) {}

    public function beforeSave(Entity $entity, SaveOptions $options): void
    {
        if (
            !$entity instanceof CoreEntity ||
            !$entity->hasAttribute('assignedUserId') ||
            !$entity->hasAttribute('teamsIds') ||
            !$this->tool->getRules($entity->getEntityType())
        ) {
            return;
        }

        if (
            !$entity->isNew() &&
            !$entity->isAttributeChanged('assignedUserId') &&
            !$entity->isAttributeChanged('teamsIds')
        ) {
            return;
        }

        $this->tool->applyToRecord($entity);
    }
}
