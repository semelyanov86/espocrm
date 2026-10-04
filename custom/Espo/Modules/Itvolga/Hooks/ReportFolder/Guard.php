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
use PDO;
use Espo\ORM\Entity;
use Espo\ORM\EntityManager;
use Espo\ORM\Query\SelectBuilder;
use Espo\ORM\Repository\Option\RemoveOptions;
use Espo\ORM\Repository\Option\SaveOptions;

/**
 * Report folders (D-88): flat (no parent), names unique among live folders (case-insensitive), the system folder
 * «Общие» is never removed, a folder holding reports is not removed (move or delete them first; reports of any owner
 * count). Both checks are current (locking) reads inside the save or delete transaction: a plain read could use the
 * transaction's older REPEATABLE READ snapshot. Name checks are serialised on the system folder row; the emptiness
 * check runs under the lock of the folder row, which a report save also takes (Repositories\Report).
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

        $this->lockedIds(['isSystem' => true]);
        $same = $this->lockedIds(['LOWER:(name)' => mb_strtolower($name), 'id!=' => $entity->getId() ?? ''], 1);

        if ($same !== []) {
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

        $count = count($this->lockedIds(['folderId' => $entity->getId()], null, Report::ENTITY_TYPE));

        if ($count > 0) {
            throw Conflict::createWithBody('folderNotEmpty',
                Body::create()->withMessageTranslation('folderNotEmpty', 'ReportFolder', ['count' => (string) $count]));
        }
    }

    /**
     * Ids of live records matching $where, read and locked with SELECT … FOR UPDATE (the latest committed rows).
     *
     * @param array<string|int, mixed> $where
     * @return list<string>
     */
    private function lockedIds(array $where, ?int $limit = null, string $entityType = ReportFolder::ENTITY_TYPE): array
    {
        $builder = SelectBuilder::create()
            ->from($entityType)
            ->select(['id'])
            ->where($where)
            ->forUpdate();

        if ($limit !== null) {
            $builder->limit(0, $limit);
        }

        return array_map('strval', $this->entityManager->getQueryExecutor()->execute($builder->build())
            ->fetchAll(PDO::FETCH_COLUMN));
    }
}
