<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Definition;

/**
 * Rules of the charts part (D-105, D-106, D-107): only summary types draw charts; at most three, each of a known type
 * and plotting COUNT or one of the report's aggregates; the axis «group 1 → group 2» needs a second group (summaries
 * with two or more levels, or a matrix), takes one chart, no funnel and no progress lines.
 */
final class ChartSettingsParser
{
    public static function parse(mixed $raw, Definition $definition): ChartSettings
    {
        $raw = json_decode((string) json_encode($raw), true);

        if ($raw === null || $raw === []) {
            return new ChartSettings();
        }

        if (!is_array($raw) || array_is_list($raw)) {
            throw new DefinitionError('badStructure', 'charts');
        }

        $title = $raw['title'] ?? '';

        if (!is_string($title)) {
            throw new DefinitionError('badChart', 'charts.title');
        }

        $title = trim($title);

        if (mb_strlen($title) > ChartSettings::MAX_TITLE_LENGTH) {
            throw new DefinitionError('badLabel', 'charts.title', ['max' => ChartSettings::MAX_TITLE_LENGTH]);
        }

        $position = $raw['position'] ?? 'top';
        $collapse = $raw['collapseTable'] ?? false;
        $axis = $raw['axis'] ?? ChartAxis::GROUP1->value;
        $axis = is_string($axis) ? ChartAxis::tryFrom($axis) : null;
        $progress = $raw['progressLines'] ?? [];

        if (!in_array($position, ChartSettings::POSITIONS, true)) {
            throw new DefinitionError('badChart', 'charts.position');
        }

        if (!is_bool($collapse)) {
            throw new DefinitionError('badChart', 'charts.collapseTable');
        }

        if ($axis === null) {
            throw new DefinitionError('badChart', 'charts.axis');
        }

        if (!is_array($progress) || !array_is_list($progress) ||
            array_diff($progress, ChartSettings::PROGRESS_LINES) !== []) {
            throw new DefinitionError('badChart', 'charts.progressLines');
        }

        $items = self::items($raw['items'] ?? [], $definition);

        if (!$definition->type->isGrouped()) {
            if ($items !== []) {
                throw new DefinitionError('notForType', 'charts');
            }

            return new ChartSettings();
        }

        $settings = new ChartSettings($title, $position, $collapse, $axis,
            array_values(array_intersect(ChartSettings::PROGRESS_LINES, $progress)), $items);

        if ($axis === ChartAxis::GROUP1_GROUP2) {
            self::checkSecondGroup($settings, $definition);
        }

        return $settings;
    }

    /**
     * @return list<ChartItem>
     */
    private static function items(mixed $raw, Definition $definition): array
    {
        if (!is_array($raw) || !array_is_list($raw)) {
            throw new DefinitionError('badStructure', 'charts.items');
        }

        if (count($raw) > ChartSettings::MAX_ITEMS) {
            throw new DefinitionError('tooMany', 'charts.items', ['max' => ChartSettings::MAX_ITEMS]);
        }

        $result = [];

        foreach ($raw as $i => $item) {
            $path = "charts.items[$i]";

            if (!is_array($item)) {
                throw new DefinitionError('badStructure', $path);
            }

            $type = is_string($item['type'] ?? null) ? ChartType::tryFrom($item['type']) : null;

            if ($type === null) {
                throw new DefinitionError('badChartType', "$path.type");
            }

            $key = $item['aggregate'] ?? 'COUNT';
            $aggregate = $key === 'COUNT' ? ($definition->aggregate('COUNT') ?? new Aggregate('COUNT')) :
                (is_string($key) ? $definition->aggregate($key) : null);

            if ($aggregate === null) {
                throw new DefinitionError('badChartAggregate', "$path.aggregate");
            }

            $result[] = new ChartItem($type, $aggregate);
        }

        return $result;
    }

    private static function checkSecondGroup(ChartSettings $settings, Definition $definition): void
    {
        $allowed = $definition->type === ReportType::MATRIX ||
            $definition->type === ReportType::SUMMARIES && count($definition->groups) >= 2;

        if (!$allowed) {
            throw new DefinitionError('chartAxisNotAllowed', 'charts.axis');
        }

        if (count($settings->items) > 1) {
            throw new DefinitionError('chartAxisOneChart', 'charts.items');
        }

        if ($settings->items !== [] && !$settings->items[0]->type->allowsSecondGroup()) {
            throw new DefinitionError('chartFunnelSecondGroup', 'charts.items[0].type');
        }

        if ($settings->progressLines !== []) {
            throw new DefinitionError('chartProgressSecondGroup', 'charts.progressLines');
        }
    }
}
