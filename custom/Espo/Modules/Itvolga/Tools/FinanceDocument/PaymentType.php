<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\FinanceDocument;

/**
 * Payments, as registered in metadata app.itvolgaFinance.payments: a payment owns its allocation rows, each row points
 * at exactly one target document (Invoice or SalesOrder).
 */
final class PaymentType
{
    /**
     * @param array<string, string> $targets document entity type => link of the allocation to it
     */
    public function __construct(
        public readonly string $entityType,
        public readonly string $allocationEntityType,
        /** Link of the allocation to its payment (PaymentAllocation.payment). */
        public readonly string $parentLink,
        public readonly string $numberPrefix,
        public readonly int $firstNumber,
        public readonly array $targets,
    ) {}

    public function series(): NumberSeries
    {
        return new NumberSeries($this->entityType, $this->numberPrefix, $this->firstNumber);
    }

    public function linkOf(string $documentType): ?string
    {
        return $this->targets[$documentType] ?? null;
    }

    /**
     * @return array<string, string> allocation id attribute => document entity type (invoiceId => Invoice)
     */
    public function targetAttributes(): array
    {
        $attributes = [];

        foreach ($this->targets as $entityType => $link) {
            $attributes[$link . 'Id'] = $entityType;
        }

        return $attributes;
    }
}
