<?php

namespace Espo\Modules\Itvolga\Tools\Import;

use Espo\Core\ORM\Entity as CoreEntity;
use Espo\Modules\Itvolga\Tools\FinanceDocument\DocumentProcessor;
use Espo\Modules\Itvolga\Tools\FinanceDocument\DocumentTypes;
use Espo\Modules\Itvolga\Tools\FinanceDocument\RowLock;
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
 *   name, source marks): the post-save enforcement of the generic writer restores only the provenance attributes.
 */
class FinanceRules
{
    /** Header attributes of a document that a recalculation in EspoCRM owns (DocumentProcessor::header). */
    public const CALCULATION = ['taxMode', 'discountAmount', 'discountAmountCurrency', 'discountPercent',
        'shippingAmount', 'shippingAmountCurrency', 'shippingTaxPercent', 'adjustment', 'adjustmentCurrency',
        'subtotal', 'subtotalCurrency', 'preTaxTotal', 'preTaxTotalCurrency', 'grandTotal', 'grandTotalCurrency'];
    /** What the generic writer may put back after a save of a finance record. */
    public const FORCEABLE = ['createdAt', 'modifiedAt', 'createdById', 'modifiedById'];

    public function __construct(
        private DocumentTypes $types,
        private KeyResolver $keys,
        private RowLock $rowLock,
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
     * Locks the document a write depends on — the document itself, the document of an item — by its key, before the
     * first plain read of the transaction. A recalculation in EspoCRM locks the same row first (DocumentProcessor):
     * it either committed before, and every later read of this transaction sees it, or it waits for the import.
     * Without the lock a recalculation committed between the import's read and its save would be overwritten.
     */
    public function lock(stdClass $op): void
    {
        $type = $op->entityType;

        if ($this->isDocument($type)) {
            [$documentType, $key] = [$type, $op->vtigerId];
        } elseif ($itemOf = $this->types->findByItem($type)) {
            $ref = $op->links->{$itemOf->parentLink} ?? null;
            [$documentType, $key] = [$itemOf->entityType, is_array($ref) ? $ref[1] : null];
        } else {
            return;
        }

        if (is_int($key)) {
            $this->rowLock->query($documentType)->where(['vtigerId' => $key])->findOne();
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

        if ($stored?->get('deleted')) {
            return ['status' => 'deleted_in_target', 'reason' => 'self', 'id' => $id];
        }

        return null;
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
