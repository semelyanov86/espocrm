<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Hooks\ReportFolder;

use Espo\Core\Exceptions\Conflict;
use Espo\Core\Exceptions\Error\Body;
use Espo\Core\Exceptions\Forbidden;
use Espo\Core\Hook\Hook\BeforeRemove;
use Espo\Core\Hook\Hook\BeforeSave;
use Espo\Modules\Itvolga\Entities\Report;
use Espo\Modules\Itvolga\Entities\ReportFolder;
use Espo\Modules\Itvolga\Tools\FinanceDocument\RowLock;
use Espo\ORM\Entity;
use Espo\ORM\EntityManager;
use Espo\ORM\Repository\Option\RemoveOptions;
use Espo\ORM\Repository\Option\SaveOptions;

/**
 * Report folders (D-88): flat (no parent), names unique among live folders (case-insensitive), the system folder
 * «Общие» is never removed, a folder holding reports is not removed (move or delete them first; reports of any owner
 * count, the check runs under a lock of the folder row so a report cannot be moved in meanwhile).
 *
 * @implements BeforeSave<ReportFolder>
 * @implements BeforeRemove<ReportFolder>
 */
class Guard implements BeforeSave, BeforeRemove
{
    public function __construct(
        private EntityManager $entityManager,
        private RowLock $rowLock,
    ) {}

    public function beforeSave(Entity $entity, SaveOptions $options): void
    {
        if ($entity->get('parentId') !== null) {
            $entity->set('parentId', null);
        }

        $name = trim((string) $entity->get('name'));
        $entity->set('name', $name);

        $same = $this->entityManager->getRDBRepositoryByClass(ReportFolder::class)
            ->where(['LOWER:(name)' => mb_strtolower($name), 'id!=' => $entity->getId() ?? ''])
            ->findOne();

        if ($same) {
            throw Conflict::createWithBody('folderNameExists',
                Body::create()->withMessageTranslation('folderNameExists', 'ReportFolder', ['name' => $name]));
        }
    }

    public function beforeRemove(Entity $entity, RemoveOptions $options): void
    {
        $this->assertRemovable($entity);
    }

    /**
     * Also called by the record service before the core tree check (which counts only the reports the user sees and
     * answers with its own message): the system folder — 403 `folderSystem`, a folder holding any report — 409.
     */
    public function assertRemovable(Entity $entity): void
    {
        if ($entity->get('isSystem')) {
            throw Forbidden::createWithBody('folderSystem',
                Body::create()->withMessageTranslation('folderSystem', 'ReportFolder'));
        }

        $this->rowLock->one(ReportFolder::ENTITY_TYPE, $entity->getId());

        $count = $this->entityManager->getRDBRepositoryByClass(Report::class)
            ->where(['folderId' => $entity->getId()])
            ->count();

        if ($count > 0) {
            throw Conflict::createWithBody('folderNotEmpty',
                Body::create()->withMessageTranslation('folderNotEmpty', 'ReportFolder', ['count' => (string) $count]));
        }
    }
}
