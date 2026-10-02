<?php

namespace Espo\Modules\Itvolga\Tools\FinanceDocument\Api;

use Espo\Core\Api\Action;
use Espo\Core\Api\Request;
use Espo\Core\Api\Response;
use Espo\Core\Api\ResponseComposer;
use Espo\Core\Exceptions\BadRequest;
use Espo\Modules\Itvolga\Tools\FinanceDocument\DocumentConverter;

/**
 * GET /FinanceDocument/:entityType/:id/convertTo/:targetEntityType — attributes of a prefilled new document.
 */
class GetConvert implements Action
{
    public function __construct(private DocumentConverter $converter) {}

    public function process(Request $request): Response
    {
        $from = $request->getRouteParam('entityType');
        $id = $request->getRouteParam('id');
        $to = $request->getRouteParam('targetEntityType');

        if (!$from || !$id || !$to) {
            throw new BadRequest();
        }

        return ResponseComposer::json($this->converter->attributes($from, $id, $to));
    }
}
