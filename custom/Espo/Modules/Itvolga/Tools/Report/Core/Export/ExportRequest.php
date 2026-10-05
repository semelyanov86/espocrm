<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Export;

use Espo\Modules\Itvolga\Tools\Report\Core\Definition\DefinitionError;

/**
 * A request of a file or a print view (POST Report/:id/export | printView, D-116, D-120): the format, the variant
 * «report data» (the limits of the report) or «all» (no row and group limits; the caps of a run stay), «in the
 * background», and the conditions of the shown result — one-off filters and quick filter values, checked later by
 * DefinitionParser::parseRun like those of a run. Nothing else of the request reaches the engine (no page, no user).
 */
final class ExportRequest
{
    public const VARIANT_REPORT = 'report';
    public const VARIANT_ALL = 'all';

    /**
     * @param array<string, mixed> $runParams parameters of ReportRunner::prepare
     */
    private function __construct(
        public readonly string $format,
        public readonly string $variant,
        public readonly bool $background,
        public readonly array $runParams,
    ) {}

    /**
     * @param array<string, mixed> $raw
     * @param list<string> $formats allowed formats (none for a print view)
     */
    public static function parse(array $raw, array $formats): self
    {
        $format = $raw['format'] ?? null;

        if ($formats !== [] && !in_array($format, $formats, true)) {
            throw new DefinitionError('badExportFormat', 'format');
        }

        $variant = $raw['variant'] ?? self::VARIANT_REPORT;

        if (!in_array($variant, [self::VARIANT_REPORT, self::VARIANT_ALL], true)) {
            throw new DefinitionError('badExportVariant', 'variant');
        }

        $background = $raw['background'] ?? false;

        if (!is_bool($background)) {
            throw new DefinitionError('badExportVariant', 'background');
        }

        return new self(
            format: $formats === [] ? '' : $format,
            variant: $variant,
            background: $background,
            runParams: self::runParams($raw, $variant === self::VARIANT_ALL),
        );
    }

    /**
     * Run parameters of a request (also of a queued one): only the conditions and the no-limit flag.
     *
     * @param array<string, mixed> $raw
     * @return array<string, mixed>
     */
    public static function runParams(array $raw, bool $noLimit): array
    {
        $params = ['noLimit' => $noLimit, 'withQuickFilterOptions' => false,
            'quickFilters' => $raw['quickFilters'] ?? []];

        if (array_key_exists('filters', $raw) && $raw['filters'] !== null) {
            $params['filters'] = $raw['filters'];
        }

        return $params;
    }
}
