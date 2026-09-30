<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Finance\Exceptions;

use RuntimeException;

/**
 * The input needs a calculation rule that is excluded by a decision (for example VAT, D-21) or is not confirmed
 * by the source data and still waits for the owner (open question). The core refuses instead of guessing.
 */
class RuleNotSupported extends RuntimeException
{
    public function __construct(
        public readonly string $rule,
        public readonly string $reference,
        string $message,
    ) {
        parent::__construct("$message [$rule, $reference]");
    }
}
