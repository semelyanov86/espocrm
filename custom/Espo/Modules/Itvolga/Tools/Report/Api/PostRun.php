<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Api;

use Espo\Core\Api\Action;
use Espo\Core\Api\Request;
use Espo\Core\Api\Response;
use Espo\Core\Api\ResponseComposer;
use Espo\Core\Exceptions\BadRequest;
use Espo\Core\Utils\Json;
use Espo\Entities\User;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\DefinitionError;
use Espo\Modules\Itvolga\Tools\Report\ErrorMapper;
use Espo\Modules\Itvolga\Tools\Report\Run\ReportRunner;
use Espo\ORM\EntityManager;

/**
 * POST /Report/:id/run {offset?, maxSize?, filters?, quickFilters?, noLimit?, withQuickFilterOptions?} — the result of
 * a report for the current user (reports.md §6). Reads only, in one transaction, so all queries see the same data.
 */
class PostRun implements Action
{
    public function __construct(
        private ReportRunner $runner,
        private User $user,
        private EntityManager $entityManager,
    ) {}

    public function process(Request $request): Response
    {
        $id = $request->getRouteParam('id');

        if (!$id) {
            throw new BadRequest();
        }

        $raw = json_decode(Json::encode($request->getParsedBody()), true);

        if (!is_array($raw)) {
            throw new BadRequest();
        }

        $report = $this->runner->loadReadable($id, $this->user);

        try {
            $result = $this->entityManager->getTransactionManager()->run(
                fn () => $this->runner->run($report, $raw, $this->user)
            );
        } catch (DefinitionError $e) {
            throw ErrorMapper::toHttp($e);
        }

        return ResponseComposer::json($result);
    }
}
