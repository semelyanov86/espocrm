<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Hooks\User;

use Espo\Core\Exceptions\BadRequest;
use Espo\Core\Exceptions\Conflict;
use Espo\Core\Exceptions\Error\Body;
use Espo\Core\Hook\Hook\BeforeSave;
use Espo\Core\ORM\Repository\Option\SaveOption;
use Espo\Entities\User;
use Espo\ORM\Entity;
use Espo\ORM\EntityManager;
use Espo\ORM\Repository\Option\SaveOptions;

/**
 * The extension of a user (cPhoneExtension, D-168) assigns calls, shows call cards and is the phone click-to-call
 * rings: two active users must never share one, and only administrators set it (entityAcl nonAdminReadOnly). The
 * Vtiger import keeps the source value (SaveOption::IMPORT): a duplicate there leaves the extension unassigned at
 * run time instead of failing the import.
 *
 * @implements BeforeSave<User>
 */
class PhoneExtensionGuard implements BeforeSave
{
    public const FIELD = 'cPhoneExtension';

    public static int $order = 40;

    public function __construct(private EntityManager $entityManager) {}

    public function beforeSave(Entity $entity, SaveOptions $options): void
    {
        $value = trim((string) $entity->get(self::FIELD));

        if ($value !== (string) $entity->get(self::FIELD)) {
            $entity->set(self::FIELD, $value === '' ? null : $value);
        }

        if ($options->get(SaveOption::IMPORT) || $value === '' || !$entity->get('isActive')) {
            return;
        }

        if (!$entity->isNew() && !$entity->isAttributeChanged(self::FIELD) && !$entity->isAttributeChanged('isActive')) {
            return;
        }

        if (!preg_match('/^[0-9]{2,10}$/', $value)) {
            throw BadRequest::createWithBody('phoneExtensionInvalid',
                Body::create()->withMessageTranslation('phoneExtensionInvalid', 'User'));
        }

        $taken = $this->entityManager->getRDBRepositoryByClass(User::class)
            ->where([
                self::FIELD => $value,
                'isActive' => true,
                'id!=' => $entity->hasId() ? $entity->getId() : '',
            ])
            ->findOne();

        if ($taken) {
            throw Conflict::createWithBody('phoneExtensionTaken',
                Body::create()->withMessageTranslation('phoneExtensionTaken', 'User'));
        }
    }
}
