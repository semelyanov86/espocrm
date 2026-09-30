<?php

namespace Espo\Modules\Itvolga\Classes\Acl\Call;

use Espo\Core\Acl\ScopeData;
use Espo\Entities\User;
use Espo\Modules\Crm\Classes\Acl\Call\AccessChecker as CallAccessChecker;
use Espo\ORM\Entity;

/**
 * Calls imported from the Vtiger PBXManager history (they carry `cConnectorCallId`) are read-only for non-admin users:
 * in Vtiger the telephony journal could not be edited or deleted by the working roles, while calendar calls could.
 * Implemented as ACL, so single and mass update/delete, inline edit and the UI buttons all follow it; the importer
 * works as the system user.
 */
class AccessChecker extends CallAccessChecker
{
    public function checkEntityEdit(User $user, Entity $entity, ScopeData $data): bool
    {
        if (!$user->isAdmin() && self::isTelephonyHistory($entity)) {
            return false;
        }

        return parent::checkEntityEdit($user, $entity, $data);
    }

    public function checkEntityDelete(User $user, Entity $entity, ScopeData $data): bool
    {
        if (!$user->isAdmin() && self::isTelephonyHistory($entity)) {
            return false;
        }

        return parent::checkEntityDelete($user, $entity, $data);
    }

    private static function isTelephonyHistory(Entity $entity): bool
    {
        $id = $entity->get('cConnectorCallId');

        return $id !== null && $id !== '';
    }
}
