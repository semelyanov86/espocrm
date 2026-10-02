<?php

namespace Espo\Modules\Itvolga\Hooks\Common;

use Espo\Core\Hook\Hook\AfterSave;
use Espo\Core\Hook\Hook\BeforeRemove;
use Espo\Core\Hook\Hook\BeforeSave;
use Espo\Modules\Itvolga\Tools\FinanceDocument\DocumentProcessor;
use Espo\Modules\Itvolga\Tools\FinanceDocument\DocumentTypes;
use Espo\Modules\Itvolga\Tools\FinanceDocument\SavePlan;
use Espo\Modules\Itvolga\Tools\FinancePayment\AllocationWrites;
use Espo\Modules\Itvolga\Tools\FinancePayment\SettlementUpdater;
use Espo\Core\ORM\Repository\Option\SaveOption;
use Espo\ORM\Entity;
use Espo\ORM\Repository\Option\RemoveOptions;
use Espo\ORM\Repository\Option\SaveOptions;
use WeakMap;

/**
 * Finance documents of the registry (app.itvolgaFinance): totals, number and items on every write path (API, mass
 * update, console). beforeSave computes everything that can fail before the row is written; afterSave writes the
 * items; both run in the document's transaction (entityDefs transactionalSave). Order 50: after formula (11) and the
 * hierarchy teams (20), before the core currency default (200). A settlement write (SettlementUpdater, a payment
 * changed) is not a document edit and passes through. Removing a document that payments can be allocated to removes
 * its allocations first, under the payment ledger (the lock order of Tools/FinancePayment/PaymentProcessor), and
 * records them in the payments' history.
 *
 * @implements BeforeSave<Entity>
 * @implements AfterSave<Entity>
 * @implements BeforeRemove<Entity>
 */
class FinanceDocument implements BeforeSave, AfterSave, BeforeRemove
{
    public static int $order = 50;

    /** @var WeakMap<Entity, SavePlan> */
    private WeakMap $plans;

    public function __construct(
        private DocumentTypes $types,
        private DocumentProcessor $processor,
        private AllocationWrites $allocations,
    ) {
        $this->plans = new WeakMap();
    }

    public function beforeSave(Entity $entity, SaveOptions $options): void
    {
        $type = $this->types->find($entity->getEntityType());

        if (!$type || $options->get(SettlementUpdater::OPTION)) {
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

        if (!$plan) {
            return;
        }

        unset($this->plans[$entity]);

        /** @var \Espo\Modules\Itvolga\Tools\FinanceDocument\DocumentType $type */
        $type = $this->types->find($entity->getEntityType());
        $this->processor->persist($entity, $type, $plan);
    }

    public function beforeRemove(Entity $entity, RemoveOptions $options): void
    {
        $paymentType = $this->types->findPaymentByTarget($entity->getEntityType());

        if ($paymentType) {
            $this->allocations->removeForDocument($entity, $paymentType, (bool) $options->get(SaveOption::SILENT));
        }
    }
}
