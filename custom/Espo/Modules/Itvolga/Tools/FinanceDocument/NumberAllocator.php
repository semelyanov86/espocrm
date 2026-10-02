<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\FinanceDocument;

use Espo\Core\Exceptions\Error;
use Espo\Entities\NextNumber;
use Espo\ORM\EntityManager;

/**
 * Numbers of documents created in EspoCRM: prefix + counter without padding (ПРЕД_25, ЗАКАЗ_15; owner decision
 * 2026-10-01). The counter is the core NextNumber row (entityType, fieldName "number"), locked inside the document's
 * transaction, so concurrent saves never share a number and a failed save leaves no gap. A number already taken
 * (an imported one, D-17) is skipped. The core `number` field type is not used: it forces varchar(36), the contract
 * keeps varchar(100) for original numbers.
 */
class NumberAllocator
{
    public const FIELD = 'number';
    private const MAX_SKIP = 1000;

    public function __construct(private EntityManager $entityManager) {}

    /**
     * Must run inside the document's transaction (entityDefs transactionalSave).
     *
     * @throws Error when the counter is not configured (itvolga-setup-finance) — never created on the fly, so two
     *   concurrent first saves cannot create two counters
     */
    public function allocate(DocumentType $type): string
    {
        $counter = $this->entityManager
            ->getRDBRepositoryByClass(NextNumber::class)
            ->where(['entityType' => $type->entityType, 'fieldName' => self::FIELD])
            ->forUpdate()
            ->findOne();

        if (!$counter) {
            throw new Error("Numbering of {$type->entityType} is not configured: run itvolga-setup-finance.");
        }

        $value = max((int) $counter->getNumberValue(), 1);

        for ($i = 0; $i < self::MAX_SKIP; $i++, $value++) {
            $number = $type->numberPrefix . $value;

            if (!$this->isTaken($type->entityType, $number)) {
                $counter->setNumberValue($value + 1);
                $this->entityManager->saveEntity($counter);

                return $number;
            }
        }

        throw new Error("No free number for {$type->entityType} near the counter value.");
    }

    /**
     * Creates the counter or raises it to $next; never lowers it. Must run inside a transaction: the counter row is
     * locked as allocate() locks it, so a concurrent allocation can neither be overwritten nor overtaken.
     *
     * @return ?string what changed, null when nothing did
     */
    public function ensure(DocumentType $type, ?int $next = null): ?string
    {
        $repository = $this->entityManager->getRDBRepositoryByClass(NextNumber::class);
        $counters = [...$repository
            ->where(['entityType' => $type->entityType, 'fieldName' => self::FIELD])
            ->forUpdate()
            ->find()];

        if (count($counters) > 1) {
            throw new Error("Several NextNumber rows for {$type->entityType}.number: fix them before numbering.");
        }

        $target = max($type->firstNumber, $next ?? 0);
        $counter = $counters[0] ?? null;

        if (!$counter) {
            $counter = $repository->getNew();
            $counter
                ->setTargetEntityType($type->entityType)
                ->setTargetFieldName(self::FIELD)
                ->setNumberValue($target);
            $this->entityManager->saveEntity($counter);

            return "counter + {$type->entityType}: $target";
        }

        if ($next !== null && $next > (int) $counter->getNumberValue()) {
            $counter->setNumberValue($next);
            $this->entityManager->saveEntity($counter);

            return "counter ~ {$type->entityType}: $next";
        }

        return null;
    }

    public function current(DocumentType $type): ?int
    {
        $counter = $this->entityManager
            ->getRDBRepositoryByClass(NextNumber::class)
            ->where(['entityType' => $type->entityType, 'fieldName' => self::FIELD])
            ->findOne();

        return $counter?->getNumberValue();
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
