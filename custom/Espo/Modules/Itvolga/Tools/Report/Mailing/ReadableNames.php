<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Mailing;

use Espo\Core\AclManager;
use Espo\Core\Select\SelectBuilderFactory;
use Espo\Entities\User;
use Espo\ORM\EntityManager;
use PDO;
use Throwable;

/**
 * Names of records as one user may see them (D-124): only records the access filter of the core gives him and only when
 * the name field of the entity is not closed to him at the field level — in letters (the owner, records of conditions)
 * and in the mailing settings of a report (chosen users and teams). Others are left out; callers show «(нет доступа)».
 */
final class ReadableNames
{
    public function __construct(
        private readonly SelectBuilderFactory $selectBuilderFactory,
        private readonly EntityManager $entityManager,
        private readonly AclManager $aclManager,
    ) {}

    /**
     * @param list<string> $ids
     * @return array<string, string> id → name
     */
    public function of(User $reader, string $entityType, array $ids): array
    {
        if ($ids === [] || !$this->entityManager->hasRepository($entityType) ||
            in_array('name', $this->aclManager->getScopeForbiddenFieldList($reader, $entityType), true)) {
            return [];
        }

        try {
            $query = $this->selectBuilderFactory
                ->create()
                ->from($entityType)
                ->forUser($reader)
                ->withStrictAccessControl()
                ->buildQueryBuilder()
                ->select(['id', 'name'])
                ->where(['id' => array_values(array_unique($ids))])
                ->order([])
                ->build();

            $names = [];

            foreach ($this->entityManager->getQueryExecutor()->execute($query)->fetchAll(PDO::FETCH_ASSOC) as $row) {
                $names[(string) $row['id']] = (string) $row['name'];
            }

            return $names;
        } catch (Throwable) {
            // No access to the entity at all: no names.
            return [];
        }
    }
}
