<?php

declare(strict_types=1);

namespace Itvolga\Tests\Reports;

use Espo\Modules\Itvolga\Tools\Report\Core\Definition\DefinitionError;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\DefinitionParser;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\FieldForbidden;
use Itvolga\Tests\Finance\TestCase;

/**
 * Rules of the charts and dashboard parts (D-105, D-106, D-109): canonical form, chart types and aggregates, the
 * axis «group 1 → group 2», the main filter field of a dashlet and the quick filter it becomes in a run.
 */
final class ChartSettingsTest extends TestCase
{
    private FakeSchema $schema;
    private DefinitionParser $parser;

    public function setUp(): void
    {
        $this->schema = new FakeSchema();
        $this->parser = new DefinitionParser($this->schema);
    }

    /**
     * @param array<string, mixed> $extra
     * @return array<string, mixed>
     */
    private static function summaries(array $extra = [], int $levels = 1): array
    {
        $groups = [['field' => 'status'], ['field' => 'account'], ['field' => 'dateInvoiced', 'granularity' => 'month']];

        return $extra + ['type' => 'summaries', 'entityType' => 'Invoice', 'groups' => array_slice($groups, 0, $levels),
            'aggregates' => [['function' => 'SUM', 'field' => 'grandTotal']]];
    }

    private function refused(array $attributes, string $key, ?string $path = null): void
    {
        $error = $this->assertThrows(DefinitionError::class, fn () => $this->parser->parse($attributes));
        assert($error instanceof DefinitionError);
        $this->assertSame($key, $error->key, 'error key');

        if ($path !== null) {
            $this->assertSame($path, $error->path, 'error path');
        }
    }

    public function testEmptyPartsAreStoredAsDefaults(): void
    {
        $attributes = $this->parser->parse(self::summaries())->toAttributes();

        $this->assertSame(['title' => '', 'position' => 'top', 'collapseTable' => false, 'axis' => 'group1',
            'progressLines' => [], 'items' => []], $attributes['charts']);
        $this->assertSame(['filterField' => null, 'mode' => 'table'], $attributes['dashboard']);

        $tabular = $this->parser->parse(['type' => 'tabular', 'entityType' => 'Invoice', 'columns' => ['name'],
            'charts' => ['title' => 'x'], 'dashboard' => null])->toAttributes();
        $this->assertSame([], $tabular['charts']['items']);
        $this->assertSame('', $tabular['charts']['title']);
    }

    public function testChartsAreNormalised(): void
    {
        $definition = $this->parser->parse(self::summaries(['charts' => [
            'title' => '  Суммы  ', 'position' => 'bottom', 'collapseTable' => true,
            'progressLines' => ['MAX', 'MIN', 'MAX'],
            'items' => [['type' => 'bar', 'aggregate' => 'SUM:grandTotal'], ['type' => 'line'],
                ['type' => 'piePercent', 'aggregate' => 'COUNT']],
        ]]));
        $charts = $definition->toAttributes()['charts'];

        $this->assertSame('Суммы', $charts['title']);
        $this->assertSame('bottom', $charts['position']);
        $this->assertSame(true, $charts['collapseTable']);
        $this->assertSame(['MIN', 'MAX'], $charts['progressLines']);
        $this->assertSame([['type' => 'bar', 'aggregate' => 'SUM:grandTotal'], ['type' => 'line', 'aggregate' => 'COUNT'],
            ['type' => 'piePercent', 'aggregate' => 'COUNT']], $charts['items']);
        // With charts the dashlet shows the chart unless the report says otherwise.
        $this->assertSame('chart', $definition->toAttributes()['dashboard']['mode']);
    }

    public function testChartRulesAreEnforced(): void
    {
        $this->refused(['type' => 'tabular', 'entityType' => 'Invoice', 'columns' => ['name'],
            'charts' => ['items' => [['type' => 'bar']]]], 'notForType', 'charts');
        $this->refused(self::summaries(['charts' => ['items' => array_fill(0, 4, ['type' => 'bar'])]]), 'tooMany',
            'charts.items');
        $this->refused(self::summaries(['charts' => ['items' => [['type' => 'pie3d']]]]), 'badChartType',
            'charts.items[0].type');
        $this->refused(self::summaries(['charts' => ['items' => [['type' => 'bar', 'aggregate' => 'AVG:grandTotal']]]]),
            'badChartAggregate', 'charts.items[0].aggregate');
        $this->refused(self::summaries(['charts' => ['position' => 'left']]), 'badChart', 'charts.position');
        $this->refused(self::summaries(['charts' => ['axis' => 'group3']]), 'badChart', 'charts.axis');
        $this->refused(self::summaries(['charts' => ['progressLines' => ['MEDIAN']]]), 'badChart',
            'charts.progressLines');
        $this->refused(self::summaries(['charts' => ['collapseTable' => 'yes']]), 'badChart', 'charts.collapseTable');
        $this->refused(self::summaries(['charts' => ['title' => str_repeat('я', 151)]]), 'badLabel', 'charts.title');
        $this->refused(self::summaries(['charts' => [['type' => 'bar']]]), 'badStructure', 'charts');
    }

