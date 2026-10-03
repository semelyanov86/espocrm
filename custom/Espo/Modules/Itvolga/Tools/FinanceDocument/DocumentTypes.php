<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\FinanceDocument;

use Espo\Core\Utils\Metadata;

/**
 * Registry of finance records (metadata app.itvolgaFinance): documents with line items (Quote, SalesOrder, Invoice,
 * Act) and payments with their allocations (stage 04.4). all() lists documents only: the item processor, the item
 * guard and itvolga-finance-verify never see payments. Conversions prefill a new document from another one; a
 * conversion link that is has-many on the new document keeps its key on the source (Invoice → Act,
 * ConversionSourceGuard).
 */
class DocumentTypes
{
    public function __construct(private Metadata $metadata) {}

    public function find(string $entityType): ?DocumentType
    {
        $defs = $this->metadata->get(['app', 'itvolgaFinance', 'documents', $entityType]);

        if (!is_array($defs)) {
            return null;
        }

        return new DocumentType(
            $entityType,
            $defs['itemEntityType'],
            $defs['parentLink'],
            $defs['numberPrefix'],
            (int) $defs['firstNumber'],
        );
    }

    public function findByItem(string $itemEntityType): ?DocumentType
    {
        foreach ($this->all() as $type) {
            if ($type->itemEntityType === $itemEntityType) {
                return $type;
            }
        }

        return null;
    }

    /**
     * @return list<DocumentType>
     */
    public function all(): array
    {
        $list = [];

        foreach (array_keys($this->metadata->get(['app', 'itvolgaFinance', 'documents']) ?? []) as $entityType) {
            $list[] = $this->find($entityType);
        }

        return array_values(array_filter($list));
    }

    /**
     * @return ?array{link: string, fieldList: list<string>}
     */
    public function conversion(string $from, string $to): ?array
    {
        $defs = $this->metadata->get(['app', 'itvolgaFinance', 'conversions', $from, $to]);

        return is_array($defs) ? $defs : null;
    }

    /**
     * Conversions into a document type, by source type.
     *
     * @return array<string, array{link: string, fieldList: list<string>}>
     */
    public function conversionsTo(string $to): array
    {
        $list = [];

        foreach ($this->metadata->get(['app', 'itvolgaFinance', 'conversions']) ?? [] as $from => $targets) {
            if (is_array($targets[$to] ?? null)) {
                $list[$from] = $targets[$to];
            }
        }

        return $list;
    }

    public function findPayment(string $entityType): ?PaymentType
    {
        $defs = $this->metadata->get(['app', 'itvolgaFinance', 'payments', $entityType]);

        if (!is_array($defs)) {
            return null;
        }

        return new PaymentType(
            $entityType,
            $defs['allocationEntityType'],
            $defs['parentLink'],
            $defs['numberPrefix'],
            (int) $defs['firstNumber'],
            $defs['targets'],
        );
    }

    public function findPaymentByAllocation(string $allocationEntityType): ?PaymentType
    {
        foreach ($this->payments() as $type) {
            if ($type->allocationEntityType === $allocationEntityType) {
                return $type;
            }
        }

        return null;
    }

    /**
     * The payment type whose allocations may point at this document type (its settlement is stored on it).
     */
    public function findPaymentByTarget(string $documentType): ?PaymentType
    {
        foreach ($this->payments() as $type) {
            if ($type->linkOf($documentType) !== null) {
                return $type;
            }
        }

        return null;
    }

    /**
     * @return list<PaymentType>
     */
    public function payments(): array
    {
        $list = [];

        foreach (array_keys($this->metadata->get(['app', 'itvolgaFinance', 'payments']) ?? []) as $entityType) {
            $list[] = $this->findPayment($entityType);
        }

        return array_values(array_filter($list));
    }

    /**
     * Number counters of every registered record type (documents and payments).
     *
     * @return list<NumberSeries>
     */
    public function numberSeries(): array
    {
        return [
            ...array_map(static fn (DocumentType $type) => $type->series(), $this->all()),
            ...array_map(static fn (PaymentType $type) => $type->series(), $this->payments()),
        ];
    }

    /**
     * The number counter of a numbered record type (a document or a payment); null for other scopes.
     */
    public function seriesOf(string $entityType): ?NumberSeries
    {
        return ($this->find($entityType) ?? $this->findPayment($entityType))?->series();
    }

    /**
     * Scopes whose records are written only through the finance save paths (documents, items, payments, allocations).
     */
    public function isFinanceScope(string $entityType): bool
    {
        return $this->find($entityType) || $this->findByItem($entityType) || $this->findPayment($entityType) ||
            $this->findPaymentByAllocation($entityType) || $entityType === LegalEntityProvider::ENTITY_TYPE;
    }
}
