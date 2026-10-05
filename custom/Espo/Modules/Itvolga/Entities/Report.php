<?php

namespace Espo\Modules\Itvolga\Entities;

use Espo\Core\Templates\Entities\Base;

class Report extends Base
{
    public const ENTITY_TYPE = 'Report';

    public const TYPE_TABULAR = 'tabular';
    public const TYPE_SUMMARIES = 'summaries';
    public const TYPE_SUMMARIES_WITH_DETAILS = 'summariesWithDetails';
    public const TYPE_MATRIX = 'matrix';

    public const ACCESS_PRIVATE = 'private';
    public const ACCESS_PUBLIC = 'public';
    public const ACCESS_SHARED = 'shared';

    /** Attributes of the report definition (stored JSON and limits), validated together (reports.md §2). */
    public const DEFINITION_ATTRIBUTES = ['type', 'entityType', 'columns', 'sorting', 'rowLimit', 'groups',
        'aggregates', 'groupSort', 'groupLimit', 'totals', 'calculations', 'filters', 'havingFilters', 'quickFilters',
        'labels', 'charts', 'dashboard'];

    /**
     * The mailing (05.3, D-121): its settings — stored, written by the API, never read back by it (`internal`) — and
     * the runtime of the job (next slot, last attempt and its outcome), written by UPDATE (D-122). A save rebases them
     * on the committed row with the definition.
     */
    public const MAILING_ATTRIBUTES = ['mailing', 'mailingNextRunAt', 'mailingLastRunAt', 'mailingLastResult'];
}
