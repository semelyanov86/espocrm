<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Finance\Payment;

/**
 * Allocation of a source payment to a document, D-11: `related_to` is the source; the Invoice↔payment link of
 * vtiger_crmentityrel counts only when `related_to` is empty; a link that disagrees with `related_to` is a conflict that
 * is reported, not guessed; the allocated amount is the whole payment (the source never splits payments).
 *
 * Outgoing payments that only have a link to a customer invoice (bank import artefacts) are not allocated (owner
 * decision Q-36); any shape absent from the live data is Unresolved.
 */
final class SourceAllocationResolver
{
    private const INVOICE = 'Invoice';
    private const SALES_ORDER = 'SalesOrder';

    public function resolve(SourcePayment $payment): SourceAllocation
    {
        $links = array_values(array_unique($payment->linkedInvoiceIds));

        if ($payment->relatedToId !== 0) {
            return $this->byRelatedTo($payment, $links);
        }

        if ($links === []) {
            return new SourceAllocation(AllocationCategory::Unallocated, AllocationDecision::None, null, null, null);
        }

        $candidate = min($links);

        if (count($links) > 1) {
            return $this->unresolved(AllocationCategory::Other, self::INVOICE, $candidate,
                'several invoice links and no related_to (not in the source data)');
        }

        if ($payment->direction === Direction::Outgoing) {
            // Bank import artefacts: payer and amount never match the invoice. Owner decision Q-36: not allocated;
            // the link goes to vtigerData and the report.
            return new SourceAllocation(AllocationCategory::RelOnly, AllocationDecision::None, self::INVOICE, $candidate, null, [],
                'outgoing payment linked to a customer invoice only through the related list: not allocated (Q-36)');
        }

        return $this->allocate(AllocationCategory::RelOnly, $payment, self::INVOICE, $candidate);
    }

    /**
     * @param list<int> $links
     */
    private function byRelatedTo(SourcePayment $payment, array $links): SourceAllocation
    {
        $type = $payment->relatedToType;
        $id = $payment->relatedToId;

        if ($payment->relatedToDeleted || !in_array($type, [self::INVOICE, self::SALES_ORDER], true)) {
            // No candidate: the link must not replace a non-empty related_to (D-11), and the target is not a document.
            return $this->unresolved(AllocationCategory::Other, null, null,
                'related_to points to a deleted or non-document record (not in the source data)');
        }

        if ($payment->direction === Direction::Outgoing) {
            return $this->unresolved(AllocationCategory::Other, $type, $id,
                'outgoing payment with related_to (not in the source data)');
        }

        if ($type === self::SALES_ORDER) {
            if ($links !== []) {
                return $this->unresolved(AllocationCategory::Other, $type, $id,
                    'related_to → sales order and an invoice link (not in the source data)');
            }

            return $this->allocate(AllocationCategory::RelatedToSalesOrder, $payment, $type, $id);
        }

        if ($links === []) {
            return $this->allocate(AllocationCategory::RelatedToInvoiceOnly, $payment, $type, $id);
        }

        if ($links === [$id]) {
            return $this->allocate(AllocationCategory::BothSameInvoice, $payment, $type, $id);
        }

        if (count($links) > 1) {
            return $this->unresolved(AllocationCategory::Other, $type, $id,
                'several invoice links next to related_to (not in the source data)');
        }

        return $this->allocate(AllocationCategory::ConflictRelOtherInvoice, $payment, $type, $id, $links,
            'the invoice link points to another invoice: allocated by related_to, manual check (D-11)');
    }

    /**
     * @param list<int> $conflicts
     */
    private function allocate(
        AllocationCategory $category,
        SourcePayment $payment,
        string $type,
        int $id,
        array $conflicts = [],
        ?string $reason = null,
    ): SourceAllocation {
        if (!$payment->amount->isPositive()) {
            return $this->unresolved($category, $type, $id, 'allocation of a zero payment (not in the source data)');
        }

        return new SourceAllocation($category, AllocationDecision::Allocate, $type, $id, $payment->amount, $conflicts, $reason);
    }

    private function unresolved(AllocationCategory $category, ?string $type, ?int $id, string $reason): SourceAllocation
    {
        return new SourceAllocation($category, AllocationDecision::Unresolved, $type, $id, null, [], $reason);
    }
}
