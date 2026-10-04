<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Calculation;

use InvalidArgumentException;

/**
 * A custom calculation expression the report cannot accept. `key` names the problem for a translated message
 * (`Report.messages.calculation<Key>`), `position` is the 1-based character where it was found (0 = whole expression).
 */
final class ParseError extends InvalidArgumentException
{
    public function __construct(
        public readonly string $key,
        public readonly int $position = 0,
        public readonly ?string $reference = null,
    ) {
        parent::__construct("Calculation expression: $key at $position.");
    }
}
