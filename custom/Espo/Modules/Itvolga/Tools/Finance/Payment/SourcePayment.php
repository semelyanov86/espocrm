<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Finance\Payment;

use Espo\Modules\Itvolga\Tools\Finance\Decimal;

/**
 * A live Vtiger payment with its document references.
 */
final class SourcePayment
{
    /**
     * @param list<int> $linkedInvoiceIds live invoices linked through vtiger_crmentityrel (both directions)
     */
    public function __construct(
        public readonly int $id,
        public readonly Direction $direction,
        /** sp_payments.spstatus as stored ('' when empty). */
        public readonly string $status,
        public readonly Decimal $amount,
        /** sp_payments.related_to, 0 when empty. */
        public readonly int $relatedToId,
        /** setype of the related_to record ('' when there is no such record). */
        public readonly string $relatedToType,
        public readonly bool $relatedToDeleted,
        public readonly array $linkedInvoiceIds,
    ) {}
}
