<?php

namespace Espo\Modules\Itvolga\Tools\Import;

use Espo\ORM\Entity;
use Espo\ORM\EntityManager;
use Espo\ORM\Query\SelectBuilder;

/**
 * Source keys → EspoCRM ids. Imported records by `vtigerId` (unique, kept by soft-deleted rows, D-41); records without
 * a Vtiger id by an allowlisted natural key (stage 06.3): the single legal entity by `vtigerCompanyKey`, the knowledge
 * base category of the FAQ by name; teams and roles (reproduced by `itvolga-setup-acl`, not imported) by name.
 */
class KeyResolver
{
    /** Entity type => the attribute that identifies a record of it (default: vtigerId). */
    public const NATURAL_KEYS = ['LegalEntity' => 'vtigerCompanyKey', 'KnowledgeBaseCategory' => 'name',
        'Team' => 'name', 'Role' => 'name'];

    /**
     * One cache per writer process: the injectable factory gives every dependent its own instance, and a removal or
     * a type change must reach all of them (stage 06.4).
     *
     * @var array<string, array<string, string>>
     */
    private static array $ids = [];

    public function __construct(private EntityManager $entityManager) {}

    public function keyAttribute(string $entityType): string
    {
        return self::NATURAL_KEYS[$entityType] ?? 'vtigerId';
    }

    public function findWithDeleted(string $entityType, int|string $key): ?Entity
    {
        $query = SelectBuilder::create()
            ->from($entityType)
            ->where([$this->keyAttribute($entityType) => $this->typed($entityType, $key)])
            ->withDeleted()
            ->order('id', 'DESC')
            ->build();
        $repository = $this->entityManager->getRDBRepository($entityType);

        if (!isset(self::NATURAL_KEYS[$entityType])) {
            return $repository->clone($query)->findOne(); // vtigerId is unique with the deleted rows (D-41)
        }

        // A name may repeat: the single live record; with none live, the latest deleted one (restored); more than
        // one live — never a guess (id() refuses them as well).
        $found = iterator_to_array($repository->clone($query)->find(), false);
        $live = array_values(array_filter($found, static fn (Entity $entity) => !$entity->get('deleted')));

        if (count($live) > 1) {
            throw new ImportError('ambiguous_key');
        }

        return $live[0] ?? $found[0] ?? null;
    }

    /**
     * Id of a live record by its source key, or null.
     */
    public function id(string $entityType, int|string $key): ?string
    {
        $cacheKey = (string) $key;

        if (isset(self::$ids[$entityType][$cacheKey])) {
            return self::$ids[$entityType][$cacheKey];
        }

        if (!$this->entityManager->hasRepository($entityType)) {
            return null;
        }

        $found = $this->entityManager->getRDBRepository($entityType)->select(['id'])
            ->where([$this->keyAttribute($entityType) => $this->typed($entityType, $key)])->find();

        if (count($found) !== 1) {
            return null; // missing, or an ambiguous natural key: never a guess
        }

        foreach ($found as $entity) {
            return self::$ids[$entityType][$cacheKey] = $entity->getId();
        }

        return null;
    }

    /**
     * The source record was imported and then deleted in EspoCRM (no live record with the key, a deleted one exists).
     */
    public function isDeleted(string $entityType, int|string $key): bool
    {
        if (!$this->entityManager->hasRepository($entityType) || $this->id($entityType, $key)) {
            return false;
        }

        return (bool) $this->findWithDeleted($entityType, $key)?->get('deleted');
    }

    /**
     * Called after the transaction of the write committed: a rolled-back insert never enters the cache.
     */
    public function remember(string $entityType, int|string $key, string $id): void
    {
        self::$ids[$entityType][(string) $key] = $id;
    }

    /**
     * A removed record (or the previous type of a retyped activity) is no longer an id of its key.
     */
    public function forget(string $entityType, int|string $key): void
    {
        unset(self::$ids[$entityType][(string) $key]);
    }

    /**
     * After a removal (cascades may delete records whose keys the caller does not know) or a failed transaction (an id
     * seen inside it may have been rolled back).
     */
    public function reset(): void
    {
        self::$ids = [];
    }

    private function typed(string $entityType, int|string $key): int|string
    {
        return isset(self::NATURAL_KEYS[$entityType]) ? (string) $key : (int) $key;
    }
}
