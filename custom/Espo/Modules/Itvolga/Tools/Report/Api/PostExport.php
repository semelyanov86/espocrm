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
 * POST /Report/:id/export {format: csv|xlsx|pdf, variant?: report|all, background?, filters?, quickFilters?} — a file
 * of the result for the current user (reports.md §12): {id, name, type} of the attachment to download with
 * ?entryPoint=download, or {scheduled: true} for a background export (the file comes by e-mail and a notification).
 */
class PostExport implements Action
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
            return ResponseComposer::json($this->service->export($id, $raw, $this->user));
        } catch (DefinitionError $e) {
            throw ErrorMapper::toHttp($e);
        }
    }
}
