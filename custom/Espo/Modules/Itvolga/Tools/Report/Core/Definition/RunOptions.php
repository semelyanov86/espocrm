<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Definition;

/**
 * Parameters of one run (POST Report/:id/run): page of the rows, quick filter values (the main filter of a dashlet is
 * one of them, D-109), the no-limit flag (export, 05.3) and whether the options of the quick filters and of the
 * dashboard filter are wanted. One-off conditions replace the definition's filters before
 * these options are made (Definition::withFilters).
 *
 * All rows (05.3, D-116): a file, a print view or a letter takes every row within the limits in one result. Only the
 * server sets it (withAllRows); a request cannot, so the API page stays ≤ MAX_PAGE_SIZE.
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
        public readonly bool $withDashboardFilterOptions = false,
        public readonly bool $allRows = false,
    ) {}

    /**
     * The same conditions as one result of all rows up to the run cap: no page, no options of filters.
     */
    public function withAllRows(int $maxRows): self
    {
        return new self(offset: 0, maxSize: $maxRows, quickFilters: $this->quickFilters, noLimit: $this->noLimit,
            withQuickFilterOptions: false, withDashboardFilterOptions: false, allRows: true);
    }
}
