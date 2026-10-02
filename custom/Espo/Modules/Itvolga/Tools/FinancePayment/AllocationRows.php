<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\FinancePayment;

use Espo\Core\ORM\Repository\Option\SaveOption;
use Espo\Modules\Itvolga\Tools\Finance\Decimal;
use Espo\Modules\Itvolga\Tools\Finance\Payment\AllocationInput;
use Espo\Modules\Itvolga\Tools\Finance\Scale;
use Espo\Modules\Itvolga\Tools\FinanceDocument\PaymentType;
use Espo\ORM\Entity;
use Espo\ORM\EntityManager;
use Espo\ORM\Query\SelectBuilder;
use stdClass;

/**
 * Allocation rows of a payment as records and as the `allocationList` table. The table has one canonical form —
 * `{id, order, invoiceId, invoiceName, salesOrderId, salesOrderName, documentNumber, amount}` with the amount in
 * kopecks — for the API, the form and the history (Update notes compare and show it), so equal tables are equal
 * values whatever notation the input used.
 */
class AllocationRows
{
    /** The owner a row was removed with ("Payment:<id>", "Invoice:<id>"): restoring that owner is refused. */
    public const REMOVED_WITH = 'removedWith';
    private const OWN_COLUMNS = ['id', 'order', 'amount', 'source'];

    public function __construct(private EntityManager $entityManager) {}

    /**
     * Removes a row together with its payment or document, marked with that owner. The core restores the
     * cascade-removed rows of a restored record by time — modifiedAt not before the record's, which the core sets
     * after the record's beforeRemove hooks that remove the rows — so it may find or miss them; the mark refuses the
     * owner's restore whatever the clock (Classes/Record/Finance/OwnerRestorer).
     */
    public function removeWithOwner(Entity $row, Entity $owner): void
    {
        $row->set(self::REMOVED_WITH, self::ownerKey($owner));
        $this->entityManager->removeEntity($row, [PaymentProcessor::WRITE_OPTION => true, SaveOption::SILENT => true]);
    }

    public static function ownerKey(Entity $owner): string
    {
        return $owner->getEntityType() . ':' . $owner->getId();
    }

    /**
     * Rows of a payment in their order; with $lock, a locking read of the rows' own columns only (no joins: rows of
     * other tables are not locked).
     *
     * @return array<string, Entity> by id
     */
    public function find(string $paymentId, PaymentType $type, bool $lock = false): array
    {
        $builder = $this->entityManager
            ->getRDBRepository($type->allocationEntityType)
            ->select([...self::OWN_COLUMNS, $type->parentLink . 'Id', ...array_keys($type->targetAttributes())])
            ->where([$type->parentLink . 'Id' => $paymentId])
            ->order('order')
            ->order('id');

        if ($lock) {
            $builder->forUpdate();
        }

        $rows = [];

        foreach ($builder->find() as $row) {
            $rows[$row->getId()] = $row;
        }

        return $rows;
    }

    public function toInput(Entity $row, PaymentType $type): AllocationInput
    {
        foreach ($type->targets as $documentType => $link) {
            $id = $row->get($link . 'Id');

            if ($id) {
                return new AllocationInput($row->getId(), $documentType, $id, Decimal::of($row->get('amount')));
            }
        }

        throw new \RuntimeException("{$type->allocationEntityType} {$row->getId()} has no document.");
    }

    /**
     * Documents by key ("Invoice:<id>"), each locked FOR UPDATE in the order of the keys (the global lock order);
     * deleted and missing documents are absent from the result.
     *
     * @param list<string> $keys sorted
     * @return array<string, Entity>
     */
    public function lockDocuments(array $keys): array
    {
        $documents = [];

        foreach ($keys as $key) {
            [$entityType, $id] = explode(':', $key, 2);

            $document = $this->entityManager
                ->getRDBRepository($entityType)
                ->where(['id' => $id])
                ->forUpdate()
                ->findOne();

            if ($document) {
                $documents[$key] = $document;
            }
        }

        return $documents;
    }

    /**
     * Documents of the given rows without locks (for reading the table), deleted ones included.
     *
     * @param iterable<AllocationInput> $rows
     * @return array<string, Entity>
     */
    public function findDocuments(iterable $rows): array
    {
        $ids = [];

        foreach ($rows as $row) {
            $ids[$row->targetType][] = $row->targetId;
        }

        $documents = [];

        foreach ($ids as $entityType => $list) {
            $query = SelectBuilder::create()
                ->from($entityType)
                ->select(['id', 'name', 'number'])
                ->withDeleted()
                ->where(['id' => array_values(array_unique($list))])
                ->build();
            $collection = $this->entityManager->getRDBRepository($entityType)->clone($query)->find();

            foreach ($collection as $document) {
                $documents[$entityType . ':' . $document->getId()] = $document;
            }
        }

        return $documents;
    }

    /**
     * One canonical table row.
     *
     * @param array<string, Entity> $documents by key
     */
    public function present(AllocationInput $row, ?string $id, int $order, PaymentType $type, array $documents): stdClass
    {
        $document = $documents[$row->targetKey()] ?? null;
        $item = (object) ['id' => $id, 'order' => $order];

        foreach ($type->targets as $documentType => $link) {
            $own = $documentType === $row->targetType;
            $item->{$link . 'Id'} = $own ? $row->targetId : null;
            $item->{$link . 'Name'} = $own ? $document?->get('name') : null;
        }

        $item->documentNumber = $document?->get('number');
        $item->amount = $row->amount->toFixed(Scale::MONEY);

        return $item;
    }

    /**
     * The canonical table of stored rows.
     *
     * @param array<string, Entity> $rows by id, in order
     * @param array<string, Entity> $documents by key
     * @return list<stdClass>
     */
    public function presentStored(array $rows, PaymentType $type, array $documents): array
    {
        $list = [];
        $order = 0;

        foreach ($rows as $row) {
            $list[] = $this->present($this->toInput($row, $type), $row->getId(), ++$order, $type, $documents);
        }

        return $list;
    }
}
