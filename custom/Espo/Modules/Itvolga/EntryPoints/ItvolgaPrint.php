<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\EntryPoints;

use Espo\Core\Api\Request;
use Espo\Core\Api\Response;
use Espo\Core\EntryPoint\EntryPoint;
use Espo\Core\Exceptions\BadRequest;
use Espo\Modules\Itvolga\Tools\FinancePrint\PrintService;

/**
 * GET ?entryPoint=itvolgaPrint&entityType=Invoice&id=… — the print form of a finance record as an inline PDF
 * (stage 05, the «Печать» action of the record view opens it in a new tab). Authentication as for every entry point;
 * access and the form rules — PrintService.
 */
class ItvolgaPrint implements EntryPoint
{
    public function __construct(private PrintService $printService) {}

    public function run(Request $request, Response $response): void
    {
        $entityType = $request->getQueryParam('entityType');
        $id = $request->getQueryParam('id');

        if (!is_string($entityType) || !is_string($id) || $entityType === '' || $id === '') {
            throw new BadRequest('No entityType or id.');
        }

        $result = $this->printService->print($entityType, $id);

        $response
            ->setHeader('Content-Type', 'application/pdf')
            ->setHeader('Content-Disposition', $result->contentDisposition($entityType . '.pdf'))
            ->setHeader('Cache-Control', 'private, no-store, max-age=0')
            ->setHeader('X-Content-Type-Options', 'nosniff');

        if (!$request->getServerParam('HTTP_ACCEPT_ENCODING')) {
            $response->setHeader('Content-Length', (string) $result->contents->getLength());
        }

        $response->setBody($result->contents->getStream());
    }
}
