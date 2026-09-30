<?php

namespace Espo\Modules\Itvolga\Hooks\ContactAccess;

use Espo\Core\Hook\Hook\BeforeSave;
use Espo\Modules\Crm\Entities\Contact;
use Espo\Modules\Itvolga\Entities\ContactAccess;
use Espo\ORM\Entity;
use Espo\ORM\EntityManager;
use Espo\ORM\Repository\Option\SaveOptions;

/**
 * Gives a record without a name the neutral name «Доступ: <contact>». The name never contains the
 * credentials themselves: it is shown wherever the record is referenced.
 *
 * @implements BeforeSave<ContactAccess>
 */
class DefaultName implements BeforeSave
{
    public function __construct(private EntityManager $entityManager) {}

    public function beforeSave(Entity $entity, SaveOptions $options): void
    {
        if ($entity->get('name')) {
            return;
        }

        $contactName = null;
        $contactId = $entity->getContactId();

        if ($contactId) {
            $contact = $this->entityManager->getEntityById(Contact::ENTITY_TYPE, $contactId);
            $contactName = $contact?->get('name');
        }

        $entity->set('name', mb_substr('Доступ: ' . ($contactName ?: '—'), 0, 100));
    }
}
