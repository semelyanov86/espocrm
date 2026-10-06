<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Hooks\UserData;

use Espo\Core\Hook\Hook\BeforeSave;
use Espo\Entities\UserData;
use Espo\Modules\Itvolga\Tools\SecurityKey\Credentials;
use Espo\Modules\Itvolga\Tools\SecurityKey\SecurityKeyLogin;
use Espo\ORM\Entity;
use Espo\ORM\Repository\Option\SaveOptions;

/**
 * Drops the user's security keys when a save takes the user off the method (D-128): 2FA turned off by the user or by
 * an administrator (the recovery when all keys are lost), the core Reset, another method. The core calls no method
 * code on these paths. Only a save that changes the 2FA settings counts: the setup writes the new keys in its own save
 * while the stored settings still name the previous method, and the core saves the new method right after.
 *
 * @implements BeforeSave<UserData>
 */
class ClearSecurityKeys implements BeforeSave
{
    public function beforeSave(Entity $entity, SaveOptions $options): void
    {
        if (!$entity->isAttributeChanged('auth2FA') && !$entity->isAttributeChanged('auth2FAMethod')) {
            return;
        }

        if ($entity->get('auth2FA') && $entity->get('auth2FAMethod') === SecurityKeyLogin::NAME) {
            return;
        }

        $entity->set(Credentials::FIELD, null);
    }
}
