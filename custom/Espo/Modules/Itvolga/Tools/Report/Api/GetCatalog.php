<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Api;

use Espo\Core\Api\Action;
use Espo\Core\Api\Request;
use Espo\Core\Api\Response;
use Espo\Core\Api\ResponseComposer;
use Espo\Core\Exceptions\Forbidden;
use Espo\Entities\User;
use Espo\Modules\Itvolga\Tools\Report\Catalog;

/**
 * GET /Report/catalog — entity types the user may report on; GET /Report/catalog/:entityType — their fields and the
 * fields of linked entities with what a report may do with each (the builder offers exactly what the server accepts).
 */
class GetCatalog implements Action
{
    public function __construct(
        private Catalog $catalog,
        private User $user,
    ) {}

    public function process(Request $request): Response
    {
        $entityType = $request->getRouteParam('entityType');

        if ($entityType === null) {
            return ResponseComposer::json(['list' => $this->catalog->entityTypes($this->user)]);
        }

        if (!in_array($entityType, array_column($this->catalog->entityTypes($this->user), 'entityType'), true)) {
            throw new Forbidden();
        }

        return ResponseComposer::json($this->catalog->fields($entityType, $this->user));
    }
}
