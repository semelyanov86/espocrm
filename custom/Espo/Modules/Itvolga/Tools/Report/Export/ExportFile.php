<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Export;

/**
 * A file of a report result before it is stored as an Attachment.
 */
final class ExportFile
{
    public function __construct(
        public readonly string $name,
        public readonly string $mimeType,
        public readonly string $contents,
    ) {}
}
