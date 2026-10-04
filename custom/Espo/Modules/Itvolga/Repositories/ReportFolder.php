<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Repositories;

use Espo\Core\Repositories\CategoryTree;
use Espo\Modules\Itvolga\Entities\ReportFolder as ReportFolderEntity;
use Espo\ORM\Entity;
use Espo\ORM\Query\SelectBuilder;
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

    /**
     * The core cleanup job purges old soft-deleted rows through this method; a standard row (with a seed key) stays,
     * since it is what tells `itvolga-setup-reports` not to bring the record back (D-100, external review B10).
     */
    public function deleteFromDb(string $id, bool $onlyDeleted = false): void
    {
        $query = SelectBuilder::create()
            ->from(ReportFolderEntity::ENTITY_TYPE)
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
