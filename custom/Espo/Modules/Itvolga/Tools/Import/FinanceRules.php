<?php

namespace Espo\Modules\Itvolga\Tools\Import;

use Espo\Core\ORM\Entity as CoreEntity;
use Espo\Modules\Itvolga\Tools\FinanceDocument\DocumentProcessor;
use Espo\Modules\Itvolga\Tools\FinanceDocument\DocumentTypes;
use Espo\Modules\Itvolga\Tools\FinanceDocument\NumberAllocator;
use Espo\Modules\Itvolga\Tools\FinanceDocument\RowLock;
use Espo\Modules\Itvolga\Tools\FinancePayment\AllocationRows;
use Espo\ORM\Entity;
use stdClass;

/**
 * Finance records of the import (stage 06.3, owner's answers 2026-10-11; finance-contract §14.2, §16.5):
 *
 * - a finance record deleted in EspoCRM is not restored: the import answers `deleted_in_target` (a finding, the policy
 *   is the delta of stage 06.4); an item or an allocation of a deleted document or payment the same, with reason
 *   `owner`/`target`;
 * - a document recalculated in EspoCRM (vtigerData.sourceTotals, D-51) keeps its calculation data — header inputs,
 *   totals, items — and its snapshot; the other fields still follow the source (`protected`); the write of a document
 *   or an item holds the document's row from its first read (`lock`), so a concurrent recalculation is kept too;
 * - the finance hooks own the derived values (legal entity, settlement, allocation name, order and rounding, payment
 *   name, source marks): the post-save enforcement of the generic writer restores only the provenance attributes;
 * - stage 06.4 (owner's answers 2026-10-12): a finance record gone from the source is removed through its hooks under
 *   the payment-side lock order, a recalculated document and its items are kept; the delta's own tombstones carry
 *   `vtigerData.deletedInSource` (set by the hook FinanceDeltaMark, cleared by it on any other removal) and come back
 *   when the source has the record again (D-148 still holds for a record deleted in EspoCRM).
 */
class FinanceRules
{
    /** Header attributes of a document that a recalculation in EspoCRM owns (DocumentProcessor::header). */
    public const CALCULATION = ['taxMode', 'discountAmount', 'discountAmountCurrency', 'discountPercent',
        'shippingAmount', 'shippingAmountCurrency', 'shippingTaxPercent', 'adjustment', 'adjustmentCurrency',
        'subtotal', 'subtotalCurrency', 'preTaxTotal', 'preTaxTotalCurrency', 'grandTotal', 'grandTotalCurrency'];
    /** What the generic writer may put back after a save of a finance record. */
    public const FORCEABLE = ['createdAt', 'modifiedAt', 'createdById', 'modifiedById'];

    /** Mark of a finance tombstone made by the delta (the record left the source), not by a user. */
    public const DELETED_IN_SOURCE = 'deletedInSource';

    public function __construct(
        private DocumentTypes $types,
        private KeyResolver $keys,
        private RowLock $rowLock,
        private NumberAllocator $numberAllocator,
    ) {}

    public function isFinance(string $entityType): bool
    {
        return $this->types->isFinanceScope($entityType);
    }

    public function isDocument(string $entityType): bool
    {
        return (bool) $this->types->find($entityType);
    }

    /**
     * Locks what a write depends on, by key, before the first plain read of the transaction: the document itself or
     * the document of an item (a recalculation in EspoCRM locks the same row first, DocumentProcessor: it either
     * committed before, and every later read of this transaction sees it, or it waits for the import); a payment or an
     * allocation takes the payment ledger first and then its own row (the order of PaymentProcessor). The record's own
     * row is locked with its tombstone (stage 06.4): whether a deleted record comes back (`deletedInSource`, D-158) is
     * decided while nobody can restore it or delete it again.
     */
    public function lock(stdClass $op): void
    {
        $type = $op->entityType;
        $key = $op->vtigerId ?? null;

        if ($payment = $this->types->findPayment($type) ?? $this->types->findPaymentByAllocation($type)) {
            $this->numberAllocator->lock($payment->series());

            if (is_int($key)) {
                $this->rowLock->lockWithDeleted($type, ['vtigerId' => $key]);
            }

            return;
        }

        if ($this->isDocument($type)) {
            if (is_int($key)) {
                $this->rowLock->lockWithDeleted($type, ['vtigerId' => $key]);
            }

            return;
        }

        if ($itemOf = $this->types->findByItem($type)) {
            $ref = $op->links->{$itemOf->parentLink} ?? null;

            if (is_array($ref) && is_int($ref[1])) {
                $this->rowLock->query($itemOf->entityType)->where(['vtigerId' => $ref[1]])->findOne();
            }
        }
    }

