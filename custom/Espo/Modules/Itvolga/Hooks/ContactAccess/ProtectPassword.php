<?php

namespace Espo\Modules\Itvolga\Hooks\ContactAccess;

use Espo\Core\Exceptions\BadRequest;
use Espo\Core\Hook\Hook\BeforeSave;
use Espo\Core\Utils\Crypt;
use Espo\Modules\Itvolga\Entities\ContactAccess;
use Espo\ORM\Entity;
use Espo\ORM\Repository\Option\SaveOptions;

/**
 * Encrypts the AnyDesk password on every write path (API, import, formula): whatever plain value is set is
 * replaced with ciphertext (AES-256-CBC, key = `cryptKey` of the installation, outside Git) before it reaches
 * the database. An empty value clears the password.
 *
 * Callers must always set the plain value; an already encrypted value would be encrypted again.
 *
 * @implements BeforeSave<ContactAccess>
 */
class ProtectPassword implements BeforeSave
{
    public static int $order = 1;

    public function __construct(private Crypt $crypt) {}

    /**
     * @throws BadRequest
     */
    public function beforeSave(Entity $entity, SaveOptions $options): void
    {
        if (!$entity->isAttributeChanged(ContactAccess::FIELD_PASSWORD)) {
            if ($entity->isNew()) {
                $entity->set(ContactAccess::FIELD_HAS_PASSWORD, false);
            }

            return;
        }

        $plain = $entity->get(ContactAccess::FIELD_PASSWORD);

        if ($plain === null || $plain === '') {
            $entity->set(ContactAccess::FIELD_PASSWORD, null);
            $entity->set(ContactAccess::FIELD_HAS_PASSWORD, false);

            return;
        }

        if (!is_string($plain) || mb_strlen($plain) > ContactAccess::PASSWORD_MAX_LENGTH) {
            throw new BadRequest("Password is too long.");
        }

        $entity->set(ContactAccess::FIELD_PASSWORD, $this->crypt->encrypt($plain));
        $entity->set(ContactAccess::FIELD_HAS_PASSWORD, true);
    }
}
