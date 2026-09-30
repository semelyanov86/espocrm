<?php

namespace Espo\Modules\Itvolga\Classes\RecordHooks\Call;

use Espo\Core\Exceptions\Forbidden;
use Espo\Core\Record\DeleteParams;
use Espo\Core\Record\Hook\DeleteHook;
use Espo\Core\Record\Hook\UpdateHook;
use Espo\Core\Record\UpdateParams;
use Espo\Entities\User;
use Espo\ORM\Entity;

/**
 * Calls imported from the Vtiger PBXManager history (they carry `cConnectorCallId`) stay read-only for
 * non-admin users: in Vtiger the telephony journal could not be edited or deleted by the working roles,
 * while calendar calls could. Applies to API updates and deletes only; the importer works below the API.
 *
 * @implements UpdateHook<Entity>
 * @implements DeleteHook<Entity>
 */
class ProtectTelephonyHistory implements UpdateHook, DeleteHook
{
    public function __construct(private User $user) {}

    /**
     * @throws Forbidden
     */
    public function process(Entity $entity, UpdateParams|DeleteParams $params): void
    {
        if ($this->user->isAdmin()) {
            return;
        }

        if ($entity->get('cConnectorCallId') !== null && $entity->get('cConnectorCallId') !== '') {
            throw new Forbidden("Telephony history is read-only.");
        }
    }
}
