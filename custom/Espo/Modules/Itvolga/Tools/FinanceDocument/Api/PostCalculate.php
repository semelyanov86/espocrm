<?php

namespace Espo\Modules\Itvolga\Tools\FinanceDocument\Api;

use Espo\Core\Api\Action;
use Espo\Core\Api\Request;
use Espo\Core\Api\Response;
use Espo\Core\Api\ResponseComposer;
use Espo\Core\Exceptions\BadRequest;
use Espo\Modules\Itvolga\Tools\FinanceDocument\CalculationPreview;
use stdClass;

/**
 * POST /FinanceDocument/:entityType/calculate {id?, attributes} — totals of an unsaved form, nothing is written.
 */
class PostCalculate implements Action
{
    public function __construct(private CalculationPreview $preview) {}

    public function process(Request $request): Response
    {
        $entityType = $request->getRouteParam('entityType');
        $body = $request->getParsedBody();
        $id = $body->id ?? null;
        $attributes = $body->attributes ?? null;

        if (!$entityType || !$attributes instanceof stdClass || ($id !== null && !is_string($id))) {
            throw new BadRequest();
        }

        return ResponseComposer::json($this->preview->preview($entityType, $id, $attributes));
    }
}
