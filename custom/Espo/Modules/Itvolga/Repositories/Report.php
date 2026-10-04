<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Repositories;

use Espo\Core\Repositories\Database;
use Espo\Modules\Itvolga\Entities\Report as ReportEntity;
use Espo\ORM\Entity;

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
}
