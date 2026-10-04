<?php

namespace Espo\Modules\Itvolga\Services;

use Espo\Core\Record\DeleteParams;
use Espo\Core\Record\DeleteResult;
use Espo\Modules\Itvolga\Hooks\ReportFolder\Guard;
use Espo\ORM\Entity;
use Espo\Services\RecordTree;

/**
 * Record service of report folders: the folder rules of the module (D-88: system folder, folder holding reports of any
 * owner) answer before the core check of the category tree, which sees only the reports the user may read.
 *
 * @extends RecordTree<\Espo\Modules\Itvolga\Entities\ReportFolder>
 */
class ReportFolder extends RecordTree
{
    protected function beforeDeleteEntity(Entity $entity): void
    {
        $this->injectableFactory->create(Guard::class)->assertRemovable($entity);

        parent::beforeDeleteEntity($entity);
    }

    /**
     * Removal in one transaction: the folder row stays locked from the check to the delete, so a report save that
     * locks the folder (Hooks/Report/Definition) waits and then sees the folder gone.
     */
    public function delete(string $id, DeleteParams $params = new DeleteParams()): DeleteResult
    {
        return $this->entityManager->getTransactionManager()->run(fn () => parent::delete($id, $params));
    }
}
