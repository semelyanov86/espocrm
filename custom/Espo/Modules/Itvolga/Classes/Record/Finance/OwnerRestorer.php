<?php

namespace Espo\Modules\Itvolga\Classes\Record\Finance;

use Espo\Core\Record\Deleted\DefaultRestorer;
use Espo\Core\Record\Deleted\Restorer;
use Espo\Modules\Itvolga\Tools\FinanceDocument\DocumentTypes;
use Espo\Modules\Itvolga\Tools\FinancePayment\AllocationRows;
use Espo\ORM\Entity;
use Espo\ORM\EntityManager;
use Espo\ORM\Name\Attribute;
use Espo\ORM\Query\SelectBuilder;

/**
 * Restoring a payment, an invoice or a sales order deleted together with allocation rows is refused (D-66): the rows
 * are never restored (AllocationRestorer), and without them the restored document keeps the paid sum of rows that are
 * gone. Which rows the core restores with a record depends on the clock (DefaultRestorer: modifiedAt not before the
 * record's); the rows carry the record they were removed with instead (AllocationRows::removeWithOwner). A record
 * deleted without allocation rows restores as before.
 *
 * @implements Restorer<Entity>
 */
class OwnerRestorer implements Restorer
{
    public function __construct(
        private EntityManager $entityManager,
        private DocumentTypes $types,
        private DefaultRestorer $restorer,
    ) {}

    public function restore(Entity $entity): void
    {
        $entityType = $entity->getEntityType();
        $type = $this->types->findPayment($entityType) ?? $this->types->findPaymentByTarget($entityType);
        $link = $type?->entityType === $entityType ? $type->parentLink : $type?->linkOf($entityType);

        if ($type && $link) {
            $query = SelectBuilder::create()
                ->from($type->allocationEntityType)
                ->withDeleted()
                ->select([Attribute::ID])
                ->where([
                    Attribute::DELETED => true,
                    $link . 'Id' => $entity->getId(),
                    AllocationRows::REMOVED_WITH => AllocationRows::ownerKey($entity),
                ])
                ->build();

            if ($this->entityManager->getRDBRepository($type->allocationEntityType)->clone($query)->findOne()) {
                throw AllocationRestorer::denied('financeRestoreOwnerDenied');
            }
        }

        $this->restorer->restore($entity);
    }
}
