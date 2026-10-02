<?php

namespace Espo\Modules\Itvolga\Hooks\Common;

use Espo\Core\Exceptions\Conflict;
use Espo\Core\Exceptions\Error\Body;
use Espo\Core\Exceptions\Forbidden;
use Espo\Core\Hook\Hook\BeforeRemove;
use Espo\Core\Hook\Hook\BeforeSave;
use Espo\Core\ORM\Repository\Option\SaveOption;
use Espo\Modules\Itvolga\Tools\FinanceDocument\DocumentProcessor;
use Espo\Modules\Itvolga\Tools\FinanceDocument\DocumentTypes;
use Espo\ORM\Entity;
use Espo\ORM\EntityManager;
use Espo\ORM\Repository\Option\RemoveOptions;
use Espo\ORM\Repository\Option\SaveOptions;

/**
 * Items of finance documents are written only together with their document (DocumentProcessor), allocations of
 * payments only together with their payment (PaymentProcessor), both also by the importer (SaveOption::IMPORT): a
 * direct write would change a line without recalculating the totals, or an allocation without checking the payment
 * sum and settling the documents. The API is closed by ACL already (Classes/Acl/FinanceItem); this guard covers
 * internal ORM paths. Removing the rows of a deleted owner (cascade removal: a deleted document or payment) is
 * allowed. The core cascade reads rows from the transaction's snapshot, which may be older than the locks: an
 * allocation is judged by its current locked row, so a row that another save moved to a live document meanwhile is
 * never removed with the old one (the removal fails as a conflict and can be repeated).
 *
 * @implements BeforeSave<Entity>
 * @implements BeforeRemove<Entity>
 */
class FinanceItemGuard implements BeforeSave, BeforeRemove
{
    public function __construct(
        private DocumentTypes $types,
        private EntityManager $entityManager,
    ) {}

    public function beforeSave(Entity $entity, SaveOptions $options): void
    {
        if ($this->owners($entity) === null || $this->isAllowed($options)) {
            return;
        }

        throw new Forbidden('Rows of finance records are changed only through their document or payment.');
    }

    public function beforeRemove(Entity $entity, RemoveOptions $options): void
    {
        $owners = $this->owners($entity);

        if ($owners === null || $this->isAllowed($options)) {
            return;
        }

        if ($this->allAlive($owners)) {
            throw new Forbidden('Rows of finance records are removed only through their document or payment.');
        }

        // A cascade: an owner of the loaded copy is gone. An allocation is judged by its current locked row — the
        // copy may come from a snapshot older than the locks, and the row may have been moved to a live document.
        if (!$this->types->findPaymentByAllocation($entity->getEntityType())) {
            return;
        }

        $current = $this->entityManager
            ->getRDBRepository($entity->getEntityType())
            ->where(['id' => $entity->getId()])
            ->forUpdate()
            ->findOne();

        // Locking reads (fresh, not the snapshot): the payment, then the document — the order of the ledger holders.
        if ($current && $this->allAlive($this->owners($current) ?? [], true)) {
            throw Conflict::createWithBody('financeAllocationChanged',
                Body::create()->withMessageTranslation('financeAllocationChanged', 'Global'));
        }
    }

    /**
     * @param list<array{string, ?string}> $owners
     */
    private function allAlive(array $owners, bool $lock = false): bool
    {
        foreach ($owners as [$entityType, $id]) {
            $found = $id && ($lock
                ? $this->entityManager->getRDBRepository($entityType)->where(['id' => $id])->forUpdate()->findOne()
                : $this->entityManager->getEntityById($entityType, $id));

            if (!$found) {
                return false;
            }
        }

        return true;
    }

    /**
     * Records a row belongs to: the document of an item; the payment and the target document of an allocation.
     *
     * @return ?list<array{string, ?string}> entity type and id; null when the entity is not a finance row
     */
    private function owners(Entity $entity): ?array
    {
        if ($type = $this->types->findByItem($entity->getEntityType())) {
            return [[$type->entityType, $entity->get($type->parentLink . 'Id')]];
        }

        $type = $this->types->findPaymentByAllocation($entity->getEntityType());

        if (!$type) {
            return null;
        }

        $owners = [[$type->entityType, $entity->get($type->parentLink . 'Id')]];

        foreach ($type->targets as $documentType => $link) {
            if ($entity->get($link . 'Id')) {
                $owners[] = [$documentType, $entity->get($link . 'Id')];
            }
        }

        return $owners;
    }

    private function isAllowed(SaveOptions|RemoveOptions $options): bool
    {
        return (bool) $options->get(DocumentProcessor::WRITE_OPTION) || (bool) $options->get(SaveOption::IMPORT);
    }
}
