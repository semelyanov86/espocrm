<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Chart;

use Closure;
use Espo\Modules\Itvolga\Tools\Finance\Decimal;
use Espo\Modules\Itvolga\Tools\Report\Core\DecimalMath;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\Aggregate;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\ChartAxis;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\ChartItem;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\ChartType;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\Definition;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\ReportType;
use Espo\Modules\Itvolga\Tools\Report\Core\Format\NumberText;
use Espo\Modules\Itvolga\Tools\Report\Core\Format\RawNumber;
use Espo\Modules\Itvolga\Tools\Report\Core\Result\KeyOrder;

/**
 * Data of the charts of a summary report (D-105…D-108), made from the assembled result of the run (D-102) without any
 * query: a chart point is the very cell of the table (`v` raw, `f` formatted) with the drill-down path of its group,
 * so the chart and the table cannot differ. Categories are the shown groups of level 1 (matrix: its rows); on the
 * axis «group 1 → group 2» the series are the values of group 2 (matrix: its columns) — a missing pair is null.
 * Shares of pies and progress lines are exact decimals; the client turns `v` into a float only to plot it.
 */
final class ChartBuilder
{
    public const MAX_SERIES = 50;
    private const SHARE_SCALE = 1;

    /**
     * @param Closure(Aggregate): string $label header of an aggregate (labels of the report applied)
     * @param Closure(Aggregate, string, Decimal, ?string): array<string, mixed> $format cell of a progress value
     *     (aggregate, function MIN|AVG|MAX, value, currency)
     */
    public function __construct(
        private readonly KeyOrder $order,
        private readonly NumberText $numbers,
        private readonly Closure $label,
        private readonly Closure $format,
    ) {}

    /**
     * @param array<string, mixed> $result
     * @return ?array<string, mixed> null when the report draws no chart
     */
    public function build(Definition $definition, array $result): ?array
    {
        $settings = $definition->charts;

        if ($settings->isEmpty() || !$definition->type->isGrouped()) {
            return null;
        }

        $isMatrix = $definition->type === ReportType::MATRIX;
        $rows = $isMatrix ? ($result['matrix']['rows'] ?? []) : ($result['tree'] ?? []);
        $second = $settings->axis === ChartAxis::GROUP1_GROUP2;
        [$series, $capped] = $second ? $this->seriesOf($definition, $result, $rows) : [[], false];

        return [
            'title' => $settings->title,
            'position' => $settings->position,
            'collapseTable' => $settings->collapseTable,
            'axis' => $settings->axis->value,
            'progressLines' => $settings->progressLines,
            'categoryLabel' => $result['groups'][0]['label'] ?? '',
            'seriesLabel' => $second ? ($result['groups'][1]['label'] ?? '') : null,
            'categories' => array_map(fn (array $row) => ['key' => $row['key'], 'path' => [$row['key']['v']]], $rows),
            'items' => array_map(fn (ChartItem $item) => $this->item($item, $definition, $result, $rows, $series,
                $capped), $settings->items),
        ];
    }

    /**
     * Series of the axis «group 1 → group 2»: matrix columns, or the union of the level-2 groups of the shown level-1
     * groups (one series per database group — `keyId` — in the order of group 2), at most MAX_SERIES.
     *
     * @param array<string, mixed> $result
     * @param list<array<string, mixed>> $rows
     * @return array{list<array{id: string, key: array<string, mixed>, column: ?int}>, bool}
     */
    private function seriesOf(Definition $definition, array $result, array $rows): array
    {
        if ($definition->type === ReportType::MATRIX) {
            $list = [];

            foreach ($result['matrix']['columns'] ?? [] as $c => $column) {
                $list[] = ['id' => self::id($column), 'key' => $column['key'], 'column' => $c];
            }
        } else {
            $byId = [];

            foreach ($rows as $row) {
                foreach ($row['children'] ?? [] as $child) {
                    $byId[self::id($child)] ??= ['id' => self::id($child), 'key' => $child['key'], 'column' => null];
                }
            }

            $list = array_values($byId);
            usort($list, fn ($a, $b) => $this->order->compare($definition->groups[1], $a['key'], $b['key']));
        }

        return [array_slice($list, 0, self::MAX_SERIES), count($list) > self::MAX_SERIES];
    }

