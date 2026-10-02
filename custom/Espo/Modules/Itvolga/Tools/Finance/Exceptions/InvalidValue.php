<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Finance\Exceptions;

use InvalidArgumentException;

/**
 * A value the finance core cannot accept: float, malformed number, wrong sign or too many decimals.
 *
 * `key` names the kind of problem (for a translated message), `documentLine` the 1-based document line and `field`
 * the attribute it concerns; all three are optional and never contain the rejected value itself.
 */
class InvalidValue extends InvalidArgumentException
{
    public function __construct(
        string $message = '',
        public readonly ?string $key = null,
        public readonly ?int $documentLine = null,
        public readonly ?string $field = null,
    ) {
        parent::__construct($message);
    }
}
