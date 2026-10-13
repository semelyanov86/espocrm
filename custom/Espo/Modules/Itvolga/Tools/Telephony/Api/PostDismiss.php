<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Telephony\Api;

use Espo\Core\Api\Action;
use Espo\Core\Api\Request;
use Espo\Core\Api\Response;
use Espo\Core\Api\ResponseComposer;
use Espo\Core\Exceptions\BadRequest;
use Espo\Modules\Itvolga\Tools\Telephony\CardService;

/**
 * POST /Telephony/cards/:id/dismiss — the user closed the card (all tabs, all devices).
 */
class PostDismiss implements Action
{
    public function __construct(private CardService $service) {}

    public function process(Request $request): Response
    {
        $id = $request->getRouteParam('id');

        if (!$id) {
            throw new BadRequest();
        }

        $this->service->dismiss($id);

        return ResponseComposer::json(true);
    }
}
