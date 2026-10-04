<?php

declare(strict_types=1);

namespace Itvolga\Tests\Reports;

use Espo\Modules\Itvolga\Tools\Report\Core\Access\SharingPolicy;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\FieldInfo;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\FieldRef;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\GroupLevel;
use Espo\Modules\Itvolga\Tools\Report\Core\Format\NumberText;
use Espo\Modules\Itvolga\Tools\Report\Core\Format\PeriodLabel;
use Espo\Modules\Itvolga\Tools\Report\Core\Format\RawNumber;
use Espo\Modules\Itvolga\Tools\Report\Core\Granularity;
use Espo\Modules\Itvolga\Tools\Report\Core\Result\KeyOrder;
use Itvolga\Tests\Finance\TestCase;

/**
 * Who reads a report (D-87), the order of group keys (D-91), the notation of numbers and periods (D-93, D-102).
 */
final class CoreTest extends TestCase
{
    public function testSharingPolicyTable(): void
    {
        // [level, access, owner, listedUser, listedTeam] => read
        $cases = [
            ['no', 'public', true, false, false, false],
            ['own', 'private', true, false, false, true],
            ['own', 'private', false, true, true, false],
            ['all', 'private', false, true, true, false],
            ['own', 'public', false, false, false, true],
            ['own', 'shared', false, true, false, true],
            ['own', 'shared', false, false, true, false],
            ['team', 'shared', false, false, true, true],
            ['team', 'shared', false, false, false, false],
            ['all', 'shared', false, false, false, true],
            ['yes', 'public', true, false, false, false],
        ];

        foreach ($cases as [$level, $access, $owner, $user, $team, $expected]) {
            $this->assertSame($expected, SharingPolicy::canRead($level, $access, $owner, $user, $team),
                "$level/$access/" . json_encode([$owner, $user, $team]));
        }

        $this->assertTrue(SharingPolicy::canEdit('own', true));
        $this->assertTrue(!SharingPolicy::canEdit('all', false), 'only the owner edits');
        $this->assertTrue(!SharingPolicy::canEdit('no', true));
    }

    private static function group(string $type, ?Granularity $granularity = null, string $direction = 'asc',
        array $options = []): GroupLevel
    {
        return new GroupLevel(new FieldInfo(FieldRef::of(null, 'f'), $type, 'Invoice', FieldInfo::LINK_NONE, null,
            ['f'], $options), $granularity, $direction);
    }

    /**
     * @param list<array{v: mixed, f: string}> $keys
     * @return list<mixed>
     */
    private static function sorted(GroupLevel $group, array $keys): array
    {
        $order = new KeyOrder();
        usort($keys, fn ($a, $b) => $order->compare($group, $a, $b));

        return array_map(fn ($k) => $k['v'], $keys);
    }

    public function testGroupKeysOrder(): void
    {
        $k = fn ($v, $f = null) => ['v' => $v, 'f' => $f ?? (string) $v];

        $this->assertSame(['2026/2', '2026/10', '2027/1', null],
            self::sorted(self::group('date', Granularity::WEEK), [$k('2026/10'), $k(null), $k('2027/1'), $k('2026/2')]));
        $this->assertSame(['2027/1', '2026/10', '2026/2', null],
            self::sorted(self::group('date', Granularity::WEEK, 'desc'), [$k('2026/10'), $k(null), $k('2027/1'),
                $k('2026/2')]));
        $this->assertSame(['Sent', 'Paid', 'Other'],
            self::sorted(self::group('enum', null, 'asc', ['Draft', 'Sent', 'Paid']), [$k('Other'), $k('Paid'),
                $k('Sent')]));
        $this->assertSame(['10', '2', '-1'],
            self::sorted(self::group('int', null, 'desc'), [$k('2'), $k('-1'), $k('10')]));
        $this->assertSame(['b', 'a'], self::sorted(self::group('link'), [$k('a', 'Яблоко'), $k('b', 'Арбуз')]));
        $this->assertSame([2026, 2027], self::sorted(self::group('date', Granularity::YEAR), [$k(2027), $k(2026)]));
    }

    public function testNumbersInTheUsersNotationWithoutFloats(): void
    {
        $ru = new NumberText(',', ' ');

        $this->assertSame('1 234 567,50', $ru->format('1234567.5', 2));
        $this->assertSame('0,01', $ru->format('0.005', 2));
        $this->assertSame('-0,01', $ru->format('-0.005', 2));
        $this->assertSame('0,00', $ru->format('-0.004', 2));
        $this->assertSame('31 111,105', $ru->format('31111.10500000'));
        $this->assertSame('', $ru->format(null));
        $this->assertSame('1,234.5', (new NumberText('.', ','))->format('1234.5'));
        $this->assertSame('1234', (new NumberText(',', ''))->format(1234));
        $this->assertSame('0.1', RawNumber::read(0.1)?->toString());
        $this->assertSame('0.5', RawNumber::read('.5')?->toString());
        $this->assertSame(null, RawNumber::read(null));
    }

    public function testPeriodLabels(): void
    {
        $labels = new PeriodLabel(['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь',
            'Октябрь', 'Ноябрь', 'Декабрь'], ['week' => '{year}, неделя {n}', 'quarter' => '{n} кв. {year}',
            'halfYear' => '{n}-е полугодие {year}'], fn (string $d) => implode('.', array_reverse(explode('-', $d))));

        $this->assertSame('Октябрь 2026', $labels->label(Granularity::MONTH, '2026-10'));
        $this->assertSame('2026, неделя 7', $labels->label(Granularity::WEEK, '2026/7'));
        $this->assertSame('4 кв. 2026', $labels->label(Granularity::QUARTER, '2026_4'));
        $this->assertSame('1-е полугодие 2026', $labels->label(Granularity::HALF_YEAR, '2026_1'));
        $this->assertSame('04.10.2026', $labels->label(Granularity::DAY, '2026-10-04'));
        $this->assertSame('2026', $labels->label(Granularity::YEAR, '2026'));
    }
}
