<?php

namespace Espo\Modules\Itvolga\Classes\Record\Finance;

use Espo\Core\Exceptions\Conflict;
use Espo\Core\Exceptions\Error\Body;
use Espo\Core\Record\Deleted\Restorer;
use Espo\ORM\Entity;

/**
 * Deleted payment allocations are never restored (stage 04.4, owner decision 2026-10-02): the core restores the
 * cascade-removed rows of a restored payment or document directly, without hooks — the payment sum would not be
 * checked and no document would be settled. The core asks this restorer for every such row, so restoring a payment
 * or a document deleted together with its allocations fails as a whole; one deleted without allocations restores.
 *
 * @implements Restorer<Entity>
 */
class AllocationRestorer implements Restorer
{
    public function restore(Entity $entity): void
    {
        throw Conflict::createWithBody('financeRestoreDenied',
            Body::create()->withMessageTranslation('financeRestoreDenied', 'Global'));
    }
}
