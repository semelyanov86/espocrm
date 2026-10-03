<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Classes\Record\Finance;

use Espo\Core\Record\Deleted\DefaultRestorer;
use Espo\Core\Record\Deleted\Restorer;
use Espo\Modules\Itvolga\Tools\FinanceDocument\DocumentProcessor;
use Espo\ORM\Entity;

/**
 * Restorer of document items (QuoteItem, SalesOrderItem, InvoiceItem, ActItem). The core calls it for the
 * cascade-removed items of a restored document (an item alone is not restored through the API: ItemRestoreRefusal)
 * and picks them by time — removed items modified not before the document. A line removed by an edit of the
 * document's table in the same second as the document's removal would come back while the totals stay without it
 * (found by the external review of stage 04.5, reproduced on the stand); such lines are marked removedByEdit
 * (DocumentProcessor) and stay removed.
 *
 * @implements Restorer<Entity>
 */
class ItemRestorer implements Restorer
{
    public function __construct(private DefaultRestorer $restorer) {}

    public function restore(Entity $entity): void
    {
        if ($entity->get(DocumentProcessor::REMOVED_BY_EDIT)) {
            return;
        }

        $this->restorer->restore($entity);
    }
}
