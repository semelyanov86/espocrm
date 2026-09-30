<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Finance\Payment;

/**
 * Where the allocation of a source payment comes from; the values are the categories of
 * scripts/audit/sql/33_allocation_check.sql (strict partition of live payments).
 */
enum AllocationCategory: string
{
    /** related_to → invoice, and the Invoice↔payment link points to the same invoice. */
    case BothSameInvoice = 'both_same_invoice';
    /** related_to → invoice, no link. */
    case RelatedToInvoiceOnly = 'related_to_invoice_only';
    /** related_to → sales order. */
    case RelatedToSalesOrder = 'related_to_salesorder';
    /** related_to → invoice, the link points to another invoice (D-11: related_to wins, the case is reported). */
    case ConflictRelOtherInvoice = 'conflict_rel_other_invoice';
    /** related_to empty, a link to an invoice exists. */
    case RelOnly = 'rel_only';
    /** Neither related_to nor a link. */
    case Unallocated = 'unallocated';
    /** A shape the source data does not contain (deleted target, several links, link next to a sales order ...). */
    case Other = 'other';
}
