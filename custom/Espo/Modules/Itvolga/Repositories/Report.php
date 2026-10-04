<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Repositories;

use Espo\Core\Repositories\Database;
use Espo\Modules\Itvolga\Entities\Report as ReportEntity;
use Espo\ORM\Entity;
use Espo\ORM\Query\SelectBuilder;

/**
 * Reports. A save runs in one transaction, so the lock that the definition hook takes on the report's folder is held
 * until the report is stored: a folder being removed is either seen with this report (and kept, 409) or seen gone
 * by this save (400 folderNotFound) — D-88. Covers every path: API, mass update, seed.
 *
 * @extends Database<ReportEntity>
 */
class Report extends Database
{
    public function save(Entity $entity, array $options = []): void
    {
        $this->entityManager
            ->getTransactionManager()
            ->run(fn () => parent::save($entity, $options));
    }

    /**
     * The core cleanup job purges old soft-deleted rows through this method; a standard row (with a seed key) stays,
     * since it is what tells `itvolga-setup-reports` not to bring the record back (D-100, external review B10).
     */
    public function deleteFromDb(string $id, bool $onlyDeleted = false): void
    {
        $query = SelectBuilder::create()
            ->from(ReportEntity::ENTITY_TYPE)
            ->select(['seedKey'])
            ->where(['id' => $id])
            ->withDeleted()
            ->build();
        $seedKey = $this->entityManager->getQueryExecutor()->execute($query)->fetchColumn();

        if (is_string($seedKey) && $seedKey !== '') {
            return;
        }

        parent::deleteFromDb($id, $onlyDeleted);
    }
}
