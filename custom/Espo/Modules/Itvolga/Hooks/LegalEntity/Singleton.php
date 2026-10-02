<?php

namespace Espo\Modules\Itvolga\Hooks\LegalEntity;

use Espo\Core\Exceptions\Forbidden;
use Espo\Core\Hook\Hook\BeforeRemove;
use Espo\Core\Hook\Hook\BeforeSave;
use Espo\Modules\Itvolga\Tools\Finance\LegalEntityResolver;
use Espo\Modules\Itvolga\Tools\FinanceDocument\LegalEntityProvider;
use Espo\ORM\Entity;
use Espo\ORM\EntityManager;
use Espo\ORM\Repository\Option\RemoveOptions;
use Espo\ORM\Repository\Option\SaveOptions;

/**
 * One legal entity (D-04, D-48): a second record is never created, the one record keeps the key `Default` and is not
 * removed (documents and payments refer to it). The setup command creates it; the importer fills the requisites.
 *
 * @implements BeforeSave<Entity>
 * @implements BeforeRemove<Entity>
 */
class Singleton implements BeforeSave, BeforeRemove
{
    public function __construct(private EntityManager $entityManager) {}

    public function beforeSave(Entity $entity, SaveOptions $options): void
    {
        if ($entity->isNew() && $this->entityManager->getRDBRepository(LegalEntityProvider::ENTITY_TYPE)->count() > 0) {
            throw new Forbidden('There is one legal entity (D-04): a second one is not created.');
        }

        if ($entity->get('vtigerCompanyKey') !== LegalEntityResolver::KEY) {
            $entity->set('vtigerCompanyKey', LegalEntityResolver::KEY);
        }
    }

    public function beforeRemove(Entity $entity, RemoveOptions $options): void
    {
        throw new Forbidden('The legal entity is not removed: documents refer to it.');
    }
}
