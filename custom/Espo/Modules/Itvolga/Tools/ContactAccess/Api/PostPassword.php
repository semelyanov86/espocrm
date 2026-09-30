<?php

namespace Espo\Modules\Itvolga\Tools\ContactAccess\Api;

use Espo\Core\Api\Action;
use Espo\Core\Api\Request;
use Espo\Core\Api\Response;
use Espo\Core\Api\ResponseComposer;
use Espo\Core\Exceptions\BadRequest;
use Espo\Modules\Itvolga\Tools\ContactAccess\PasswordService;

/**
 * POST /ContactAccess/:id/password — reveals the AnyDesk password (logged). POST so that the value is never
 * cached or prefetched; the response forbids caching.
 */
class PostPassword implements Action
{
    public function __construct(private PasswordService $service) {}

    public function process(Request $request): Response
    {
        $id = $request->getRouteParam('id');

        if (!$id) {
            throw new BadRequest();
        }

        return ResponseComposer::json(['password' => $this->service->reveal($id)])
            ->setHeader('Cache-Control', 'no-store')
            ->setHeader('Pragma', 'no-cache');
    }
}
