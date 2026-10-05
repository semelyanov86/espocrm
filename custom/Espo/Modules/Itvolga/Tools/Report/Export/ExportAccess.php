<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Export;

use Espo\Core\Acl\Permission;
use Espo\Core\Acl\Table;
use Espo\Core\AclManager;
use Espo\Core\Exceptions\Error\Body;
use Espo\Core\Exceptions\Forbidden;
use Espo\Core\Utils\Config;
use Espo\Entities\User;

/**
 * Whether a user may take a report result out of the CRM — export files, the print view, a background export, a
 * mailing of his report (D-116, D-126): the role permission «Экспорт» (exportPermission = yes) and the global switch
 * `exportDisabled` for non-administrators, as the core export checks them (Tools/Export/Service). Checked for the
 * given user, so a job checks the requester or the owner as they are now.
 */
final class ExportAccess
{
    public function __construct(
        private readonly Config $config,
        private readonly AclManager $aclManager,
    ) {}

    public function canExport(User $user): bool
    {
        if (!$user->isActive()) {
            return false;
        }

        if ($this->config->get('exportDisabled') && !$user->isAdmin()) {
            return false;
        }

        return $this->aclManager->getPermissionLevel($user, Permission::EXPORT) === Table::LEVEL_YES;
    }

    /**
     * @throws Forbidden
     */
    public function assert(User $user): void
    {
        if (!$this->canExport($user)) {
            throw Forbidden::createWithBody('exportForbidden',
                Body::create()->withMessageTranslation('exportForbidden', 'Report'));
        }
    }
}
