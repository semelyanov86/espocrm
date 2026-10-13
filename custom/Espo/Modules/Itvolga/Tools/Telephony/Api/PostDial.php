<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Telephony\Api;

use Espo\Core\Api\Action;
use Espo\Core\Api\Request;
use Espo\Core\Api\Response;
use Espo\Core\Api\ResponseComposer;
use Espo\Core\Exceptions\BadRequest;
use Espo\Modules\Itvolga\Tools\Telephony\DialService;

/**
 * POST /Telephony/dial {phoneNumber, entityType?, entityId?} — click-to-call from a phone number of a record.
 */
class PostDial implements Action
{
    public function __construct(private DialService $service) {}

    public function process(Request $request): Response
    {
        $body = $request->getParsedBody();
        $number = $body->phoneNumber ?? null;
        $entityType = $body->entityType ?? null;
        $entityId = $body->entityId ?? null;

        if (!is_string($number) || $number === '' || strlen($number) > 100
            || ($entityType !== null && !is_string($entityType)) || ($entityId !== null && !is_string($entityId))) {
            throw new BadRequest();
        }

        return ResponseComposer::json($this->service->dial($number, $entityType, $entityId))
            ->setHeader('Cache-Control', 'no-store');
    }
}
