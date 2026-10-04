<?php

declare(strict_types=1);

namespace Itvolga\Tests\Reports;

use Espo\Modules\Itvolga\Tools\Report\Core\Definition\DefinitionError;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\DefinitionParser;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\FieldForbidden;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\ReportType;
use Itvolga\Tests\Finance\TestCase;

/**
 * Rules of report definitions (reports.md §2–§4, D-90, D-99): parts per type, cross-references, field capabilities,
 * the single to-many link, and that every section sends its fields through the Schema (where ACL is checked).
 */
final class DefinitionParserTest extends TestCase
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
    private static function tabular(array $extra = []): array
    {
        return $extra + ['type' => 'tabular', 'entityType' => 'Invoice', 'columns' => ['name', 'grandTotal'],
            'rowLimit' => 20];
    }

    /**
     * @param array<string, mixed> $extra
     * @return array<string, mixed>
     */
    private static function summaries(array $extra = []): array
    {
        return $extra + ['type' => 'summaries', 'entityType' => 'Invoice',
            'groups' => [['field' => 'status', 'direction' => 'asc']],
            'aggregates' => [['function' => 'COUNT'], ['function' => 'SUM', 'field' => 'grandTotal']]];
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

    public function testTabularDefinitionIsNormalised(): void
    {
        $definition = $this->parser->parse(self::tabular([
            'columns' => ['name', 'account.name', 'grandTotal', 'name'],
            'sorting' => [['column' => 'grandTotal', 'direction' => 'desc']],
            'totals' => [['column' => 'grandTotal', 'functions' => ['MAX', 'SUM']]],
            'calculations' => [['label' => ' Двойная ', 'expression' => '{grandTotal} * 2', 'functions' => ['SUM']]],
            'labels' => ['c:grandTotal' => 'Итого', 'c:gone' => 'x', 'k:k1' => '  '],
        ]));

        $this->assertSame(ReportType::TABULAR, $definition->type);
        $attributes = $definition->toAttributes();
        $this->assertSame(['name', 'account.name', 'grandTotal'], $attributes['columns']);
        $this->assertSame([['column' => 'grandTotal', 'functions' => ['SUM', 'MAX']]], $attributes['totals']);
        $this->assertSame('Двойная', $attributes['calculations'][0]['label']);
        $this->assertSame('k1', $attributes['calculations'][0]['id']);
        $this->assertSame(['c:grandTotal' => 'Итого'], (array) $attributes['labels']);
        $this->assertSame(['type' => 'and', 'items' => []], $attributes['filters']);
        $this->assertSame(null, $definition->manyLink);
    }

    public function testPartsOfEachType(): void
    {
        $this->refused(self::tabular(['columns' => []]), 'columnsRequired');
        $this->refused(self::tabular(['groups' => [['field' => 'status']]]), 'notForType', 'groups');
        $this->refused(self::tabular(['aggregates' => [['function' => 'COUNT']]]), 'notForType', 'aggregates');
        $this->refused(self::summaries(['aggregates' => []]), 'aggregatesRequired');
        $this->refused(self::summaries(['groups' => []]), 'groupsRequired');
        $this->refused(self::summaries(['columns' => ['name']]), 'notForType', 'columns');
        $this->refused(self::summaries(['calculations' => [['label' => 'x', 'expression' => '1']]]), 'notForType');
        $this->refused(self::summaries(['type' => 'matrix']), 'matrixNeedsTwoGroups');
        $this->refused(self::summaries(['type' => 'summariesWithDetails', 'columns' => ['name'],
            'groups' => [['field' => 'status'], ['field' => 'account']]]), 'groupsRequired');
        $this->refused(self::summaries(['type' => 'summariesWithDetails']), 'columnsRequired');
        $this->refused(self::summaries(['groups' => array_fill(0, 4, ['field' => 'status'])]), 'tooMany');
        $this->refused(self::summaries(['type' => 'pivot']), 'badType');
        $this->refused(self::summaries(['entityType' => 'invoice; drop']), 'badEntityType');

        $matrix = $this->parser->parse(self::summaries(['type' => 'matrix', 'groups' => [['field' => 'status'],
            ['field' => 'dateInvoiced', 'granularity' => 'month']]]));
        $this->assertSame('month', $matrix->groups[1]->granularity?->value);
    }

    public function testGroupsAggregatesAndHaving(): void
    {
        $this->refused(self::summaries(['groups' => [['field' => 'status', 'granularity' => 'month']]]),
            'badGranularity');
        $this->refused(self::summaries(['groups' => [['field' => 'dateInvoiced', 'granularity' => 'decade']]]),
            'badGranularity');
        $this->refused(self::summaries(['groups' => [['field' => 'description']]]), 'fieldNotForGroup');
        $this->refused(self::summaries(['groups' => [['field' => 'status'], ['field' => 'status']]]),
            'duplicateGroup');
        $this->refused(self::summaries(['aggregates' => [['function' => 'SUM', 'field' => 'name']]]),
            'aggregateNotNumeric');
        $this->refused(self::summaries(['aggregates' => [['function' => 'COUNT', 'field' => 'grandTotal']]]),
            'badAggregate');
        $this->refused(self::summaries(['aggregates' => [['function' => 'MEDIAN', 'field' => 'grandTotal']]]),
            'badAggregate');
        $this->refused(self::summaries(['groupSort' => ['aggregate' => 'AVG:grandTotal']]), 'badGroupSort');
        $this->refused(self::summaries(['havingFilters' => [['aggregate' => 'COUNT', 'operator' => 'greaterThan',
            'value' => '1e3']]]), 'badHavingValue');
        $this->refused(self::summaries(['havingFilters' => [['aggregate' => 'SUM:grandTotal', 'operator' => 'like',
            'value' => '1']]]), 'badHaving');

        $definition = $this->parser->parse(self::summaries([
            'groups' => [['field' => 'dateInvoiced'], ['field' => 'account', 'direction' => 'desc']],
            'groupSort' => ['aggregate' => 'SUM:grandTotal', 'direction' => 'desc'], 'groupLimit' => 2,
            'havingFilters' => [['aggregate' => 'SUM:grandTotal', 'operator' => 'between', 'value' => ['10', '20.5']]],
        ]));
        $this->assertSame('day', $definition->groups[0]->granularity?->value);
        $this->assertSame('SUM:grandTotal', $definition->groupSort['aggregate']->key());
        $this->assertSame(2, $definition->groupLimit);
        $this->assertSame(['COUNT', 'SUM:grandTotal'], array_map(fn ($a) => $a->key(), $definition->aggregates));
    }

    public function testSingleToManyLinkAndMultipliedAggregatesAreRefused(): void
    {
        $definition = $this->parser->parse(self::summaries(['groups' => [['field' => 'items.product']],
            'aggregates' => [['function' => 'COUNT'], ['function' => 'SUM', 'link' => 'items', 'field' => 'amount']]]));
        $this->assertSame('items', $definition->manyLink);

        $this->refused(self::summaries(['groups' => [['field' => 'items.product']]]), 'aggregateMultiplied');
        $this->refused(self::tabular(['columns' => ['items.amount', 'contacts.lastName']]), 'oneManyLink');
        $this->refused(self::tabular(['columns' => ['items.amount', 'grandTotal'],
            'totals' => [['column' => 'grandTotal', 'functions' => ['SUM']]]]), 'aggregateMultiplied');
        $this->refused(self::tabular(['columns' => ['items.amount', 'grandTotal'],
            'calculations' => [['label' => 'x', 'expression' => '{grandTotal}', 'functions' => ['SUM']]]]),
            'aggregateMultiplied');

        $tabular = $this->parser->parse(self::tabular(['columns' => ['name', 'items.amount'],
            'totals' => [['column' => 'items.amount', 'functions' => ['SUM']]]]));
        $this->assertSame('items', $tabular->manyLink);
    }

    public function testCalculationErrorsCarryPositionAndLabel(): void
    {
        $error = $this->assertThrows(DefinitionError::class, fn () => $this->parser->parse(self::tabular([
            'calculations' => [['label' => 'Ставка', 'expression' => '{grandTotal} * ', 'functions' => []]]])));
        assert($error instanceof DefinitionError);
        $this->assertSame(['calculationUnexpectedEnd', 'calculations[0].expression'], [$error->key, $error->path]);
        $this->assertSame(['position' => 16, 'label' => 'Ставка'], $error->params);

        $this->refused(self::tabular(['calculations' => [['label' => 'x', 'expression' => '{name} + 1']]]),
            'calculationBadReference');
        $this->refused(self::tabular(['calculations' => [['label' => 'x', 'expression' => '{dateDue} + 1']]]),
            'calculationBadReference');
        $this->refused(self::tabular(['calculations' => [['label' => '', 'expression' => '1']]]),
            'calculationLabelRequired');
    }

    public function testConditionsAreCheckedByFieldFamily(): void
    {
        $filters = ['type' => 'or', 'items' => [
            ['field' => 'status', 'where' => ['type' => 'in', 'attribute' => 'status', 'value' => ['Paid']],
                'advanced' => ['type' => 'anyOf', 'valueList' => ['Paid']]],
            ['type' => 'and', 'items' => [
                ['field' => 'account.industry', 'where' => ['type' => 'or', 'value' => [
                    ['type' => 'isNull', 'attribute' => 'industry'],
                    ['type' => 'equals', 'attribute' => 'industry', 'value' => '']]]],
                ['field' => 'dateInvoiced', 'where' => ['type' => 'currentWeek', 'attribute' => 'dateInvoiced']],
                ['field' => 'createdAt', 'where' => ['type' => 'xDaysAgo', 'attribute' => 'createdAt', 'value' => '3']],
                ['field' => 'assignedUser', 'where' => ['type' => 'isCurrentUser', 'attribute' => 'assignedUserId']],
                ['field' => 'dateDue', 'where' => ['type' => 'compareField', 'attribute' => 'dateDue',
                    'value' => ['operator' => 'lessThan', 'field' => 'dateInvoiced']]],
            ]],
        ]];
        $definition = $this->parser->parse(self::tabular(['filters' => $filters]));
        $tree = $definition->filters;

        $this->assertSame('or', $tree['type']);
        $this->assertSame(['type' => 'currentWeek', 'attribute' => 'dateInvoiced', 'date' => true],
            $tree['items'][1]['items'][1]['where']);
        $this->assertSame(['type' => 'xDaysAgo', 'attribute' => 'createdAt', 'value' => 3, 'dateTime' => true],
            $tree['items'][1]['items'][2]['where']);
        $this->assertSame(['status', 'account.industry', 'dateInvoiced', 'createdAt', 'assignedUser', 'dateDue'],
            array_keys($definition->filterFields));

        $bad = fn (array $where, string $field = 'status') => self::tabular(['filters' => ['type' => 'and',
            'items' => [['field' => $field, 'where' => $where]]]]);
        $this->refused($bad(['type' => 'expression', 'attribute' => 'status']), 'operatorNotAllowed');
        $this->refused($bad(['type' => 'equals', 'attribute' => 'name', 'value' => 'x']), 'badCondition');
        $this->refused($bad(['type' => 'equals', 'attribute' => 'CONCAT:(status)', 'value' => 'x']), 'badCondition');
        $this->refused($bad(['type' => 'subQueryIn', 'value' => []]), 'operatorNotAllowed');
        $this->refused($bad(['type' => 'isCurrentUser', 'attribute' => 'accountId'], 'account'), 'operatorNotAllowed');
        $this->refused($bad(['type' => 'lastXDays', 'attribute' => 'dateDue', 'value' => '-1'], 'dateDue'),
            'badConditionValue');
        $this->refused($bad(['type' => 'greaterThan', 'attribute' => 'grandTotal', 'value' => '1 OR 1'],
            'grandTotal'), 'badConditionValue');
        $this->refused($bad(['type' => 'on', 'attribute' => 'dateDue', 'value' => 'yesterday'], 'dateDue'),
            'badConditionValue');
        $this->refused($bad(['type' => 'compareField', 'attribute' => 'dateDue',
            'value' => ['operator' => 'lessThan', 'field' => 'createdAt']], 'dateDue'), 'badCompareField');
        $this->refused($bad(['type' => 'compareField', 'attribute' => 'dateDue',
            'value' => ['operator' => 'lessThan', 'field' => 'account.createdAt']], 'dateDue'), 'badConditionValue');
        $this->refused($bad(['type' => 'linkedWith', 'attribute' => 'teams', 'value' => ['t1']], 'items.product'),
            'operatorNotAllowed');
        $nested = ['type' => 'or', 'value' => [['type' => 'or', 'value' => [['type' => 'or', 'value' => []]]]]];
        $this->refused($bad($nested), 'badCondition');
    }

    public function testEverySectionChecksItsFieldsThroughTheSchema(): void
    {
        $where = fn (string $field) => ['type' => 'and', 'items' => [['field' => $field,
            'where' => ['type' => 'isNotNull', 'attribute' => $field === 'secretNote' ? 'secretNote' : 'secretInn']]]];
        $cases = [
            self::tabular(['columns' => ['name', 'secretNote']]),
            self::tabular(['columns' => ['name', 'account.secretInn']]),
            self::summaries(['groups' => [['field' => 'account.secretInn']]]),
            self::summaries(['aggregates' => [['function' => 'SUM', 'link' => 'account', 'field' => 'secretInn']]]),
            self::tabular(['filters' => $where('secretNote')]),
            self::tabular(['filters' => $where('account.secretInn')]),
            self::tabular(['quickFilters' => ['secretNote']]),
            self::tabular(['entityType' => 'Secret']),
            self::tabular(['filters' => ['type' => 'and', 'items' => [['field' => 'dateDue', 'where' => [
                'type' => 'compareField', 'attribute' => 'dateDue',
                'value' => ['operator' => 'equals', 'field' => 'secretDate']]]]]]),
        ];

        foreach ($cases as $i => $attributes) {
            $this->assertThrows(FieldForbidden::class, fn () => $this->parser->parse($attributes), null);
            $this->assertTrue(true, "case $i");
        }

        $this->refused(self::tabular(['columns' => ['vtigerData']]), 'unknownField');
        $this->refused(self::tabular(['columns' => ['nope.name']]), 'unknownField');
        $this->refused(self::tabular(['columns' => ['account.name.x']]), 'badField');
        $this->refused(self::tabular(['columns' => ['teams']]), 'fieldNotForColumn');
        $this->refused(self::tabular(['quickFilters' => ['items.name']]), 'fieldNotForQuickFilter');
    }

    public function testRunParametersReplaceConditionsAndKeepQuickFiltersOfTheReport(): void
    {
        $definition = $this->parser->parse(self::tabular(['quickFilters' => ['status', 'account']]));
        [$run, $options] = $this->parser->parseRun($definition, [
            'offset' => 40, 'maxSize' => 20,
            'filters' => ['type' => 'and', 'items' => [['field' => 'paid', 'where' => ['type' => 'isTrue',
                'attribute' => 'paid']]]],
            'quickFilters' => [['field' => 'status', 'mode' => 'notIn', 'values' => ['Draft'], 'includeEmpty' => true],
                ['field' => 'account', 'values' => [], 'includeEmpty' => false]],
        ]);

        $this->assertSame(['paid'], array_keys($run->filterFields));
        $this->assertSame([40, 20, 1], [$options->offset, $options->maxSize, count($options->quickFilters)]);
        $this->assertSame('notIn', $options->quickFilters[0]->mode);

        $badRun = fn (array $raw) => $this->assertThrows(DefinitionError::class,
            fn () => $this->parser->parseRun($definition, $raw));
        $badRun(['quickFilters' => [['field' => 'name', 'values' => ['x']]]]);
        $badRun(['maxSize' => 1000]);
        $badRun(['offset' => -1]);
        $badRun(['quickFilters' => [['field' => 'status', 'values' => [['nested']]]]]);
        $this->assertThrows(FieldForbidden::class, fn () => $this->parser->parseRun($definition, ['filters' => [
            'type' => 'and', 'items' => [['field' => 'secretNote', 'where' => ['type' => 'isNull',
                'attribute' => 'secretNote']]]]]));
    }
}
