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
use Espo\Modules\Itvolga\Tools\Report\Export\ExportService;

/**
 * POST /Report/:id/printView {variant?, filters?, quickFilters?} — the print view of the result for the current user
 * (reports.md §12): {title, orientation, html}, a complete HTML document of the table as on the screen, without
 * scripts. The same rights as an export (D-119).
 */
class PostPrintView implements Action
{
    public function __construct(
        private ExportService $service,
        private User $user,
    ) {}

    public function process(Request $request): Response
    {
        $id = $request->getRouteParam('id');
        $raw = json_decode(Json::encode($request->getParsedBody()), true);

        if (!$id || !is_array($raw)) {
            throw new BadRequest();
        }

        try {
            return ResponseComposer::json($this->service->printView($id, $raw, $this->user));
        } catch (DefinitionError $e) {
            throw ErrorMapper::toHttp($e);
        }
    }
}
