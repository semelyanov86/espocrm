<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Definition;

/**
 * Parameters of one run (POST Report/:id/run): page of the rows, quick filter values, the no-limit flag (export,
 * 05.3) and whether the quick filter options are wanted. One-off conditions replace the definition's filters before
 * these options are made (Definition::withFilters).
 */
final class RunOptions
{
    public const MAX_PAGE_SIZE = 200;

    /**
     * @param list<QuickFilterValue> $quickFilters
     */
    public function __construct(
        public readonly int $offset = 0,
        public readonly int $maxSize = 50,
        public readonly array $quickFilters = [],
        public readonly bool $noLimit = false,
        public readonly bool $withQuickFilterOptions = true,
    ) {}
}
