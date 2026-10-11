<?php

namespace Espo\Modules\Itvolga\Tools\Import;

use Espo\ORM\Entity;
use Espo\ORM\EntityManager;
use Espo\ORM\Query\SelectBuilder;

/**
 * Source keys → EspoCRM ids. Imported records by `vtigerId` (unique, kept by soft-deleted rows, D-41); teams and
 * roles (reproduced by `itvolga-setup-acl`, not imported) by name.
 */
class KeyResolver
{
    private const BY_NAME = ['Team', 'Role'];

    /** @var array<string, array<string, string>> */
    private array $ids = [];

    public function __construct(private EntityManager $entityManager) {}

    public function findWithDeleted(string $entityType, int $vtigerId): ?Entity
    {
        $query = SelectBuilder::create()
            ->from($entityType)
            ->where(['vtigerId' => $vtigerId])
            ->withDeleted()
            ->build();

        return $this->entityManager->getRDBRepository($entityType)->clone($query)->findOne();
    }

    /**
     * Id of a live record by its source key, or null.
     */
    public function id(string $entityType, int|string $key): ?string
    {
        $cacheKey = (string) $key;

        if (isset($this->ids[$entityType][$cacheKey])) {
            return $this->ids[$entityType][$cacheKey];
        }

        $where = in_array($entityType, self::BY_NAME, true) ? ['name' => (string) $key] : ['vtigerId' => (int) $key];

        if (!$this->entityManager->hasRepository($entityType)) {
            return null;
        }

        $found = $this->entityManager->getRDBRepository($entityType)->select(['id'])->where($where)->find();

        if (count($found) !== 1) {
            return null; // missing, or an ambiguous team/role name: never a guess
        }

        foreach ($found as $entity) {
            return $this->ids[$entityType][$cacheKey] = $entity->getId();
        }

        return null;
    }

    public function remember(string $entityType, int $vtigerId, string $id): void
    {
        $this->ids[$entityType][(string) $vtigerId] = $id;
    }
}
