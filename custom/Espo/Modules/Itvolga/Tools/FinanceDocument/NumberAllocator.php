<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\FinanceDocument;

use Espo\Core\Exceptions\Error;
use Espo\Entities\NextNumber;
use Espo\ORM\EntityManager;

/**
 * Numbers of records created in EspoCRM: prefix + counter without padding (ПРЕД_25, ЗАКАЗ_15, payments without a
 * prefix; owner decisions 2026-10-01, 2026-10-02). The counter is the core NextNumber row (entityType, fieldName
 * "number"), locked inside the record's transaction, so concurrent saves never share a number and a failed save leaves
 * no gap. A number already taken (an imported one, D-17) is skipped. The core `number` field type is not used: it
 * forces varchar(36), the contract keeps varchar(100) for original numbers.
 */
class NumberAllocator
{
    public const FIELD = 'number';
    private const MAX_SKIP = 1000;

    public function __construct(private EntityManager $entityManager) {}

    /**
     * Must run inside the record's transaction (entityDefs transactionalSave).
     *
     * @throws Error when the counter is not configured (itvolga-setup-finance) — never created on the fly, so two
     *   concurrent first saves cannot create two counters
     */
    public function allocate(NumberSeries $series): string
    {
        $counter = $this->lockCounter($series)
            ?? throw new Error("Numbering of {$series->entityType} is not configured: run itvolga-setup-finance.");

        $value = max((int) $counter->getNumberValue(), 1);

        for ($i = 0; $i < self::MAX_SKIP; $i++, $value++) {
            $number = $series->prefix . $value;

            if (!$this->isTaken($series->entityType, $number)) {
                $counter->setNumberValue($value + 1);
                $this->entityManager->saveEntity($counter);

                return $number;
            }
        }

        throw new Error("No free number for {$series->entityType} near the counter value.");
    }

    /**
     * Locks the counter row for the rest of the transaction without taking a number. Payments use it as their ledger
     * lock: every write that changes allocations or settlement takes it first (Tools/FinancePayment).
     *
     * @return bool false when the counter is not configured
     */
    public function lock(NumberSeries $series): bool
    {
        return $this->lockCounter($series) !== null;
    }

    /**
     * Creates the counter or raises it to $next; never lowers it. Must run inside a transaction: the counter row is
     * locked as allocate() locks it, so a concurrent allocation can neither be overwritten nor overtaken.
     *
     * @return ?string what changed, null when nothing did
     */
    public function ensure(NumberSeries $series, ?int $next = null): ?string
    {
        $repository = $this->entityManager->getRDBRepositoryByClass(NextNumber::class);
        $counters = [...$repository
            ->where(['entityType' => $series->entityType, 'fieldName' => self::FIELD])
            ->forUpdate()
            ->find()];

        if (count($counters) > 1) {
            throw new Error("Several NextNumber rows for {$series->entityType}.number: fix them before numbering.");
        }

        $target = max($series->firstNumber, $next ?? 0);
        $counter = $counters[0] ?? null;

        if (!$counter) {
            $counter = $repository->getNew();
            $counter
                ->setTargetEntityType($series->entityType)
                ->setTargetFieldName(self::FIELD)
                ->setNumberValue($target);
            $this->entityManager->saveEntity($counter);

            return "counter + {$series->entityType}: $target";
        }

        if ($next !== null && $next > (int) $counter->getNumberValue()) {
            $counter->setNumberValue($next);
            $this->entityManager->saveEntity($counter);

            return "counter ~ {$series->entityType}: $next";
        }

        return null;
    }

    public function current(NumberSeries $series): ?int
    {
        $counter = $this->entityManager
            ->getRDBRepositoryByClass(NextNumber::class)
            ->where(['entityType' => $series->entityType, 'fieldName' => self::FIELD])
            ->findOne();

        return $counter?->getNumberValue();
    }

    private function lockCounter(NumberSeries $series): ?NextNumber
    {
        return $this->entityManager
            ->getRDBRepositoryByClass(NextNumber::class)
            ->where(['entityType' => $series->entityType, 'fieldName' => self::FIELD])
            ->forUpdate()
            ->findOne();
    }

    private function isTaken(string $entityType, string $number): bool
    {
        // Deleted documents keep their numbers: a number is never given twice.
        $query = $this->entityManager
            ->getQueryBuilder()
            ->select(['id'])
            ->from($entityType)
            ->withDeleted()
            ->where([self::FIELD => $number])
            ->limit(0, 1)
            ->build();

        return (bool) $this->entityManager->getQueryExecutor()->execute($query)->fetch();
    }
}
