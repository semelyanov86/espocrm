<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Definition;

/**
 * The report on a dashboard (D-109): the field of the main filter chosen in the dashlet header (an enum field or the
 * owner of the main entity; a quick filter of that field) and the default mode of the dashlet.
 */
final class DashboardSettings
{
    public const MODE_CHART = 'chart';
    public const MODE_TABLE = 'table';
    public const MODES = [self::MODE_CHART, self::MODE_TABLE];

    public function __construct(
        public readonly ?FieldInfo $filterField = null,
        public readonly string $mode = self::MODE_TABLE,
    ) {}

    /**
     * @return array{filterField: ?string, mode: string}
     */
    public function toArray(): array
    {
        return ['filterField' => $this->filterField?->ref->toString(), 'mode' => $this->mode];
    }
}
