<?php

namespace Espo\Modules\Itvolga\Tools\Import;

use RuntimeException;

/**
 * A refused import operation. The message is a closed code (and at most an attribute name): never a value.
 */
class ImportError extends RuntimeException
{
    /**
     * @param string[] $attributes
     */
    public function __construct(public readonly string $reason, public readonly array $attributes = [])
    {
        parent::__construct($reason);
    }
}
