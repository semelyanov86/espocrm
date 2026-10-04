<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Api;

use Espo\Core\Acl;
use Espo\Core\Api\Action;
use Espo\Core\Api\Request;
use Espo\Core\Api\Response;
use Espo\Core\Api\ResponseComposer;
use Espo\Core\Exceptions\BadRequest;
use Espo\Core\Exceptions\Forbidden;
use Espo\Core\Exceptions\NotFound;
use Espo\Entities\User;
use Espo\Modules\Itvolga\Entities\ReportMetricSet;
use Espo\Modules\Itvolga\Tools\Report\Core\Metric\MetricRowsParser;
use Espo\Modules\Itvolga\Tools\Report\Metric\MetricSources;
use Espo\ORM\EntityManager;

/**
 * GET /ReportMetricSet/:id/values — the rows of a key-metrics set with their values for the current user (D-112):
 * reads only, in one transaction; a row whose source is closed, removed or no longer fits gets a status instead of a
 * value.
 */
class GetMetricValues implements Action
{
    public function __construct(
        private EntityManager $entityManager,
        private Acl $acl,
        private MetricSources $sources,
        private User $user,
    ) {}

    public function process(Request $request): Response
    {
        $id = $request->getRouteParam('id');

        if (!$id) {
            throw new BadRequest();
        }

        $set = $this->entityManager->getRDBRepositoryByClass(ReportMetricSet::class)->getById($id);

        if (!$set) {
            throw new NotFound();
        }

        if (!$this->acl->checkEntityRead($set)) {
            throw new Forbidden();
        }

        $rows = MetricRowsParser::parse($set->get('rows'));
        $values = $this->entityManager->getTransactionManager()->run(
            fn () => $this->sources->evaluate($rows, $this->user)
        );

        return ResponseComposer::json(['id' => $set->getId(), 'name' => $set->get('name'), 'rows' => $values]);
    }
}
