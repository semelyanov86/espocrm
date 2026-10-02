<?php

namespace Espo\Modules\Itvolga\Hooks\Payment;

use Espo\Core\Hook\Hook\AfterRemove;
use Espo\Core\Hook\Hook\AfterSave;
use Espo\Core\Hook\Hook\BeforeRemove;
use Espo\Core\Hook\Hook\BeforeSave;
use Espo\Modules\Itvolga\Tools\FinanceDocument\DocumentTypes;
use Espo\Modules\Itvolga\Tools\FinancePayment\PaymentPlan;
use Espo\Modules\Itvolga\Tools\FinancePayment\PaymentProcessor;
use Espo\ORM\Entity;
use Espo\ORM\Repository\Option\RemoveOptions;
use Espo\ORM\Repository\Option\SaveOptions;
use WeakMap;

/**
 * Payments (stage 04.4) on every write path (API, mass update, console, import): the allocation table, the number,
 * the legal entity and the settlement of the documents, in the payment's transaction (entityDefs transactionalSave).
 * beforeSave decides and locks, afterSave writes the rows; a removal locks before the core removes the rows and
 * settles the documents after. Order 50, like the finance documents.
 *
 * @implements BeforeSave<Entity>
 * @implements AfterSave<Entity>
 * @implements BeforeRemove<Entity>
 * @implements AfterRemove<Entity>
 */
class Allocations implements BeforeSave, AfterSave, BeforeRemove, AfterRemove
{
    public static int $order = 50;

    /** @var WeakMap<Entity, PaymentPlan> */
    private WeakMap $plans;
    /** @var WeakMap<Entity, array<string, Entity>> */
    private WeakMap $removals;

    public function __construct(
        private DocumentTypes $types,
        private PaymentProcessor $processor,
    ) {
        $this->plans = new WeakMap();
        $this->removals = new WeakMap();
    }

    public function beforeSave(Entity $entity, SaveOptions $options): void
    {
        $type = $this->types->findPayment($entity->getEntityType());

        if (!$type) {
            return;
        }

        $plan = $this->processor->prepare($entity, $type, $options);

        if ($plan) {
            $this->plans[$entity] = $plan;
        }
    }

    public function afterSave(Entity $entity, SaveOptions $options): void
    {
        $plan = $this->plans[$entity] ?? null;
        $type = $this->types->findPayment($entity->getEntityType());

        if (!$plan || !$type) {
            return;
        }

        unset($this->plans[$entity]);
        $this->processor->persist($entity, $type, $plan);
    }

    public function beforeRemove(Entity $entity, RemoveOptions $options): void
    {
        $type = $this->types->findPayment($entity->getEntityType());

        if ($type) {
            $this->removals[$entity] = $this->processor->prepareRemoval($entity, $type);
        }
    }

    public function afterRemove(Entity $entity, RemoveOptions $options): void
    {
        $documents = $this->removals[$entity] ?? null;

        if ($documents === null) {
            return;
        }

        unset($this->removals[$entity]);
        $this->processor->completeRemoval($documents, $options);
    }
}