    /**
     * @param array<string, mixed> $result
     * @param list<array<string, mixed>> $rows
     * @param list<array{id: string, key: array<string, mixed>, column: ?int}> $series
     * @return array<string, mixed>
     */
    private function item(ChartItem $item, Definition $definition, array $result, array $rows, array $series,
        bool $capped): array
    {
        $index = array_search($item->aggregate->key(), array_map(fn (Aggregate $a) => $a->key(),
            $definition->aggregates), true);
        $index = $index === false ? null : $index;
        $label = ($this->label)($item->aggregate);
        $notes = $capped ? ['seriesCapped'] : [];
        $inner = null;

        if ($series === []) {
            $lines = [['key' => null, 'label' => $label, 'points' => array_map(fn (array $row) =>
                $this->point($row, $index, [$row['key']['v']]), $rows)]];
        } else {
            $lines = [];

            foreach ($series as $s) {
                $points = [];

                foreach ($rows as $r => $row) {
                    $points[] = $this->pairPoint($row, $r, $s, $index, $result);
                }

                $lines[] = ['key' => $s['key'], 'label' => (string) $s['key']['f'], 'points' => $points];
            }

            if ($item->type->isPie()) {
                $inner = array_map(fn (array $row) => $this->point($row, $index, [$row['key']['v']]), $rows);
            }
        }

        $all = array_merge($inner ?? [], ...array_map(fn ($line) => $line['points'], $lines));
        $currencies = [];

        foreach ($all as $point) {
            if ($point !== null && $point['v'] !== null && isset($point['cur'])) {
                $currencies[$point['cur']] = true;
            }

            if ($point !== null && !empty($point['mixed'])) {
                $notes[] = 'mixedValuesOmitted';
            }
        }

        $unavailable = count($currencies) > 1 ? 'mixedCurrencies' : null;
        $currency = array_key_first($currencies);
        $progress = [];

        if ($item->type->isPie() || $item->type === ChartType::FUNNEL) {
            foreach ($all as $point) {
                $value = self::number($point);

                if ($value !== null && !$value->isPositive()) {
                    $notes[] = 'nonPositiveOmitted';
                }
            }
        }

        if ($item->type->isPie()) {
            // Shares of the outer ring (or the only one) over all its points, in the order of the series.
            $outer = $this->withShares(array_merge(...array_map(fn ($line) => $line['points'], $lines)));
            $offset = 0;

            foreach ($lines as &$line) {
                $line['points'] = array_slice($outer, $offset, count($line['points']));
                $offset += count($line['points']);
            }

            unset($line);
            $inner = $inner === null ? null : $this->withShares($inner);
        } elseif ($series === [] && $item->type->hasProgressLines() && $definition->charts->progressLines !== [] &&
            $unavailable === null) {
            $values = array_map(fn ($point) => self::number($point), $lines[0]['points']);

            foreach (ProgressLines::compute($values, $definition->charts->progressLines) as $function => $list) {
                $progress[$function] = array_map(fn (?Decimal $value) => $value === null ? null :
                    ($this->format)($item->aggregate, $function, $value, $currency), $list);
            }
        }

        return [
            'type' => $item->type->value,
            'aggregate' => $item->aggregate->key(),
            'label' => $label,
            'series' => $lines,
            'inner' => $inner,
            'progress' => (object) $progress,
            'notes' => array_values(array_unique($notes)),
            'unavailable' => $unavailable,
        ];
    }

    /**
     * The point of a group: the cell of the aggregate (COUNT not chosen as an aggregate: the group's exact count).
     *
     * @param array<string, mixed> $node
     * @param list<mixed> $path
     * @return array<string, mixed>
     */
    private function point(array $node, ?int $index, array $path): array
    {
        $cell = $index === null ? ['v' => (int) $node['count'], 'f' => $this->numbers->format((int) $node['count'])] :
            $node['values'][$index];

        return $cell + ['path' => $path];
    }

    /**
     * @param array<string, mixed> $row
     * @param array{id: string, key: array<string, mixed>, column: ?int} $series
     * @param array<string, mixed> $result
     * @return ?array<string, mixed>
     */
    private function pairPoint(array $row, int $r, array $series, ?int $index, array $result): ?array
    {
        if ($series['column'] !== null) {
            $cell = $result['matrix']['cells'][$r][$series['column']] ?? null;

            return $cell === null ? null : $this->point($cell, $index, [$row['key']['v'], $series['key']['v']]);
        }

        foreach ($row['children'] ?? [] as $child) {
            if (self::id($child) === $series['id']) {
                return $this->point($child, $index, [$row['key']['v'], $child['key']['v']]);
            }
        }

        return null;
    }

    /**
     * Shares of a pie ring: each drawn (positive) value of the ring in percent of their sum, exact.
     *
     * @param list<?array<string, mixed>> $points
     * @return list<?array<string, mixed>>
     */
    private function withShares(array $points): array
    {
        $sum = Decimal::zero();

        foreach ($points as $point) {
            $value = self::number($point);

            if ($value !== null && $value->isPositive()) {
                $sum = $sum->add($value);
            }
        }

        return array_map(function (?array $point) use ($sum): ?array {
            $value = self::number($point);

            if ($point === null || $value === null || !$value->isPositive()) {
                return $point;
            }

            $share = DecimalMath::divide($value->mul(100), $sum);

            return $point + ['share' => $share === null ? null : ['v' => $share->toString(),
                'f' => $this->numbers->format($share, self::SHARE_SCALE) . ' %']];
        }, $points);
    }

    /**
     * Value of a point a chart may draw: none for an empty or mixed-currency cell.
     *
     * @param ?array<string, mixed> $point
     */
    private static function number(?array $point): ?Decimal
    {
        if ($point === null || !empty($point['mixed'])) {
            return null;
        }

        return RawNumber::read($point['v']);
    }

    /**
     * Identity of a group node: the database group (`keyId` from the assembler), else its raw key.
     *
     * @param array<string, mixed> $node
     */
    private static function id(array $node): string
    {
        return (string) ($node['keyId'] ?? json_encode($node['key']['v']));
    }
}
