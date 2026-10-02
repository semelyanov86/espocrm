<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\FinancePayment;

use Espo\Modules\Itvolga\Tools\Finance\Payment\AllocationPlan;
use Espo\ORM\Entity;

/**
 * What PaymentProcessor::prepare decided, for persist() in afterSave of the same transaction.
 */
final class PaymentPlan
{
    /**
     * @param array<string, Entity> $stored locked rows of the payment by id
     * @param array<string, Entity> $documents locked documents by key ("Invoice:<id>")
     * @param array<int, string> $newIds ids generated for new rows, by position in the plan
     * @param list<string> $settle keys of the documents to recompute, sorted
     */
    public function __construct(
        public readonly AllocationPlan $edit,
        public readonly array $stored,
        public readonly array $documents,
        public readonly array $newIds,
        public readonly array $settle,
        public readonly bool $isNew,
        public readonly bool $silent,
    ) {}
}
