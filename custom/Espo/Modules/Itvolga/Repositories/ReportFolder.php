<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Repositories;

use Espo\Core\Repositories\CategoryTree;
use Espo\Modules\Itvolga\Entities\ReportFolder as ReportFolderEntity;
use Espo\ORM\Entity;
use Espo\ORM\Query\InsertBuilder;

/**
 * Report folders. The core category tree deletes a removed folder physically; a removed standard folder (one with a
 * seed key) leaves a soft-deleted row behind, so `itvolga-setup-reports` knows it was deleted and does not bring it
 * back (D-100), like a deleted standard report.
 *
 * @extends CategoryTree<ReportFolderEntity>
 */
class ReportFolder extends CategoryTree
{
    protected function afterRemove(Entity $entity, array $options = [])
    {
        parent::afterRemove($entity, $options);

        $seedKey = $entity->get('seedKey');

        if (!is_string($seedKey) || $seedKey === '') {
            return;
        }

        $this->entityManager->getQueryExecutor()->execute(InsertBuilder::create()
            ->into(ReportFolderEntity::ENTITY_TYPE)
            ->columns(['id', 'name', 'seedKey', 'deleted'])
            ->values(['id' => $entity->getId(), 'name' => $entity->get('name'), 'seedKey' => $seedKey,
                'deleted' => true])
            ->build());
    }
}
