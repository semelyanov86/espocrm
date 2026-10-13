<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Telephony\Api;

use Espo\Core\Api\Action;
use Espo\Core\Api\Request;
use Espo\Core\Api\Response;
use Espo\Core\Api\ResponseComposer;
use Espo\Modules\Itvolga\Tools\Telephony\CardService;

/**
 * GET /Telephony/cards — the call cards of the current user, [{id, data}] as the popup notification manager polls
 * them (app.popupNotifications.itvolgaCall).
 */
class GetCards implements Action
{
    public function __construct(private CardService $service) {}

    public function process(Request $request): Response
    {
        return ResponseComposer::json($this->service->list())->setHeader('Cache-Control', 'no-store');
    }
}
