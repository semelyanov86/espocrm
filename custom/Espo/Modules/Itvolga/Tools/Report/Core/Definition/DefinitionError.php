<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Definition;

use InvalidArgumentException;

/**
 * A report definition (or the parameters of a run) the engine refuses: `key` names the rule for a translated message
 * (`Report.messages.<code>`), `path` points to the place ("groups[1].granularity"), `params` fill the message. None of
 * them carries a filter value or record data (error messages are logged by the core).
 */
class DefinitionError extends InvalidArgumentException
{
    /**
     * @param array<string, string|int> $params
     */
    public function __construct(
        public readonly string $key,
        public readonly string $path,
        public readonly array $params = [],
    ) {
        parent::__construct("Report definition: $key" . ($path !== '' ? " at $path" : '') . '.');
    }
}
