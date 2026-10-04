<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Api;

use Espo\Core\Acl;
use Espo\Core\Acl\Table;
use Espo\Core\Api\Action;
use Espo\Core\Api\Request;
use Espo\Core\Api\Response;
use Espo\Core\Api\ResponseComposer;
use Espo\Core\Exceptions\Forbidden;
use Espo\Core\Select\SelectBuilderFactory;
use Espo\Modules\Itvolga\Entities\Report;
use Espo\ORM\EntityManager;
use PDO;

/**
 * GET /Report/folderCounts — number of reports per folder that the current user may read (the counters of the folder
 * panel of the list, D-88): {"total": n, "folders": {"<folderId>": n}}.
 */
class GetFolderCounts implements Action
{
    public function __construct(
        private Acl $acl,
        private SelectBuilderFactory $selectBuilderFactory,
        private EntityManager $entityManager,
    ) {}

    public function process(Request $request): Response
    {
        if (!$this->acl->checkScope(Report::ENTITY_TYPE, Table::ACTION_READ)) {
            throw new Forbidden();
        }

        $query = $this->selectBuilderFactory->create()
            ->from(Report::ENTITY_TYPE)
            ->withAccessControlFilter()
            ->buildQueryBuilder()
            ->select([['folderId', 'folderId'], ['COUNT:(id)', 'n']])
            ->group(['folderId'])
            ->order([])
            ->build();

        $folders = [];
        $total = 0;

        foreach ($this->entityManager->getQueryExecutor()->execute($query)->fetchAll(PDO::FETCH_ASSOC) as $row) {
            $total += (int) $row['n'];

            if ($row['folderId'] !== null) {
                $folders[$row['folderId']] = (int) $row['n'];
            }
        }

        return ResponseComposer::json(['total' => $total, 'folders' => (object) $folders]);
    }
}