    /**
     * The answer instead of a write or a comparison, or null when the operation proceeds.
     *
     * @return ?array<string, mixed>
     * @throws ImportError the owner of an item or an allocation was never imported (a write; the check answers
     *   «missing» for the item instead)
     */
    public function guard(stdClass $op, ?Entity $stored, bool $check = false): ?array
    {
        $type = $op->entityType;

        if (!$this->isFinance($type)) {
            return null;
        }

        $id = $stored?->getId();

        if ($itemOf = $this->types->findByItem($type)) {
            $owner = $this->owner($op, $itemOf->parentLink, $itemOf->entityType, $check);

            if (!$owner) {
                return null; // the check pass before the document is imported: the item is missing too
            }

            if ($owner->get('deleted')) {
                return ['status' => 'deleted_in_target', 'reason' => 'owner', 'id' => $id];
            }

            if ($this->isRecalculated($owner)) {
                return ['status' => 'protected', 'reason' => 'recalculated_in_target', 'id' => $id];
            }

            // An item the source moves to another document leaves its current one: never out of a recalculated
            // document (its row is locked like the requested one; a removed document no longer protects anything).
            $current = $stored?->get($itemOf->parentLink . 'Id');

            if ($current && $current !== $owner->getId()) {
                $previous = $this->rowLock->one($itemOf->entityType, $current);

                if ($previous && $this->isRecalculated($previous)) {
                    return ['status' => 'protected', 'reason' => 'recalculated_in_target', 'id' => $id];
                }
            }
        }

        if ($payment = $this->types->findPaymentByAllocation($type)) {
            $owner = $this->owner($op, $payment->parentLink, $payment->entityType, $check);

            if (!$owner) {
                return null;
            }

            if ($owner->get('deleted')) {
                return ['status' => 'deleted_in_target', 'reason' => 'owner', 'id' => $id];
            }

            foreach ($payment->targets as $documentType => $link) {
                $ref = $op->links->$link ?? null;

                if ($ref !== null && $this->keys->isDeleted($documentType, $ref[1])) {
                    return ['status' => 'deleted_in_target', 'reason' => 'target', 'id' => $id];
                }
            }
        }

        if ($stored?->get('deleted') && !$this->isDeletedInSource($stored)) {
            return ['status' => 'deleted_in_target', 'reason' => 'self', 'id' => $id];
        }

        return null; // a delta's tombstone back in the source is restored like any record (stage 06.4)
    }

    public function isDeletedInSource(Entity $entity): bool
    {
        $data = $entity->get('vtigerData');

        return $data instanceof stdClass && ($data->{self::DELETED_IN_SOURCE} ?? false) === true;
    }

    /**
     * Locks what the removal of a finance record goes through, in the order of the payment side (PaymentProcessor):
     * the payment ledger first for an invoice, an order, a payment or an allocation — their removal hooks take it, and
     * a document row locked before it would invert the order —, then the record's own row (a document, a payment) or
     * the row of the item's document (as an upsert of an item, FinanceRules::lock). The policy below reads the locked
     * rows: a recalculation committed meanwhile is seen, a later one waits.
     */
    public function lockForRemoval(string $entityType, Entity $stored): void
    {
        $this->lockLedger($entityType); // taken already by RemovalWriter before its first read; re-entrant

        if ($this->isDocument($entityType) || $this->types->findPayment($entityType)) {
            $this->rowLock->one($entityType, $stored->getId());
        } elseif (($itemOf = $this->types->findByItem($entityType)) && $stored->get($itemOf->parentLink . 'Id')) {
            $this->rowLock->one($itemOf->entityType, $stored->get($itemOf->parentLink . 'Id'));
        }
    }

    /**
     * The payment ledger of every finance record whose removal touches the payment side — a payment, an allocation, a
     * document allocations point to and its items — locked before the first plain read of the removal's transaction
     * (stage 06.4): every allocation write takes the ledger first, so the consistent reads of the core's cascades see
     * the allocations as they are while the removal runs, not as they were before a concurrent move.
     */
    public function lockLedger(string $entityType): void
    {
        $itemOf = $this->types->findByItem($entityType);
        $payment = $this->types->findPayment($entityType) ?? $this->types->findPaymentByAllocation($entityType)
            ?? $this->types->findPaymentByTarget($itemOf?->entityType ?? $entityType);

        if ($payment) {
            $this->numberAllocator->lock($payment->series());
        }
    }

