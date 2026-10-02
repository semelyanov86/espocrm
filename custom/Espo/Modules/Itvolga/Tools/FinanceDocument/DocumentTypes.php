<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\FinanceDocument;

use Espo\Core\Utils\Metadata;

/**
 * Registry of finance documents (metadata app.itvolgaFinance): Quote and SalesOrder now, Invoice and Act later
 * only add an entry there.
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
}
