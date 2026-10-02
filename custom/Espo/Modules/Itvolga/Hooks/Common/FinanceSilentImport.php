<?php

namespace Espo\Modules\Itvolga\Hooks\Common;

use Espo\Core\Exceptions\Error;
use Espo\Core\Hook\Hook\BeforeRemove;
use Espo\Core\Hook\Hook\BeforeSave;
use Espo\Core\ORM\Repository\Option\SaveOption;
use Espo\Modules\Itvolga\Tools\FinanceDocument\DocumentTypes;
use Espo\ORM\Entity;
use Espo\ORM\Repository\Option\RemoveOptions;
use Espo\ORM\Repository\Option\SaveOptions;

/**
 * The importer writes finance records with SaveOption::IMPORT and SaveOption::SILENT (finance-contract §16.5, D-68):
 * IMPORT alone keeps the source values but not the history quiet — the core stream, audit, assignment notifications
 * and webhooks look at SILENT only, and an import of years of payments and documents would flood them. An import write
 * without SILENT is refused before anything is written.
 *
 * @implements BeforeSave<Entity>
 * @implements BeforeRemove<Entity>
 */
class FinanceSilentImport implements BeforeSave, BeforeRemove
{
    public static int $order = 5;

    public function __construct(private DocumentTypes $types) {}

    public function beforeSave(Entity $entity, SaveOptions $options): void
    {
        $this->check($entity, $options);
    }

    public function beforeRemove(Entity $entity, RemoveOptions $options): void
    {
        $this->check($entity, $options);
    }

    private function check(Entity $entity, SaveOptions|RemoveOptions $options): void
    {
        if (
            $options->get(SaveOption::IMPORT) &&
            !$options->get(SaveOption::SILENT) &&
            $this->types->isFinanceScope($entity->getEntityType())
        ) {
            throw new Error("{$entity->getEntityType()}: an import write must be silent (SaveOption::SILENT).");
        }
    }
}
