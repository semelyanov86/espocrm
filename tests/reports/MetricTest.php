<?php

declare(strict_types=1);

namespace Itvolga\Tests\Reports;

use Espo\Modules\Itvolga\Tools\Report\Core\Dashboard\DashboardPruner;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\DefinitionError;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\DefinitionParser;
use Espo\Modules\Itvolga\Tools\Report\Core\Metric\MetricRow;
use Espo\Modules\Itvolga\Tools\Report\Core\Metric\MetricRowsParser;
use Espo\Modules\Itvolga\Tools\Report\Core\Metric\MetricRules;
use Itvolga\Tests\Finance\TestCase;

/**
 * Key metrics (D-111…D-113): rows of a set (ids, canonical form, sources, limits), the aggregate a report metric
 * computes (tabular, numeric column, the to-many rule), and the removal of a set's dashlets from a dashboard.
 */
final class MetricTest extends TestCase
{
    private DefinitionParser $parser;

    public function setUp(): void
    {
        $this->parser = new DefinitionParser(new FakeSchema());
    }

    private function refused(mixed $rows, string $key, ?string $path = null): void
    {
        $error = $this->assertThrows(DefinitionError::class, fn () => MetricRowsParser::parse($rows));
        assert($error instanceof DefinitionError);
        $this->assertSame($key, $error->key, 'error key');

        if ($path !== null) {
            $this->assertSame($path, $error->path, 'error path');
        }
    }

    public function testRowsAreNormalised(): void
    {
        $rows = MetricRowsParser::parse([
            ['id' => 'm2', 'label' => ' Сумма ', 'source' => 'report', 'reportId' => 'abc123', 'function' => 'SUM',
                'column' => 'grandTotal'],
            ['label' => 'Число', 'source' => 'report', 'reportId' => 'abc123'],
            ['id' => 'm2', 'label' => 'Открытые', 'source' => 'filter', 'entityType' => 'Opportunity',
                'filter' => ['kind' => 'system', 'name' => 'open'], 'where' => [['type' => 'equals']]],
            ['label' => 'Мой фильтр', 'source' => 'filter', 'entityType' => 'Invoice',
                'filter' => ['kind' => 'preset', 'name' => 'Неоплаченные'],
                'where' => [['type' => 'equals', 'attribute' => 'status', 'value' => 'Sent']]],
        ]);

        $this->assertSame(['m2', 'm1', 'm3', 'm4'], array_map(fn (MetricRow $r) => $r->id, $rows));
        $this->assertSame(['id' => 'm2', 'label' => 'Сумма', 'source' => 'report', 'reportId' => 'abc123',
            'function' => 'SUM', 'column' => 'grandTotal'], $rows[0]->toArray());
        $this->assertSame('COUNT', $rows[1]->function);
        $this->assertSame(null, $rows[1]->column);
        // A system filter is its primary where item, whatever the client sent.
        $this->assertSame([['type' => 'primary', 'value' => 'open']], $rows[2]->where);
        $this->assertSame(['kind' => 'preset', 'name' => 'Неоплаченные'], $rows[3]->filter);
        $this->assertSame('Sent', $rows[3]->where[0]['value']);
        $this->assertSame($rows[0]->sourceKey(), MetricRowsParser::parse([['id' => 'm7', 'label' => 'Другая',
            'source' => 'report', 'reportId' => 'abc123', 'function' => 'SUM', 'column' => 'grandTotal']])[0]->sourceKey());
        $this->assertSame([], MetricRowsParser::parse(null));
    }

    public function testRowsAreChecked(): void
    {
        $report = ['label' => 'x', 'source' => 'report', 'reportId' => 'abc'];
        $filter = ['label' => 'x', 'source' => 'filter', 'entityType' => 'Invoice',
            'filter' => ['kind' => 'preset', 'name' => 'p'], 'where' => []];

        $this->refused(['label' => 'x'], 'badStructure', 'rows');
        $this->refused(array_fill(0, 31, $report), 'tooMany', 'rows');
        $this->refused([['label' => ' '] + $report], 'metricLabelRequired', 'rows[0].label');
        $this->refused([['source' => 'sql'] + $report], 'badMetricSource', 'rows[0].source');
        $this->refused([['reportId' => '../x'] + $report], 'badMetricSource', 'rows[0].reportId');
        $this->refused([['function' => 'MEDIAN'] + $report], 'badMetric', 'rows[0].function');
        $this->refused([['column' => 'grandTotal'] + $report], 'badMetric', 'rows[0].column');
        $this->refused([['function' => 'SUM'] + $report], 'badMetric', 'rows[0].column');
        $this->refused([['entityType' => 'invoice'] + $filter], 'badMetricSource', 'rows[0].entityType');
        $this->refused([['function' => 'SUM'] + $filter], 'badMetric', 'rows[0].function');
        $this->refused([['filter' => ['kind' => 'system', 'name' => 'a b']] + $filter], 'badMetricFilter',
            'rows[0].filter');
        $this->refused([['where' => [['value' => 1]]] + $filter], 'badMetricFilter', 'rows[0].where');
        $this->refused([['where' => [['type' => 'equals', 'attribute' => 'name', 'value' => str_repeat('x', 9000)]]] +
            $filter], 'metricFilterTooLarge', 'rows[0].where');
    }

