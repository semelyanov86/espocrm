<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Classes\Record\Report;

use Espo\Core\Record\Deleted\DefaultRestorer;
use Espo\Core\Record\Deleted\Restorer as RestorerInterface;
use Espo\Modules\Itvolga\Entities\Report;
use Espo\Modules\Itvolga\Entities\ReportFolder;
use Espo\Modules\Itvolga\Tools\FinanceDocument\RowLock;
use Espo\ORM\Entity;
use Espo\ORM\EntityManager;
use Espo\ORM\Query\UpdateBuilder;

/**
 * Restores a deleted report as the core does; a report whose folder was removed meanwhile goes to «Общие» (external
 * review W7). The folder is read with a lock, as a report save reads it (D-88).
 *
 * @implements RestorerInterface<Entity>
 */
final class Restorer implements RestorerInterface
{
    public function __construct(
        private DefaultRestorer $defaultRestorer,
        private EntityManager $entityManager,
        private RowLock $rowLock,
    ) {}

    public function restore(Entity $entity): void
    {
        $this->entityManager->getTransactionManager()->run(function () use ($entity): void {
            $this->defaultRestorer->restore($entity);
            $folderId = $entity->get('folderId');

            if ($folderId === null || $this->rowLock->one(ReportFolder::ENTITY_TYPE, (string) $folderId)) {
                return;
            }

            $general = $this->entityManager->getRDBRepositoryByClass(ReportFolder::class)
                ->where(['isSystem' => true])
                ->findOne();

            $this->entityManager->getQueryExecutor()->execute(UpdateBuilder::create()
                ->in(Report::ENTITY_TYPE)
                ->set(['folderId' => $general?->getId()])
                ->where(['id' => $entity->getId()])
                ->build());
        });
    }
}
