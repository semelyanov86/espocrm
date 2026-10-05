<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Mailing;

use DateInterval;
use DateTimeImmutable;
use DateTimeZone;

/**
 * Moments of a mailing (D-121): the wall clock of the owner's time zone, the result in UTC.
 *
 *  - first(): the first slot strictly after now — today, if its time is still ahead; weekly and every two weeks — the
 *    nearest chosen weekday; monthly — the chosen day, the last day of a shorter month (the 31st is the 30th of April,
 *    the 28th or 29th of February — never a carry-over to the next month); yearly — the chosen date, the 29th of
 *    February is the 28th in other years;
 *  - after(): the slot after a run of `scheduled` — every two weeks keeps its anchor (14 days from the scheduled slot,
 *    as many times as needed to be after now); the others take the first slot after now. Missed slots are not caught
 *    up: one attempt, then the next future slot.
 */
final class Schedule
{
    public static function first(MailingSettings $settings, DateTimeZone $zone, DateTimeImmutable $now): DateTimeImmutable
    {
        $local = $now->setTimezone($zone);

        $slot = match ($settings->frequency) {
            MailingSettings::DAILY => self::daily($settings, $zone, $local, $now),
            MailingSettings::WEEKLY, MailingSettings::BIWEEKLY => self::weekly($settings, $zone, $local, $now),
            MailingSettings::MONTHLY => self::monthly($settings, $zone, $local, $now),
            default => self::yearly($settings, $zone, $local, $now),
        };

        return $slot->setTimezone(new DateTimeZone('UTC'));
    }

    public static function after(MailingSettings $settings, DateTimeZone $zone, DateTimeImmutable $scheduled,
        DateTimeImmutable $now): DateTimeImmutable
    {
        if ($settings->frequency !== MailingSettings::BIWEEKLY) {
            return self::first($settings, $zone, $now);
        }

        $date = $scheduled->setTimezone($zone);
        // The zone of the owner may have changed since the slot: its local date may be a day off the chosen weekday
        // (internal review) — the nearest chosen weekday keeps the rhythm.
        $shift = (((int) $settings->weekday - (int) $date->format('N') + 10) % 7) - 3;
        $date = $date->modify(sprintf('%+d days', $shift));

        do {
            $date = $date->add(new DateInterval('P14D'));
            $slot = self::at($zone, (int) $date->format('Y'), (int) $date->format('n'), (int) $date->format('j'),
                $settings);
        } while ($slot <= $now);

        return $slot->setTimezone(new DateTimeZone('UTC'));
    }

    private static function at(DateTimeZone $zone, int $year, int $month, int $day, MailingSettings $settings):
        DateTimeImmutable
    {
        // A wall-clock time that a clock change skips moves forward (PHP), so a slot always exists.
        return (new DateTimeImmutable('now', $zone))
            ->setDate($year, $month, $day)
            ->setTime($settings->hour(), $settings->minute());
    }

    private static function daysIn(int $year, int $month): int
    {
        return (int) (new DateTimeImmutable(sprintf('%04d-%02d-01', $year, $month)))->format('t');
    }

    private static function daily(MailingSettings $s, DateTimeZone $zone, DateTimeImmutable $local,
        DateTimeImmutable $now): DateTimeImmutable
    {
        $day = $local;

        while (true) {
            $slot = self::at($zone, (int) $day->format('Y'), (int) $day->format('n'), (int) $day->format('j'), $s);

            if ($slot > $now) {
                return $slot;
            }

            $day = $day->add(new DateInterval('P1D'));
        }
    }

    private static function weekly(MailingSettings $s, DateTimeZone $zone, DateTimeImmutable $local,
        DateTimeImmutable $now): DateTimeImmutable
    {
        $day = $local;

        for ($i = 0; $i <= 7; $i++) {
            if ((int) $day->format('N') === $s->weekday) {
                $slot = self::at($zone, (int) $day->format('Y'), (int) $day->format('n'), (int) $day->format('j'), $s);

                if ($slot > $now) {
                    return $slot;
                }
            }

            $day = $day->add(new DateInterval('P1D'));
        }

        return self::at($zone, (int) $day->format('Y'), (int) $day->format('n'), (int) $day->format('j'), $s);
    }

    private static function monthly(MailingSettings $s, DateTimeZone $zone, DateTimeImmutable $local,
        DateTimeImmutable $now): DateTimeImmutable
    {
        $year = (int) $local->format('Y');
        $month = (int) $local->format('n');

        for ($i = 0; $i < 3; $i++) {
            $slot = self::at($zone, $year, $month, min((int) $s->day, self::daysIn($year, $month)), $s);

            if ($slot > $now) {
                return $slot;
            }

            [$year, $month] = $month === 12 ? [$year + 1, 1] : [$year, $month + 1];
        }

        return $slot;
    }

    private static function yearly(MailingSettings $s, DateTimeZone $zone, DateTimeImmutable $local,
        DateTimeImmutable $now): DateTimeImmutable
    {
        $year = (int) $local->format('Y');

        for ($i = 0; $i < 3; $i++) {
            $slot = self::at($zone, $year, (int) $s->month, min((int) $s->day, self::daysIn($year, (int) $s->month)),
                $s);

            if ($slot > $now) {
                return $slot;
            }

            $year++;
        }

        return $slot;
    }
}
