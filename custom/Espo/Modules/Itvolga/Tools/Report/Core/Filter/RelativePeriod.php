<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Filter;

use DateTimeImmutable;
use LogicException;

/**
 * Calendar periods of the relative date conditions (D-92), in the time zone of the run: inclusive day ranges
 * ['from', 'to'] ('YYYY-MM-DD'), or a single bound. Weeks are ISO (Monday first); fiscal year and quarters start
 * fiscalYearShift months after January, like the core settings.
 */
final class RelativePeriod
{
    /**
     * @return array{string, ?string, ?string} [kind: range|before|after, first date, second date]
     */
    public static function resolve(string $type, ?int $days, RunContext $context): array
    {
        $today = $context->today();
        $n = $days ?? 0;

        return match ($type) {
            'today' => self::range($today, $today),
            'yesterday' => self::range($today->modify('-1 day'), $today->modify('-1 day')),
            'tomorrow' => self::range($today->modify('+1 day'), $today->modify('+1 day')),
            'past' => ['before', self::date($today), null],
            'future' => ['after', self::date($today), null],
            'lastSevenDays' => self::range($today->modify('-7 day'), $today),
            'currentWeek' => self::week($today, 0),
            'lastWeek' => self::week($today, -1),
            'nextWeek' => self::week($today, 1),
            'currentMonth' => self::month($today, 0),
            'lastMonth' => self::month($today, -1),
            'nextMonth' => self::month($today, 1),
            'currentQuarter' => self::quarter($today, 0, 0),
            'lastQuarter' => self::quarter($today, -1, 0),
            'nextQuarter' => self::quarter($today, 1, 0),
            'currentYear' => self::year($today, 0, 0),
            'lastYear' => self::year($today, -1, 0),
            'nextYear' => self::year($today, 1, 0),
            'currentFiscalYear' => self::year($today, 0, $context->fiscalYearShift),
            'lastFiscalYear' => self::year($today, -1, $context->fiscalYearShift),
            'currentFiscalQuarter' => self::quarter($today, 0, $context->fiscalYearShift),
            'lastFiscalQuarter' => self::quarter($today, -1, $context->fiscalYearShift),
            'lastXDays' => self::range($today->modify("-$n day"), $today),
            'nextXDays' => self::range($today, $today->modify("+$n day")),
            'olderThanXDays' => ['before', self::date($today->modify("-$n day")), null],
            'afterXDays' => ['after', self::date($today->modify("+$n day")), null],
            'xDaysAgo' => self::range($today->modify("-$n day"), $today->modify("-$n day")),
            'inXDays' => self::range($today->modify("+$n day"), $today->modify("+$n day")),
            default => throw new LogicException("Unknown period type '$type'."),
        };
    }

    /**
     * @return array{string, string, string}
     */
    private static function range(DateTimeImmutable $from, DateTimeImmutable $to): array
    {
        return ['range', self::date($from), self::date($to)];
    }

    private static function date(DateTimeImmutable $date): string
    {
        return $date->format('Y-m-d');
    }

    /**
     * @return array{string, string, string}
     */
    private static function week(DateTimeImmutable $today, int $shift): array
    {
        $monday = $today->modify('-' . ((int) $today->format('N') - 1) . ' day')->modify(($shift * 7) . ' day');

        return self::range($monday, $monday->modify('+6 day'));
    }

    /**
     * @return array{string, string, string}
     */
    private static function month(DateTimeImmutable $today, int $shift): array
    {
        $first = $today->modify('first day of this month')->modify("$shift month");

        return self::range($first, $first->modify('last day of this month'));
    }

    /**
     * @return array{string, string, string}
     */
    private static function quarter(DateTimeImmutable $today, int $shift, int $fiscalShift): array
    {
        $month = (int) $today->format('n');
        $offset = ((($month - 1 - $fiscalShift) % 3) + 3) % 3;
        $first = $today->modify('first day of this month')->modify("-$offset month")->modify(($shift * 3) . ' month');

        return self::range($first, $first->modify('+2 month')->modify('last day of this month'));
    }

    /**
     * @return array{string, string, string}
     */
    private static function year(DateTimeImmutable $today, int $shift, int $fiscalShift): array
    {
        $month = (int) $today->format('n');
        $year = (int) $today->format('Y') - ($month <= $fiscalShift ? 1 : 0) + $shift;
        $first = $today->setDate($year, $fiscalShift + 1, 1);

        return self::range($first, $first->modify('+11 month')->modify('last day of this month'));
    }
}