    /**
     * Why a finance record gone from the source stays (a finding), or null. A document stays when it was recalculated
     * in EspoCRM (D-51), when an imported allocation still points to it (the allocation goes by its own removal: the
     * document's hook would remove it without the delta's mark, D-158) or when it has live items of another key range
     * (the core's cascade would remove them past the run's boundary). An item stays when its document is recalculated
     * and, when the run removes the document too (items go first, RunContext::removes), whenever the document will stay
     * — a document kept with its totals and allocations keeps its items. An item gone from a document the source still
     * has goes (Vtiger writes the lines of a document anew on every save).
     */
    public function keptOnRemoval(string $entityType, Entity $stored, RunContext $run): ?string
    {
        if ($this->isDocument($entityType)) {
            $document = $this->rowLock->one($entityType, $stored->getId());

            return $document ? $this->documentKept($document, $run) : null;
        }

        if ($itemOf = $this->types->findByItem($entityType)) {
            $documentId = $stored->get($itemOf->parentLink . 'Id');
            $document = $documentId ? $this->rowLock->one($itemOf->entityType, $documentId) : null;

            if (!$document || $document->get('deleted')) {
                return null;
            }

            if ($this->isRecalculated($document)) {
                return 'recalculated_in_target';
            }

            return $run->removes($itemOf->entityType, $document->get('vtigerId')) ?
                $this->documentKept($document, $run) : null;
        }

        return null;
    }

    private function documentKept(Entity $document, RunContext $run): ?string
    {
        $type = $document->getEntityType();

        if ($this->isRecalculated($document)) {
            return 'recalculated_in_target';
        }

        $payment = $this->types->findPaymentByTarget($type);
        $link = $payment?->linkOf($type);

        if ($link && $this->rowLock->query($payment->allocationEntityType)
                ->where([$link . 'Id' => $document->getId(), 'vtigerId!=' => null])->findOne()) {
            return 'allocated_in_target';
        }

        $documentType = $this->types->find($type);

        foreach ($this->rowLock->query($documentType->itemEntityType)
                     ->where([$documentType->parentLink . 'Id' => $document->getId(), 'vtigerId!=' => null])->find()
                 as $item) {
            if (!$run->inRange($item->get('vtigerId'))) {
                return 'items_outside_run';
            }
        }

        return null;
    }

    /**
     * Attributes a restored finance tombstone resets: the item's «removed by an edit» and the allocation's «removed with
     * its owner» marks (an owner restored through the API refuses rows with the latter, OwnerRestorer).
     *
     * @return array<string, mixed>
     */
    public function revivalReset(string $entityType): array
    {
        if ($this->types->findByItem($entityType)) {
            return [DocumentProcessor::REMOVED_BY_EDIT => false];
        }

        if ($this->types->findPaymentByAllocation($entityType)) {
            return [AllocationRows::REMOVED_WITH => null];
        }

        return [];
    }

    public function isRecalculated(Entity $document): bool
    {
        $data = $document->get('vtigerData');

        return $data instanceof stdClass && isset($data->{DocumentProcessor::SOURCE_TOTALS});
    }

    /**
     * A document recalculated in EspoCRM: the calculation attributes leave the operation and the stored snapshot of
     * the source totals stays in vtigerData.
     *
     * @return string[] Attributes the import does not own on this record.
     */
    public function protect(stdClass $op, CoreEntity $stored): array
    {
        if (!$this->isDocument($op->entityType) || !$this->isRecalculated($stored)) {
            return [];
        }

        $protected = [];

        foreach (self::CALCULATION as $attribute) {
            if (property_exists($op->attributes, $attribute)) {
                unset($op->attributes->$attribute);
                $protected[] = $attribute;
            }
        }

        $key = DocumentProcessor::SOURCE_TOTALS;
        $data = is_object($op->attributes->vtigerData ?? null) ? clone $op->attributes->vtigerData : new stdClass();
        $data->$key = $stored->get('vtigerData')->$key;
        $op->attributes->vtigerData = $data;

        return $protected;
    }

    /**
     * @param array<string, mixed> $want attribute => value the generic writer would put back
     * @return array<string, mixed>
     */
    public function forceable(string $entityType, array $want): array
    {
        return $this->isFinance($entityType) ? array_intersect_key($want, array_flip(self::FORCEABLE)) : $want;
    }

    private function owner(stdClass $op, string $link, string $entityType, bool $check): ?Entity
    {
        $ref = $op->links->$link ?? null;
        $owner = is_array($ref) ? $this->keys->findWithDeleted($entityType, $ref[1]) : null;

        if (!$owner && !$check) {
            throw new ImportError('owner_missing', [$link]);
        }

        return $owner;
    }
}
