<?php

namespace Espo\Modules\Itvolga\Hooks\Common;

use Espo\Core\Exceptions\Forbidden;
use Espo\Core\Hook\Hook\BeforeRemove;
use Espo\Core\Hook\Hook\BeforeSave;
use Espo\Core\ORM\Repository\Option\SaveOption;
use Espo\Modules\Itvolga\Tools\FinanceDocument\DocumentProcessor;
use Espo\Modules\Itvolga\Tools\FinanceDocument\DocumentTypes;
use Espo\ORM\Entity;
use Espo\ORM\EntityManager;
use Espo\ORM\Repository\Option\RemoveOptions;
use Espo\ORM\Repository\Option\SaveOptions;

/**
 * Items of finance documents are written only together with their document (DocumentProcessor) or by the importer
 * (SaveOption::IMPORT): a direct write would change a line without recalculating the totals. The API is closed by ACL
 * already (Classes/Acl/FinanceItem); this guard covers internal ORM paths. Removing the items of a deleted document
 * (cascade removal) is allowed.
 *
 * @implements BeforeSave<Entity>
 * @implements BeforeRemove<Entity>
 */
class FinanceItemGuard implements BeforeSave, BeforeRemove
{
    public function __construct(
        private DocumentTypes $types,
        private EntityManager $entityManager,
    ) {}

    public function beforeSave(Entity $entity, SaveOptions $options): void
    {
        if (!$this->types->findByItem($entity->getEntityType()) || $this->isAllowed($options)) {
            return;
        }

        throw new Forbidden('Items of finance documents are changed only through the document.');
    }

    public function beforeRemove(Entity $entity, RemoveOptions $options): void
    {
        $type = $this->types->findByItem($entity->getEntityType());

        if (!$type || $this->isAllowed($options)) {
            return;
        }

        $documentId = $entity->get($type->parentLink . 'Id');

        if (!$documentId || !$this->entityManager->getEntityById($type->entityType, $documentId)) {
            return;
        }

        throw new Forbidden('Items of finance documents are removed only through the document.');
    }

    private function isAllowed(SaveOptions|RemoveOptions $options): bool
    {
        return (bool) $options->get(DocumentProcessor::WRITE_OPTION) || (bool) $options->get(SaveOption::IMPORT);
    }
}
