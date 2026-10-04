<?php

declare(strict_types=1);

namespace Itvolga\Tests\Reports;

use Espo\Modules\Itvolga\Tools\Finance\Decimal;
use Espo\Modules\Itvolga\Tools\Report\Core\Chart\ChartBuilder;
use Espo\Modules\Itvolga\Tools\Report\Core\Chart\ProgressLines;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\Aggregate;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\Definition;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\DefinitionParser;
use Espo\Modules\Itvolga\Tools\Report\Core\Format\NumberText;
use Espo\Modules\Itvolga\Tools\Report\Core\Result\KeyOrder;
use Itvolga\Tests\Finance\TestCase;

/**
 * Chart data from an assembled result (D-105…D-108): points are the table's cells with their drill-down paths,
 * COUNT without a COUNT aggregate, matrix rows and cells, series of group 2 ordered and merged by database group,
 * missing pairs, pie shares per ring, mixed currencies, progress lines.
 */
final class ChartBuilderTest extends TestCase
{
    private DefinitionParser $parser;
    private ChartBuilder $builder;

    public function setUp(): void
    {
        $this->parser = new DefinitionParser(new FakeSchema());
        $this->builder = new ChartBuilder(new KeyOrder(), new NumberText(',', ' '),
            fn (Aggregate $a) => 'L:' . $a->key(),
            fn (Aggregate $a, string $function, Decimal $v, ?string $cur) =>
                ['v' => $v->toString(), 'f' => "$function " . $v->toString() . ($cur ? " $cur" : '')]);
    }

    /**
     * @param array<string, mixed> $charts
     */
    private function summaries(array $charts, int $levels = 1): Definition
    {
        return $this->parser->parse(['type' => 'summaries', 'entityType' => 'Invoice',
            'groups' => array_slice([['field' => 'status'], ['field' => 'dateInvoiced', 'granularity' => 'month']], 0,
                $levels),
            'aggregates' => [['function' => 'SUM', 'field' => 'grandTotal']], 'charts' => $charts]);
    }

    private static function money(string $v, string $cur = 'RUB'): array
    {
        return ['v' => $v, 'f' => "$v ₽", 'cur' => $cur];
    }

    private static function node(?string $key, int $count, array $value, array $children = [], ?string $keyId = null): array
    {
        return ['key' => ['v' => $key, 'f' => $key ?? '(пусто)'], 'count' => $count, 'values' => [$value],
            'children' => $children] + ($keyId === null ? [] : ['keyId' => $keyId]);
    }

    private static function result(array $tree): array
    {
        return ['groups' => [['label' => 'Статус'], ['label' => 'Дата (месяц)']], 'tree' => $tree];
    }

    public function testNoChartsGiveNoData(): void
    {
        $this->assertSame(null, $this->builder->build($this->summaries([]), self::result([])));
    }

    public function testPointsAreTheCellsOfTheGroups(): void
    {
        $definition = $this->summaries(['items' => [['type' => 'bar', 'aggregate' => 'SUM:grandTotal'],
            ['type' => 'line', 'aggregate' => 'COUNT']]]);
        $data = $this->builder->build($definition, self::result([
            self::node('Draft', 2, self::money('19500.00')),
            self::node('Sent', 3, self::money('1000.50')),
            self::node(null, 1, ['v' => null, 'f' => '']),
        ]));

        $this->assertSame([['v' => 'Draft', 'f' => 'Draft'], ['v' => 'Sent', 'f' => 'Sent'],
            ['v' => null, 'f' => '(пусто)']], array_map(fn ($c) => $c['key'], $data['categories']));
        $this->assertSame([['Draft'], ['Sent'], [null]], array_map(fn ($c) => $c['path'], $data['categories']));
        $this->assertSame('Статус', $data['categoryLabel']);

        $sum = $data['items'][0];
        $this->assertSame('L:SUM:grandTotal', $sum['label']);
        $this->assertSame(1, count($sum['series']));
        $this->assertSame(['v' => '19500.00', 'f' => '19500.00 ₽', 'cur' => 'RUB', 'path' => ['Draft']],
            $sum['series'][0]['points'][0]);
        $this->assertSame(null, $sum['unavailable']);

        // COUNT is not one of the aggregates: the exact count of each group.
        $count = $data['items'][1]['series'][0]['points'];
        $this->assertSame([2, 3, 1], array_map(fn ($p) => $p['v'], $count));
        $this->assertSame('L:COUNT', $data['items'][1]['label']);
    }

