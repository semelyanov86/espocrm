<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Repositories;

use Espo\Core\Exceptions\Conflict;
use Espo\Core\Exceptions\Error\Body;
use Espo\Core\Repositories\Database;
use Espo\Modules\Itvolga\Entities\ReportMetricSet as SetEntity;
use Espo\ORM\Entity;
use PDOException;

/**
 * Key-metrics sets (D-111). A save runs in one transaction, so the row lock and the checks of the hook hold until the
 * set is stored. Names are unique among live sets by the unique index (name, deleteId) of the core's deleteId scheme;
 * a save that loses the race with another one of the same name gets the same 409 as the hook's own check.
 *
 * @extends Database<SetEntity>
 */
class ReportMetricSet extends Database
{
    public function save(Entity $entity, array $options = []): void
    {
        try {
            $this->entityManager
                ->getTransactionManager()
                ->run(fn () => parent::save($entity, $options));
        } catch (PDOException $e) {
            if ((string) $e->getCode() !== '23000') {
                throw $e;
            }

            throw Conflict::createWithBody('metricSetNameExists',
                Body::create()->withMessageTranslation('metricSetNameExists', 'Report'));
        }
    }
}
