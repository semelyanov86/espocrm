<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\FinanceDocument;

/**
 * A finance document with line items, as registered in metadata app.itvolgaFinance.documents.
 */
final class DocumentType
{
    public function __construct(
        public readonly string $entityType,
        public readonly string $itemEntityType,
        /** Link of the item to its document (QuoteItem.quote). */
        public readonly string $parentLink,
        public readonly string $numberPrefix,
        /** First number of documents created in EspoCRM (Vtiger cur_id at the audit snapshot). */
        public readonly int $firstNumber,
    ) {}

    public function series(): NumberSeries
    {
        return new NumberSeries($this->entityType, $this->numberPrefix, $this->firstNumber);
    }
}