    public function testSecondGroupSeriesAreMergedAndOrdered(): void
    {
        $definition = $this->summaries(['axis' => 'group1group2', 'items' => [['type' => 'stackedBar']]], 2);
        $data = $this->builder->build($definition, self::result([
            self::node('Draft', 3, self::money('10'), [
                self::node('2026-09', 1, self::money('4'), [], 'm9'),
                self::node('2026-08', 2, self::money('6'), [], 'm8'),
            ]),
            self::node('Paid', 1, self::money('5'), [
                self::node('2026-09', 1, self::money('5'), [], 'm9'),
            ]),
        ]));
        $item = $data['items'][0];

        $this->assertSame('Дата (месяц)', $data['seriesLabel']);
        $this->assertSame(['2026-08', '2026-09'], array_map(fn ($s) => $s['key']['v'], $item['series']));
        // Draft has both months; Paid has no 2026-08 — a missing pair is null.
        $this->assertSame([2, null], array_map(fn ($p) => $p['v'] ?? null,
            [$item['series'][0]['points'][0], $item['series'][0]['points'][1]]));
        $this->assertSame(null, $item['series'][0]['points'][1]);
        $this->assertSame(['Paid', '2026-09'], $item['series'][1]['points'][1]['path']);
        $this->assertSame(null, $item['inner']);
    }

    public function testSeriesOfOneDatabaseGroupMergeAcrossCategories(): void
    {
        $definition = $this->parser->parse(['type' => 'summaries', 'entityType' => 'Invoice',
            'groups' => [['field' => 'status'], ['field' => 'name']], 'aggregates' => [['function' => 'COUNT']],
            'charts' => ['axis' => 'group1group2', 'items' => [['type' => 'bar']]]]);
        $data = $this->builder->build($definition, self::result([
            ['key' => ['v' => 'Draft', 'f' => 'Draft'], 'count' => 1, 'values' => [['v' => 1, 'f' => '1']],
                'children' => [['key' => ['v' => 'Берлин', 'f' => 'Берлин'], 'count' => 1,
                    'values' => [['v' => 1, 'f' => '1']], 'keyId' => 'b']]],
            ['key' => ['v' => 'Sent', 'f' => 'Sent'], 'count' => 2, 'values' => [['v' => 2, 'f' => '2']],
                'children' => [['key' => ['v' => 'берлин', 'f' => 'берлин'], 'count' => 2,
                    'values' => [['v' => 2, 'f' => '2']], 'keyId' => 'b']]],
        ]));
        $series = $data['items'][0]['series'];

        $this->assertSame(1, count($series));
        // Each point keeps the key of its own group for the drill-down.
        $this->assertSame([['Draft', 'Берлин'], ['Sent', 'берлин']], array_map(fn ($p) => $p['path'],
            $series[0]['points']));
    }

    public function testMatrixRowsAndCells(): void
    {
        $matrix = fn (array $charts) => $this->parser->parse(['type' => 'matrix', 'entityType' => 'Invoice',
            'groups' => [['field' => 'status'], ['field' => 'dateInvoiced', 'granularity' => 'month']],
            'aggregates' => [['function' => 'SUM', 'field' => 'grandTotal']], 'charts' => $charts]);
        $result = ['groups' => [['label' => 'Статус'], ['label' => 'Месяц']], 'matrix' => [
            'rows' => [self::node('Draft', 2, self::money('30')), self::node('Sent', 1, self::money('7'))],
            'columns' => [self::node('2026-08', 1, self::money('10')), self::node('2026-09', 2, self::money('27'))],
            'cells' => [[['count' => 1, 'values' => [self::money('10')]], ['count' => 1, 'values' => [self::money('20')]]],
                [null, ['count' => 1, 'values' => [self::money('7')]]]],
        ]];

        $rows = $this->builder->build($matrix(['items' => [['type' => 'bar', 'aggregate' => 'SUM:grandTotal']]]), $result);
        $this->assertSame(['30', '7'], array_map(fn ($p) => $p['v'], $rows['items'][0]['series'][0]['points']));

        $cells = $this->builder->build($matrix(['axis' => 'group1group2', 'items' => [['type' => 'line']]]), $result);
        $series = $cells['items'][0]['series'];
        $this->assertSame(['2026-08', '2026-09'], array_map(fn ($s) => $s['key']['v'], $series));
        $this->assertSame([1, null], array_map(fn ($p) => $p['v'] ?? null, $series[0]['points']));
        $this->assertSame(['Sent', '2026-09'], $series[1]['points'][1]['path']);
    }

