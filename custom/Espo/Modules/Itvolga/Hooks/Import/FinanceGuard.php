<?php

namespace Espo\Modules\Itvolga\Hooks\Import;

use Espo\Core\Exceptions\Forbidden;
use Espo\Core\Hook\Hook\BeforeSave;
use Espo\Modules\Itvolga\Tools\FinanceDocument\DocumentTypes;
use Espo\ORM\Entity;
use Espo\ORM\Repository\Option\SaveOptions;

/**
 * The core CSV import is closed to finance records (stage 04.4, owner decision 2026-10-02): it checks only the import
 * and create rights, ignores `scopes.importable` and saves rows with SaveOption::IMPORT — the path of the Vtiger
 * importer, which keeps totals and numbers as given. Finance documents, items, payments and allocations are imported
 * only by the migration importer (stage 06.3).
 *
 * @implements BeforeSave<Entity>
 */
class FinanceGuard implements BeforeSave
{
    public function __construct(private DocumentTypes $types) {}

    public function beforeSave(Entity $entity, SaveOptions $options): void
    {
        if ($entity->isNew() && $this->types->isFinanceScope((string) $entity->get('entityType'))) {
            throw new Forbidden('Finance records are not imported from CSV.');
        }
    }
}
