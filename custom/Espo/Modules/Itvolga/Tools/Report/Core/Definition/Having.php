<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Definition;

/**
 * A condition on an aggregate of the level-1 groups (SQL HAVING); conditions combine with AND.
 */
final class Having
{
    public const OPERATORS = ['equals', 'notEquals', 'greaterThan', 'lessThan', 'greaterThanOrEquals',
        'lessThanOrEquals', 'between'];

    /**
     * @param string|array{string, string} $value decimal string(s)
     */
    public function __construct(
        public readonly Aggregate $aggregate,
        public readonly string $operator,
        public readonly string|array $value,
    ) {}

    /**
     * @return array<string, mixed>
     */
    public function toArray(): array
    {
        return ['aggregate' => $this->aggregate->key(), 'operator' => $this->operator, 'value' => $this->value];
    }
}
