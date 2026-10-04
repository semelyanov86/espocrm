<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report;

use Espo\Core\Exceptions\BadRequest;
use Espo\Core\Exceptions\Error\Body;
use Espo\Core\Exceptions\Forbidden;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\DefinitionError;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\FieldForbidden;

/**
 * A refused definition or run → HTTP error with a translated message `Report.messages.<key>` (D-101): 400, or 403 when
 * ACL closes a field, link or entity. Parameters name fields and places, never values.
 */
final class ErrorMapper
{
    public static function toHttp(DefinitionError $e): BadRequest|Forbidden
    {
        $data = array_map('strval', $e->params) + ['path' => $e->path];
        $body = Body::create()->withMessageTranslation($e->key, 'Report', $data);

        return $e instanceof FieldForbidden ?
            Forbidden::createWithBody($e->getMessage(), $body) :
            BadRequest::createWithBody($e->getMessage(), $body);
    }
}
