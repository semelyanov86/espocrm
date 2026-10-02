<?php

namespace Espo\Modules\Itvolga\Classes\Record\Finance;

use Espo\Core\Exceptions\Conflict;
use Espo\Core\Exceptions\Error\Body;
use Espo\Core\Record\Deleted\Restorer;
use Espo\ORM\Entity;

/**
 * Deleted payment allocations are never restored (stage 04.4, owner decision 2026-10-02): the core restores the
 * cascade-removed rows of a restored payment or document directly, without hooks — the payment sum would not be
 * checked and no document would be settled. The core asks this restorer for every such row it finds; the restore of
 * a payment or a document deleted together with its rows is refused before that (OwnerRestorer).
 *
 * @implements Restorer<Entity>
 */
class AllocationRestorer implements Restorer
{
    public function restore(Entity $entity): void
    {
        throw self::denied();
    }

    public static function denied(): Conflict
    {
        return Conflict::createWithBody('financeRestoreDenied',
            Body::create()->withMessageTranslation('financeRestoreDenied', 'Global'));
    }
}
