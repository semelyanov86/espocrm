<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Classes\Record\Finance;

use Espo\Core\Api\Request;
use Espo\Core\Exceptions\Conflict;
use Espo\Core\Exceptions\Error\Body;

/**
 * Controllers of document items (QuoteItem, SalesOrderItem, InvoiceItem, ActItem): a removed line is not restored on
 * its own (POST <Item>/action/restoreDeleted, administrators) — it would come back while the document's totals stay
 * without it (found by the stage 04.5 review). A line comes back with its document (the core restores the cascade-
 * removed items of a restored document through their restorer, ItemRestorer, not through this action) or is added
 * again in the document's table.
 */
trait ItemRestoreRefusal
{
    /**
     * @throws Conflict
     */
    public function postActionRestoreDeleted(Request $request): bool
    {
        throw Conflict::createWithBody('financeRestoreItemDenied',
            Body::create()->withMessageTranslation('financeRestoreItemDenied', 'Global'));
    }
}