    public function testReportMetricAggregate(): void
    {
        $tabular = $this->parser->parse(['type' => 'tabular', 'entityType' => 'Invoice',
            'columns' => ['name', 'grandTotal', 'account.cEmployees']]);

        $this->assertSame('COUNT', MetricRules::aggregate($tabular, 'COUNT', null)->key());
        $this->assertSame('AVG:grandTotal', MetricRules::aggregate($tabular, 'AVG', 'grandTotal')->key());
        $this->assertSame('MAX:account.cEmployees', MetricRules::aggregate($tabular, 'MAX', 'account.cEmployees')->key());

        foreach ([['SUM', 'name', 'metricBadColumn'], ['SUM', 'dateDue', 'metricBadColumn'],
            ['COUNT', 'grandTotal', 'badMetric'], ['MEDIAN', 'grandTotal', 'badMetric']] as [$fn, $column, $key]) {
            $error = $this->assertThrows(DefinitionError::class, fn () => MetricRules::aggregate($tabular, $fn, $column));
            $this->assertSame($key, $error->key);
        }

        // With a to-many link only its fields are summed (D-90): a main field would be repeated per line.
        $lines = $this->parser->parse(['type' => 'tabular', 'entityType' => 'Invoice',
            'columns' => ['name', 'grandTotal', 'items.amount']]);
        $this->assertSame('SUM:items.amount', MetricRules::aggregate($lines, 'SUM', 'items.amount')->key());
        $error = $this->assertThrows(DefinitionError::class, fn () => MetricRules::aggregate($lines, 'SUM', 'grandTotal'));
        $this->assertSame('aggregateMultiplied', $error->key);

        $summaries = $this->parser->parse(['type' => 'summaries', 'entityType' => 'Invoice',
            'groups' => [['field' => 'status']], 'aggregates' => [['function' => 'COUNT']]]);
        $error = $this->assertThrows(DefinitionError::class, fn () => MetricRules::aggregate($summaries, 'COUNT', null));
        $this->assertSame('metricNotTabular', $error->key);
    }

    public function testDashboardPrunerRemovesTheTargetDashletsOfAllTabs(): void
    {
        $layout = [
            ['name' => 'Мой', 'id' => 't1', 'layout' => [
                ['id' => 'd1', 'name' => 'ReportMetrics', 'x' => 0], ['id' => 'd2', 'name' => 'Stream', 'x' => 2],
                ['id' => 'd3', 'name' => 'ReportMetrics', 'x' => 4], 'broken',
            ]],
            ['name' => 'Второй', 'layout' => [['id' => 'd4', 'name' => 'ReportMetrics']]],
            ['name' => 'Пустой'],
        ];
        $options = ['d1' => ['metricSetId' => 'S'], 'd2' => ['title' => 'x'], 'd3' => ['metricSetId' => 'OTHER'],
            'd4' => ['metricSetId' => 'S', 'title' => 'y']];
        $isTarget = fn (string $name, array $o) => $name === 'ReportMetrics' && ($o['metricSetId'] ?? null) === 'S';

        [$newLayout, $newOptions, $removed] = DashboardPruner::prune($layout, $options, $isTarget);

        $this->assertSame(['d1', 'd4'], $removed);
        $this->assertSame(['d2', 'd3'], array_map(fn ($i) => $i['id'], array_slice($newLayout[0]['layout'], 0, 2)));
        $this->assertSame('broken', $newLayout[0]['layout'][2]);
        $this->assertSame([], $newLayout[1]['layout']);
        $this->assertSame(['name' => 'Пустой'], $newLayout[2]);
        $this->assertSame(['d2', 'd3'], array_keys($newOptions));
        $this->assertSame(null, DashboardPruner::prune($newLayout, $newOptions, $isTarget));
        $this->assertSame(null, DashboardPruner::prune(null, null, $isTarget));
    }
}
