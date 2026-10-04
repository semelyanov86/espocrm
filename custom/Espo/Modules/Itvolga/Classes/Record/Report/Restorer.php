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
use Espo\ORM\Query\SelectBuilder;
use Espo\ORM\Query\UpdateBuilder;

/**
 * Restores a deleted report as the core does; a report whose folder was removed meanwhile goes to «Общие» (external
 * review W7; the folder is read with a lock, as a report save reads it, D-88), and a shared report whose lists the
 * core cleanup emptied becomes private — its owner keeps it, nobody gets it by accident (review W18).
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
            $this->keepSharingValid($entity);
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

    private function keepSharingValid(Entity $entity): void
    {
        if ($entity->get('accessType') !== Report::ACCESS_SHARED) {
            return;
        }

        foreach (['ReportSharedUser', 'ReportSharedTeam'] as $relation) {
            $query = SelectBuilder::create()
                ->from($relation)
                ->select(['id'])
                ->where(['reportId' => $entity->getId()])
                ->limit(0, 1)
                ->build();

            if ($this->entityManager->getQueryExecutor()->execute($query)->fetchColumn() !== false) {
                return;
            }
        }

        $this->entityManager->getQueryExecutor()->execute(UpdateBuilder::create()
            ->in(Report::ENTITY_TYPE)
            ->set(['accessType' => Report::ACCESS_PRIVATE])
            ->where(['id' => $entity->getId()])
            ->build());
    }
}
