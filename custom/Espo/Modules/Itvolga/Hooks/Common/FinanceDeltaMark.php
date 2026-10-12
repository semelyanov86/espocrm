<?php

namespace Espo\Modules\Itvolga\Hooks\Common;

use Espo\Core\Hook\Hook\BeforeRemove;
use Espo\Modules\Itvolga\Tools\FinanceDocument\DocumentTypes;
use Espo\Modules\Itvolga\Tools\Import\FinanceRules;
use Espo\ORM\Entity;
use Espo\ORM\Repository\Option\RemoveOptions;
use stdClass;

/**
 * Who deleted a finance record (stage 06.4, D-158): the import's delta marks the records it removes because they left
 * the source (`vtigerData.deletedInSource`, removal option OPTION) — such a record comes back when the source has it
 * again; any other removal (a user, a cascade of the finance hooks) clears a mark left from an earlier delta removal
 * that was restored meanwhile, so a record deleted in EspoCRM is never brought back (D-148). The attribute is written
 * by the core mapper's update together with `deleted = 1`.
 *
 * @implements BeforeRemove<Entity>
 */
class FinanceDeltaMark implements BeforeRemove
{
    public const OPTION = 'itvolgaDeltaRemoval';
    public static int $order = 6;

    public function __construct(private DocumentTypes $types) {}

    public function beforeRemove(Entity $entity, RemoveOptions $options): void
    {
        if (!$this->types->isFinanceScope($entity->getEntityType()) || !$entity->hasAttribute('vtigerData')) {
            return;
        }

        $data = $entity->get('vtigerData');
        $data = $data instanceof stdClass ? clone $data : new stdClass();
        $key = FinanceRules::DELETED_IN_SOURCE;

        if ($options->get(self::OPTION)) {
            $data->$key = true;
        } elseif (property_exists($data, $key)) {
            unset($data->$key);
        } else {
            return;
        }

        $entity->set('vtigerData', $data);
    }
}
