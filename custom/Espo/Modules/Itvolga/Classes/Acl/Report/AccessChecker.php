<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Classes\Acl\Report;

use Espo\Core\Acl\AccessEntityCREDSChecker;
use Espo\Core\Acl\DefaultAccessChecker;
use Espo\Core\Acl\ScopeData;
use Espo\Core\Acl\Traits\DefaultAccessCheckerDependency;
use Espo\Core\ORM\Entity as CoreEntity;
use Espo\Entities\User;
use Espo\Modules\Itvolga\Entities\Report;
use Espo\Modules\Itvolga\Tools\Report\Core\Access\SharingPolicy;
use Espo\ORM\Entity;

/**
 * Record access to reports (D-87): reading by the access type and the lists of users and teams (SharingPolicy, the
 * same rule as the select filters), editing and deleting by the owner only. Administrators never reach this class.
 *
 * @implements AccessEntityCREDSChecker<Report>
 */
class AccessChecker implements AccessEntityCREDSChecker
{
    use DefaultAccessCheckerDependency;

    public function __construct(DefaultAccessChecker $defaultAccessChecker)
    {
        $this->defaultAccessChecker = $defaultAccessChecker;
    }

    public function checkEntityRead(User $user, Entity $entity, ScopeData $data): bool
    {
        assert($entity instanceof CoreEntity);

        if ($user->isAdmin()) {
            return true;
        }

        $isShared = $entity->get('accessType') === Report::ACCESS_SHARED;

        return SharingPolicy::canRead(
            (string) $data->getRead(),
            (string) $entity->get('accessType'),
            $this->isOwner($user, $entity),
            $isShared && $entity->hasLinkMultipleId('sharedUsers', $user->getId()),
            $isShared && array_intersect($entity->getLinkMultipleIdList('sharedTeams'), $user->getTeamIdList()) !== [],
        );
    }

    public function checkEntityEdit(User $user, Entity $entity, ScopeData $data): bool
    {
        return $user->isAdmin() || SharingPolicy::canEdit((string) $data->getEdit(), $this->isOwner($user, $entity));
    }

    public function checkEntityDelete(User $user, Entity $entity, ScopeData $data): bool
    {
        return $user->isAdmin() || SharingPolicy::canEdit((string) $data->getDelete(), $this->isOwner($user, $entity));
    }

    public function checkEntityStream(User $user, Entity $entity, ScopeData $data): bool
    {
        return false;
    }

    private function isOwner(User $user, Entity $entity): bool
    {
        $ownerId = $entity->isNew() ? null : $entity->getFetched('assignedUserId');

        return ($ownerId ?? $entity->get('assignedUserId')) === $user->getId();
    }
}
