<?php

namespace Espo\Modules\Itvolga\Hooks\Common;

use Espo\Core\Exceptions\Error\Body;
use Espo\Core\Exceptions\Forbidden;
use Espo\Core\Hook\Hook\BeforeSave;
use Espo\Core\ORM\Repository\Option\SaveOption;
use Espo\Modules\Itvolga\Tools\FinanceDocument\DocumentTypes;
use Espo\Modules\Itvolga\Tools\FinanceDocument\NumberAllocator;
use Espo\ORM\Entity;
use Espo\ORM\Repository\Option\SaveOptions;

/**
 * The number of a stored finance document or payment never changes (D-17; owner decision 2026-10-03, stage 04.6): a
 * new record gets it from the counter (NumberAllocator), an imported one keeps the Vtiger number — only the importer
 * (SaveOption::IMPORT) writes a number to a stored record, as in the source, empty and repeated ones included. The API
 * drops the field already (read-only); this guard covers every other write path — console, formula, hooks, internal
 * saves, the system user too. Order 45: after formula (11), before the finance processors (50), so a refused save
 * takes no lock and no number.
 *
 * @implements BeforeSave<Entity>
 */
class FinanceNumberGuard implements BeforeSave
{
    public const LABEL = 'financeNumberReadOnly';

    public static int $order = 45;

    public function __construct(private DocumentTypes $types) {}

    public function beforeSave(Entity $entity, SaveOptions $options): void
    {
        if (
            $entity->isNew() ||
            $options->get(SaveOption::IMPORT) ||
            !$entity->isAttributeChanged(NumberAllocator::FIELD) ||
            !$this->types->seriesOf($entity->getEntityType())
        ) {
            return;
        }

        throw Forbidden::createWithBody(self::LABEL, Body::create()->withMessageTranslation(self::LABEL, 'Global'));
    }
}
