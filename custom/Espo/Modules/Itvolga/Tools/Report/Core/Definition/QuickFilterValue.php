<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Definition;

/**
 * Values chosen in a quick filter block of the result page for one run: records whose value is (mode in) or is not
 * (mode notIn) among the values; `includeEmpty` stands for the "(empty)" item.
 */
final class QuickFilterValue
{
    /**
     * @param list<string|int|bool> $values
     */
    public function __construct(
        public readonly FieldInfo $field,
        public readonly string $mode,
        public readonly array $values,
        public readonly bool $includeEmpty,
    ) {}

    public function isEmpty(): bool
    {
        return $this->values === [] && !$this->includeEmpty;
    }
}
