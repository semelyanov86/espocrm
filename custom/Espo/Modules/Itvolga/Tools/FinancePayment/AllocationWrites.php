<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\FinancePayment;

use Espo\Core\Exceptions\Error;
use Espo\Core\ORM\Repository\Option\SaveOption;
use Espo\Core\Utils\Config;
use Espo\Modules\Itvolga\Tools\Finance\Decimal;
use Espo\Modules\Itvolga\Tools\Finance\Exceptions\InvalidValue;
use Espo\Modules\Itvolga\Tools\Finance\Exceptions\OverAllocation;
use Espo\Modules\Itvolga\Tools\Finance\Payment\AllocationCalculator;
use Espo\Modules\Itvolga\Tools\Finance\Payment\AllocationInput;
use Espo\Modules\Itvolga\Tools\Finance\Payment\AllocationPlan;
use Espo\Modules\Itvolga\Tools\Finance\Payment\Direction;
use Espo\Modules\Itvolga\Tools\Finance\Scale;
use Espo\Modules\Itvolga\Tools\FinanceDocument\NumberAllocator;
use Espo\Modules\Itvolga\Tools\FinanceDocument\PaymentType;
use Espo\ORM\Entity;
use Espo\ORM\EntityManager;

/**
 * Allocation rows written outside the payment's table: by the importer (stage 06.3, ORM with SaveOption::IMPORT;
 * source relatedTo / relationLink, sourceConflict, vtigerData as in the source, D-11) and removed with their document.
 * The import path is not a bypass of the payment's invariants: one document per row, a live incoming payment, the
 * sum of its rows within the payment, the same lock order as a payment save, and the settlement of the documents.
 * Errors name the record, never a value.
 */
class AllocationWrites
{
    public function __construct(
        private EntityManager $entityManager,
        private Config $config,
        private NumberAllocator $numberAllocator,
        private AllocationRows $rows,
        private SettlementUpdater $settlement,
        private AllocationHistory $history,
    ) {}

    /**
     * beforeSave of an imported row: locks and checks; returns the locked documents to settle after the save.
     *
     * @return array<string, Entity>
     * @throws Error
     */
    public function prepare(Entity $row, PaymentType $type): array
    {
        $name = "{$type->allocationEntityType} {$row->getId()}";

        if (!$row->isNew() && $row->isAttributeChanged($type->parentLink . 'Id')) {
            throw new Error("$name: the payment of an allocation never changes.");
        }

        if (!$this->numberAllocator->lock($type->series())) {
            throw new Error("Numbering of {$type->entityType} is not configured: run itvolga-setup-finance.");
        }

        $payment = $this->entityManager
            ->getRDBRepository($type->entityType)
            ->where(['id' => $row->get($type->parentLink . 'Id')])
            ->forUpdate()
            ->findOne() ?? throw new Error("$name: the payment does not exist.");

        if (Direction::tryFrom((string) $payment->get('direction')) !== Direction::Incoming) {
            throw new Error("$name: an outgoing payment is not allocated (D-49, Q-36).");
        }

        $locked = $this->rows->find($payment->getId(), $type, true);
        $current = $row->isNew() ? null : ($locked[$row->getId()] ?? null);

        if (!$row->isNew() && !$current) {
            throw new Error("$name: the allocation does not exist any more.");
        }

        $loadedKeys = [];

        if ($current) {
            foreach ($type->targets as $documentType => $link) {
                if ($row->getFetched($link . 'Id')) {
                    $loadedKeys[] = $documentType . ':' . $row->getFetched($link . 'Id');
                }
            }

            // The entity was loaded before the lock: unchanged values are the locked row's (another save may have
            // moved or changed it meanwhile), so the ORM writes exactly what this save changes.
            foreach (['amount', 'order', ...array_keys($type->targetAttributes())] as $attribute) {
                if (!$row->isAttributeChanged($attribute)) {
                    $row->set($attribute, $current->get($attribute));
                }

                $row->setFetched($attribute, $current->get($attribute));
            }
        }

        try {
            $input = AllocationInput::fromArray((array) $row->getValueMap(), 1, $type->targetAttributes())
                ->withId($row->isNew() ? null : $row->getId());
        } catch (InvalidValue $e) {
            throw new Error("$name: rejected allocation ({$e->key}).");
        }

        $amounts = [$input->amount];
        $order = 0;

        foreach ($locked as $stored) {
            if ($stored->getId() === $row->getId()) {
                continue;
            }

            $other = $this->rows->toInput($stored, $type);

            if ($other->targetKey() === $input->targetKey()) {
                throw new Error("$name: the payment already has a row for this document.");
            }

            $amounts[] = $other->amount;
            $order = max($order, (int) $stored->get('order'));
        }

        try {
            (new AllocationCalculator())->remainder(Decimal::of($payment->get('amount')), $amounts);
        } catch (OverAllocation) {
            throw new Error("$name: the allocations exceed the payment.");
        }

        // The resulting document, the current one and the one of the loaded copy: every document whose sum may differ.
        $keys = [$input->targetKey(), ...$loadedKeys];

        if ($current) {
            $keys[] = $this->rows->toInput($current, $type)->targetKey();
        }

        $documents = $this->rows->lockDocuments(AllocationPlan::sortedKeys($keys));

        if (!isset($documents[$input->targetKey()])) {
            throw new Error("$name: the document does not exist.");
        }

        if ($row->isNew() && !$row->get('order')) {
            $row->set('order', $order + 1);
        }

        $row->set([
            'amount' => $input->amount->toFixed(Scale::MONEY),
            'amountCurrency' => (string) $this->config->get('defaultCurrency'),
            'name' => trim($payment->get('number') . ' → ' . $documents[$input->targetKey()]->get('number')),
        ]);

        return $documents;
    }

