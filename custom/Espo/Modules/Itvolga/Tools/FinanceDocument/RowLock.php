<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\FinanceDocument;

use Espo\ORM\Defs\AttributeDefs;
use Espo\ORM\Entity;
use Espo\ORM\EntityManager;
use Espo\ORM\Repository\RDBSelectBuilder;
use Espo\ORM\Type\AttributeType;

/**
 * Locking reads of finance records that lock the record's own row only. `SELECT … FOR UPDATE` of a full entity also
 * locks the row of every belongs-to link joined to load its name — the account, the contact, the users, the act of an
 * invoice and the single legal entity of every document and payment: unrelated saves queue on those rows, and saves
 * that lock records in different orders deadlock (a payment holding the legal entity through one invoice waits for
 * another invoice whose save waits for the legal entity; found by the stage 04.5 review, confirmed on the stand). The
 * own attributes — storable and not foreign (a foreign field such as PaymentAllocation.paymentStatus is storable but
 * joined) — are all the save paths read from a locked record; link-multiple ids (teams) load on demand.
 */
class RowLock
{
    /** @var array<string, list<string>> */
    private array $attributes = [];

    public function __construct(private EntityManager $entityManager) {}

    public function one(string $entityType, string $id): ?Entity
    {
        return $this->query($entityType)->where(['id' => $id])->findOne();
    }

    /**
     * A locking select of the own attributes; the caller adds the conditions and the order.
     *
     * @return RDBSelectBuilder<Entity>
     */
    public function query(string $entityType): RDBSelectBuilder
    {
        return $this->entityManager
            ->getRDBRepository($entityType)
            ->select($this->attributes($entityType))
            ->forUpdate();
    }

    /**
     * @return list<string>
     */
    private function attributes(string $entityType): array
    {
        return $this->attributes[$entityType] ??= array_values(array_map(
            static fn (AttributeDefs $defs) => $defs->getName(),
            array_filter(
                $this->entityManager->getDefs()->getEntity($entityType)->getAttributeList(),
                static fn (AttributeDefs $defs) => !$defs->isNotStorable() &&
                    $defs->getType() !== AttributeType::FOREIGN,
            ),
        ));
    }
}
