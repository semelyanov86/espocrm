<?php

declare(strict_types=1);

namespace Itvolga\Tests\Reports;

use DateTimeImmutable;
use DateTimeZone;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\DefinitionParser;
use Espo\Modules\Itvolga\Tools\Report\Core\Filter\RelativePeriod;
use Espo\Modules\Itvolga\Tools\Report\Core\Filter\RunContext;
use Espo\Modules\Itvolga\Tools\Report\Core\Filter\WhereTranslator;
use Itvolga\Tests\Finance\TestCase;

/**
 * Relative periods resolve in the run's time zone (D-92) and conditions become core where items (reports.md §4).
 */
final class PeriodTest extends TestCase
{
    /** 2026-10-04 23:30 UTC = Monday 2026-10-05 03:30 in Samara (UTC+4). */
    private static function context(int $fiscalShift = 0, string $zone = 'Europe/Samara'): RunContext
    {
        return new RunContext(new DateTimeImmutable('2026-10-04 23:30:00', new DateTimeZone('UTC')), $zone, 'u1',
            $fiscalShift);
    }

    public function testCalendarPeriodsInTheUsersTimeZone(): void
    {
        $c = self::context();
        $expect = [
            'today' => ['range', '2026-10-05', '2026-10-05'], 'yesterday' => ['range', '2026-10-04', '2026-10-04'],
            'tomorrow' => ['range', '2026-10-06', '2026-10-06'], 'past' => ['before', '2026-10-05', null],
            'currentWeek' => ['range', '2026-10-05', '2026-10-11'], 'lastWeek' => ['range', '2026-09-28', '2026-10-04'],
            'nextWeek' => ['range', '2026-10-12', '2026-10-18'], 'currentMonth' => ['range', '2026-10-01', '2026-10-31'],
            'lastMonth' => ['range', '2026-09-01', '2026-09-30'], 'nextMonth' => ['range', '2026-11-01', '2026-11-30'],
            'currentQuarter' => ['range', '2026-10-01', '2026-12-31'], 'lastQuarter' => ['range', '2026-07-01', '2026-09-30'],
            'nextQuarter' => ['range', '2027-01-01', '2027-03-31'], 'currentYear' => ['range', '2026-01-01', '2026-12-31'],
            'lastYear' => ['range', '2025-01-01', '2025-12-31'], 'nextYear' => ['range', '2027-01-01', '2027-12-31'],
            'lastSevenDays' => ['range', '2026-09-28', '2026-10-05'],
        ];

        foreach ($expect as $type => $range) {
            $this->assertSame($range, RelativePeriod::resolve($type, null, $c), $type);
        }

        $this->assertSame(['range', '2026-10-04', '2026-10-04'],
            RelativePeriod::resolve('today', null, self::context(0, 'UTC')), 'UTC today');
        $this->assertSame(['range', '2026-10-02', '2026-10-02'], RelativePeriod::resolve('xDaysAgo', 3, $c));
        $this->assertSame(['range', '2026-10-08', '2026-10-08'], RelativePeriod::resolve('inXDays', 3, $c));
        $this->assertSame(['range', '2026-09-25', '2026-10-05'], RelativePeriod::resolve('lastXDays', 10, $c));
        $this->assertSame(['before', '2026-09-25', null], RelativePeriod::resolve('olderThanXDays', 10, $c));
        $this->assertSame(['after', '2026-10-15', null], RelativePeriod::resolve('afterXDays', 10, $c));
    }

    public function testFiscalYearAndQuarterFollowTheShift(): void
    {
        $april = self::context(3);
        $this->assertSame(['range', '2026-04-01', '2027-03-31'], RelativePeriod::resolve('currentFiscalYear', null, $april));
        $this->assertSame(['range', '2025-04-01', '2026-03-31'], RelativePeriod::resolve('lastFiscalYear', null, $april));
        $this->assertSame(['range', '2026-10-01', '2026-12-31'], RelativePeriod::resolve('currentFiscalQuarter', null, $april));

        $february = self::context(1);
        $this->assertSame(['range', '2026-08-01', '2026-10-31'], RelativePeriod::resolve('currentFiscalQuarter', null, $february));
        $this->assertSame(['range', '2026-05-01', '2026-07-31'], RelativePeriod::resolve('lastFiscalQuarter', null, $february));
        $this->assertSame(['range', '2026-02-01', '2027-01-31'], RelativePeriod::resolve('currentFiscalYear', null, $february));
        $this->assertSame('4', self::context()->offsetHours());
        $this->assertSame('5.5', self::context(0, 'Asia/Kolkata')->offsetHours());
    }

    public function testConditionsBecomeCoreWhereItems(): void
    {
        $parser = new DefinitionParser(new FakeSchema());
        $definition = $parser->parse(['type' => 'tabular', 'entityType' => 'Invoice', 'columns' => ['name'],
            'filters' => ['type' => 'and', 'items' => [
                ['field' => 'dateInvoiced', 'where' => ['type' => 'yesterday', 'attribute' => 'dateInvoiced']],
                ['field' => 'createdAt', 'where' => ['type' => 'currentMonth', 'attribute' => 'createdAt']],
                ['field' => 'createdAt', 'where' => ['type' => 'past', 'attribute' => 'createdAt']],
                ['type' => 'or', 'items' => [
                    ['field' => 'assignedUser', 'where' => ['type' => 'isCurrentUser', 'attribute' => 'assignedUserId']],
                    ['field' => 'account.industry', 'where' => ['type' => 'in', 'attribute' => 'industry',
                        'value' => ['IT']]],
                ]],
                ['type' => 'and', 'items' => []],
                ['field' => 'dateDue', 'where' => ['type' => 'compareField', 'attribute' => 'dateDue',
                    'value' => ['operator' => 'lessThan', 'field' => 'dateInvoiced']]],
                ['field' => 'dateDue', 'where' => ['type' => 'between', 'attribute' => 'dateDue',
                    'value' => ['2026-01-01', '2026-01-31']]],
            ]]]);

        $where = WhereTranslator::translate($definition->filters, $definition->filterFields, self::context());
        $this->assertSame(['type' => 'and', 'value' => [
            ['type' => 'on', 'attribute' => 'dateInvoiced', 'value' => '2026-10-04'],
            ['type' => 'between', 'attribute' => 'createdAt', 'value' => ['2026-10-01', '2026-10-31'],
                'dateTime' => true, 'timeZone' => 'Europe/Samara'],
            ['type' => 'past', 'attribute' => 'createdAt', 'dateTime' => true, 'timeZone' => 'Europe/Samara'],
            ['type' => 'or', 'value' => [
                ['type' => 'equals', 'attribute' => 'assignedUserId', 'value' => 'u1'],
                ['type' => 'itvolgaRelated', 'attribute' => 'id', 'value' => ['link' => 'account',
                    'where' => [['type' => 'in', 'attribute' => 'industry', 'value' => ['IT']]]]],
            ]],
            ['type' => 'itvolgaFieldCompare', 'attribute' => 'dateDue', 'value' => ['operator' => 'lessThan',
                'attribute' => 'dateInvoiced', 'timeZone' => 'Europe/Samara']],
            ['type' => 'between', 'attribute' => 'dateDue', 'value' => ['2026-01-01', '2026-01-31']],
        ]], $where);

        $this->assertSame(null, WhereTranslator::translate(['type' => 'and', 'items' => []], [], self::context()));
    }
}