    /**
     * @param array<string, Entity> $documents
     */
    public function settle(array $documents): void
    {
        foreach ($documents as $document) {
            $this->settlement->recompute($document, true);
        }
    }

    /**
     * beforeRemove of a row that is not removed by its payment's save: locks the ledger and the row's document (an
     * imported row removed by the importer), or nothing (its payment or its document is being removed).
     *
     * @return array<string, Entity>
     */
    public function prepareRemoval(Entity $row, PaymentType $type): array
    {
        $this->numberAllocator->lock($type->series());

        // The current target of the row, not the one of the copy loaded before the lock.
        $current = $this->entityManager
            ->getRDBRepository($type->allocationEntityType)
            ->where(['id' => $row->getId()])
            ->forUpdate()
            ->findOne();

        return $current ? $this->rows->lockDocuments([$this->rows->toInput($current, $type)->targetKey()]) : [];
    }

    /**
     * beforeRemove of an invoice or a sales order: its rows are removed here, under the ledger, from a locking read —
     * not by the core cascade, whose plain read may come from a snapshot older than the lock and miss a row another
     * save committed meanwhile. Each payment's history shows the row leaving the table, by the user who removed the
     * document; the payments' unallocated rest grows by itself (derived on read).
     */
    public function removeForDocument(Entity $document, PaymentType $type, bool $silent): void
    {
        if (!$this->numberAllocator->lock($type->series())) {
            return;
        }

        $link = $type->linkOf($document->getEntityType());
        $rows = $this->entityManager
            ->getRDBRepository($type->allocationEntityType)
            ->where([$link . 'Id' => $document->getId()])
            ->order($type->parentLink . 'Id')
            ->forUpdate()
            ->find();

        foreach ($rows as $row) {
            // A locking read: a payment committed while this removal waited is not in the transaction's snapshot.
            $payment = $this->entityManager
                ->getRDBRepository($type->entityType)
                ->where(['id' => $row->get($type->parentLink . 'Id')])
                ->forUpdate()
                ->findOne();
            $before = $payment ? $this->rows->find($payment->getId(), $type, true) : [];

            $this->entityManager->removeEntity($row, [PaymentProcessor::WRITE_OPTION => true, SaveOption::SILENT => true]);

            if ($payment && !$silent) {
                $this->recordRemoval($payment, $type, $before, $row->getId());
            }
        }
    }

    /**
     * @param array<string, Entity> $before the payment's rows before the removal, in order
     */
    private function recordRemoval(Entity $payment, PaymentType $type, array $before, string $removedId): void
    {
        $documents = $this->rows->findDocuments(array_map(fn (Entity $row) => $this->rows->toInput($row, $type), $before));
        $after = array_filter($before, static fn (Entity $row) => $row->getId() !== $removedId);

        $this->history->record($payment, $this->rows->presentStored($before, $type, $documents),
            $this->rows->presentStored($after, $type, $documents));
    }
}
