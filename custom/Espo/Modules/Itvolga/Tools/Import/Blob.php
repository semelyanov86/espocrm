<?php

namespace Espo\Modules\Itvolga\Tools\Import;

/**
 * Bytes of one imported file, received and checked (BlobReceiver), waiting in a part file for their attachment.
 */
final class Blob
{
    public function __construct(
        public readonly string $path,
        public readonly int $size,
        public readonly string $sha256,
    ) {}
}
