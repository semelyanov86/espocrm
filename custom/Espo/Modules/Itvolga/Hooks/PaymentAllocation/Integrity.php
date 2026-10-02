<?php

namespace Espo\Modules\Itvolga\Hooks\PaymentAllocation;

use Espo\Core\Hook\Hook\AfterRemove;
use Espo\Core\Hook\Hook\AfterSave;
use Espo\Core\Hook\Hook\BeforeRemove;
use Espo\Core\Hook\Hook\BeforeSave;
use Espo\Core\ORM\Repository\Option\SaveOption;
use Espo\Modules\Itvolga\Tools\FinanceDocument\DocumentTypes;
use Espo\Modules\Itvolga\Tools\FinanceDocument\PaymentType;
use Espo\Modules\Itvolga\Tools\FinancePayment\AllocationWrites;
use Espo\Modules\Itvolga\Tools\FinancePayment\PaymentProcessor;
use Espo\ORM\Entity;
use Espo\ORM\Repository\Option\RemoveOptions;
use Espo\ORM\Repository\Option\SaveOptions;
use WeakMap;

/**
 * Allocation rows written by the importer (SaveOption::IMPORT; Hooks/Common/FinanceItemGuard refuses every other
 * direct write): an imported row is checked and settles its documents, as does a row the importer removes. Rows
 * written or removed by their payment's save, or removed with their payment or document, carry the write option and
 * are handled there (Tools/FinancePayment); a row the core cascade meets again afterwards is already removed.
 *
 * @implements BeforeSave<Entity>
 * @implements AfterSave<Entity>
 * @implements BeforeRemove<Entity>
 * @implements AfterRemove<Entity>
 */
class Integrity implements BeforeSave, AfterSave, BeforeRemove, AfterRemove
{
    public static int $order = 50;

    /** @var WeakMap<Entity, array<string, Entity>> */
    private WeakMap $locked;

    public function __construct(
        private DocumentTypes $types,
        private AllocationWrites $writes,
    ) {
        $this->locked = new WeakMap();
    }

    public function beforeSave(Entity $entity, SaveOptions $options): void
    {
        $type = $this->importType($entity, $options);

        if ($type) {
            $this->locked[$entity] = $this->writes->prepare($entity, $type);
        }
    }

    public function afterSave(Entity $entity, SaveOptions $options): void
    {
        $this->settle($entity);
    }

    public function beforeRemove(Entity $entity, RemoveOptions $options): void
    {
        $type = $this->importType($entity, $options);

        if ($type) {
            $this->locked[$entity] = $this->writes->prepareRemoval($entity, $type);
        }
    }

    public function afterRemove(Entity $entity, RemoveOptions $options): void
    {
        $this->settle($entity);
    }

    private function importType(Entity $entity, SaveOptions|RemoveOptions $options): ?PaymentType
    {
        if ($options->get(PaymentProcessor::WRITE_OPTION) || !$options->get(SaveOption::IMPORT)) {
            return null;
        }

        return $this->types->findPaymentByAllocation($entity->getEntityType());
    }

    private function settle(Entity $entity): void
    {
        $documents = $this->locked[$entity] ?? null;

        if ($documents !== null) {
            unset($this->locked[$entity]);
            $this->writes->settle($documents);
        }
    }
}