    public function testPieSharesAndRings(): void
    {
        $definition = $this->summaries(['axis' => 'group1group2', 'items' => [['type' => 'piePercent',
            'aggregate' => 'SUM:grandTotal']]], 2);
        $data = $this->builder->build($definition, self::result([
            self::node('Draft', 2, self::money('40'), [
                self::node('2026-08', 1, self::money('10'), [], '8'), self::node('2026-09', 1, self::money('30'), [], '9'),
            ]),
            self::node('Sent', 1, self::money('-5'), [self::node('2026-09', 1, self::money('-5'), [], '9')]),
        ]));
        $item = $data['items'][0];

        // Inner ring: level 1, the negative group is not drawn; shares of its own positive sum.
        $this->assertSame('100', $item['inner'][0]['share']['v']);
        $this->assertSame(false, isset($item['inner'][1]['share']));
        // Outer ring: pairs, shares of the ring's positive sum (10 + 30).
        $this->assertSame('25', $item['series'][0]['points'][0]['share']['v']);
        $this->assertSame('25,0 %', $item['series'][0]['points'][0]['share']['f']);
        $this->assertSame('75', $item['series'][1]['points'][0]['share']['v']);
        $this->assertSame(['nonPositiveOmitted'], $item['notes']);
    }

    public function testMixedCurrenciesMakeTheChartUnavailable(): void
    {
        $definition = $this->summaries(['progressLines' => ['AVG'], 'items' => [['type' => 'bar',
            'aggregate' => 'SUM:grandTotal']]]);
        $data = $this->builder->build($definition, self::result([
            self::node('Draft', 1, self::money('10', 'RUB')), self::node('Sent', 1, self::money('10', 'EUR')),
            self::node('Paid', 1, ['v' => null, 'f' => 'разные валюты', 'mixed' => true]),
        ]));

        $this->assertSame('mixedCurrencies', $data['items'][0]['unavailable']);
        $this->assertSame(['mixedValuesOmitted'], $data['items'][0]['notes']);
        $this->assertSame([], (array) $data['items'][0]['progress']);
    }

    public function testProgressLinesOfTheShownCategories(): void
    {
        $definition = $this->summaries(['progressLines' => ['MIN', 'AVG', 'MAX'], 'items' => [['type' => 'bar',
            'aggregate' => 'SUM:grandTotal'], ['type' => 'pie', 'aggregate' => 'SUM:grandTotal']]]);
        $data = $this->builder->build($definition, self::result([
            self::node('Draft', 1, self::money('19500.00')), self::node('Sent', 1, self::money('1000.50')),
            self::node(null, 1, ['v' => null, 'f' => '']), self::node('Paid', 1, self::money('7.77')),
        ]));
        $progress = (array) $data['items'][0]['progress'];

        $this->assertSame(['19500', '1000.5', '1000.5', '7.77'], array_map(fn ($c) => $c['v'], $progress['MIN']));
        $this->assertSame(['19500', '10250.25', '10250.25', '6836.09'], array_map(fn ($c) => $c['v'], $progress['AVG']));
        $this->assertSame(['19500', '19500', '19500', '19500'], array_map(fn ($c) => $c['v'], $progress['MAX']));
        $this->assertSame('AVG 10250.25 RUB', $progress['AVG'][1]['f']);
        // Pies draw no progress lines.
        $this->assertSame([], (array) $data['items'][1]['progress']);
    }

    public function testProgressLinesRunningValues(): void
    {
        $lines = ProgressLines::compute([null, Decimal::of('10'), Decimal::of('1'), null, Decimal::of('7')],
            ['MIN', 'AVG', 'MAX']);

        $this->assertSame([null, '10', '1', '1', '1'], array_map(fn ($d) => $d?->toString(), $lines['MIN']));
        $this->assertSame([null, '10', '5.5', '5.5', '6'], array_map(fn ($d) => $d?->toString(), $lines['AVG']));
        $this->assertSame([null, '10', '10', '10', '10'], array_map(fn ($d) => $d?->toString(), $lines['MAX']));
        // A running average of a plain mean, 8 decimals rounded half away from zero: 2 / 7.
        $this->assertDecimal('0.28571429', ProgressLines::compute(array_merge(array_fill(0, 6, Decimal::of('0')),
            [Decimal::of('2')]), ['AVG'])['AVG'][6]);
    }
}
