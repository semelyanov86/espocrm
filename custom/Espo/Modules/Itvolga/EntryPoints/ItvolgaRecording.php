<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\EntryPoints;

use Espo\Core\Api\Request;
use Espo\Core\Api\Response;
use Espo\Core\EntryPoint\EntryPoint;
use Espo\Core\Exceptions\BadRequest;
use Espo\Modules\Itvolga\Tools\Telephony\RecordingService;

/**
 * GET ?entryPoint=itvolgaRecording&id=<Call id> — the recording of a call as audio/wav for the player of the Call
 * view (stage 07.1, D-171). Authentication as for every entry point (the browser sends its auth cookie; no public
 * link exists); access, the file and logging — RecordingService.
 */
class ItvolgaRecording implements EntryPoint
{
    public function __construct(private RecordingService $service) {}

    public function run(Request $request, Response $response): void
    {
        $id = $request->getQueryParam('id');

        if (!is_string($id) || !preg_match('/^[A-Za-z0-9]{1,24}$/', $id)) {
            throw new BadRequest('No id.');
        }

        $result = $this->service->open($id, $request->getHeader('Range'));

        $response
            ->setStatus($result['status'])
            ->setHeader('Cache-Control', 'private, no-store, max-age=0')
            ->setHeader('X-Content-Type-Options', 'nosniff');

        foreach ($result['headers'] as $name => $value) {
            $response->setHeader($name, $value);
        }

        if ($result['body'] !== null) {
            $response->setBody($result['body']);
        }
    }
}