    public function testSecondGroupAxisNeedsTwoGroupsAndOneChart(): void
    {
        $axis = fn (array $items, array $extra = []) => ['charts' => ['axis' => 'group1group2', 'items' => $items] + $extra];

        $this->refused(self::summaries($axis([['type' => 'stackedBar']])), 'chartAxisNotAllowed', 'charts.axis');
        $this->refused(['type' => 'summariesWithDetails', 'entityType' => 'Invoice', 'groups' => [['field' => 'status']],
            'columns' => ['name'], 'aggregates' => [['function' => 'COUNT']]] + $axis([['type' => 'bar']]),
            'chartAxisNotAllowed');
        $this->refused(self::summaries($axis([['type' => 'bar'], ['type' => 'line']]), 2), 'chartAxisOneChart');
        $this->refused(self::summaries($axis([['type' => 'funnel']]), 2), 'chartFunnelSecondGroup',
            'charts.items[0].type');
        $this->refused(self::summaries($axis([['type' => 'bar']], ['progressLines' => ['AVG']]), 2),
            'chartProgressSecondGroup');

        $summaries = $this->parser->parse(self::summaries($axis([['type' => 'pie']]), 3));
        $this->assertSame('group1group2', $summaries->toAttributes()['charts']['axis']);

        $matrix = $this->parser->parse(['type' => 'matrix', 'entityType' => 'Invoice',
            'groups' => [['field' => 'status'], ['field' => 'dateInvoiced', 'granularity' => 'month']],
            'aggregates' => [['function' => 'COUNT']]] + $axis([['type' => 'stackedHorizontalBar']]));
        $this->assertSame('stackedHorizontalBar', $matrix->toAttributes()['charts']['items'][0]['type']);
    }

    public function testDashboardFilterFieldIsAnEnumOrTheOwner(): void
    {
        foreach (['status', 'assignedUser'] as $field) {
            $definition = $this->parser->parse(self::summaries(['dashboard' => ['filterField' => $field,
                'mode' => 'table']]));
            $this->assertSame(['filterField' => $field, 'mode' => 'table'], $definition->toAttributes()['dashboard']);
        }

        foreach (['name', 'account', 'account.industry', 'paid', 'cTags'] as $field) {
            $this->refused(self::summaries(['dashboard' => ['filterField' => $field]]), 'badDashboardFilter',
                'dashboard.filterField');
        }

        $this->refused(self::summaries(['dashboard' => ['filterField' => 'gone']]), 'unknownField');
        $this->assertThrows(FieldForbidden::class, fn () => $this->parser->parse(self::summaries(['dashboard' =>
            ['filterField' => 'secretNote']])));
        $this->refused(self::summaries(['dashboard' => ['mode' => 'map']]), 'badDashboardMode', 'dashboard.mode');
        $this->refused(['type' => 'tabular', 'entityType' => 'Invoice', 'columns' => ['name'],
            'dashboard' => ['mode' => 'chart']], 'notForType', 'dashboard.mode');
    }

    public function testMainFilterIsAQuickFilterOfTheDashboardField(): void
    {
        $definition = $this->parser->parse(self::summaries(['dashboard' => ['filterField' => 'assignedUser']]));
        [, $options] = $this->parser->parseRun($definition, ['quickFilters' => [['field' => 'assignedUser',
            'mode' => 'in', 'values' => ['u1']]], 'withDashboardFilterOptions' => true]);

        $this->assertSame('assignedUser', $options->quickFilters[0]->field->ref->toString());
        $this->assertSame(true, $options->withDashboardFilterOptions);

        $error = $this->assertThrows(DefinitionError::class, fn () => $this->parser->parseRun($definition,
            ['quickFilters' => [['field' => 'status', 'mode' => 'in', 'values' => ['Sent']]]]));
        assert($error instanceof DefinitionError);
        $this->assertSame('badQuickFilter', $error->key);

        [, $plain] = $this->parser->parseRun($definition, []);
        $this->assertSame(false, $plain->withDashboardFilterOptions);
    }
}
