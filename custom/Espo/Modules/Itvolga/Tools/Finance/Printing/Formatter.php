<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Finance\Printing;

use DateTimeImmutable;
use DateTimeZone;
use Espo\Modules\Itvolga\Tools\Finance\Decimal;
use Espo\Modules\Itvolga\Tools\Finance\Exceptions\InvalidValue;
use Exception;
use IntlDateFormatter;
use RuntimeException;

/**
 * Russian print notation of stored values (stage 05): numbers with a comma and non-breaking-space thousand groups,
 * dates «3 октября 2026 г.» / «03.10.2026». Exact: a number keeps every significant decimal and is never rounded,
 * so a printed value always equals the stored one (D-05).
 */
final class Formatter
{
    public const NBSP = "\u{00A0}";
    public const BLANK_DATE = '«___» __________ 20__ г.';

    /** «3 октября 2026 г.»: ICU writes the month of a date in the genitive in Russian. */
    private const LONG_DATE = "d MMMM y 'г.'";
    /**
     * @param mixed $value decimal string, int or Decimal (float is rejected by Decimal)
     * @param int $minScale decimals shown at least (zeros appended), more when significant
     */
    public static function number(mixed $value, int $minScale = 0): string
    {
        $decimal = Decimal::of($value);
        $scale = max($minScale, $decimal->significantScale());
        $text = $decimal->toFixed($scale);
        $sign = '';

        if (str_starts_with($text, '-')) {
            $sign = '-';
            $text = substr($text, 1);
        }

        [$integer, $fraction] = array_pad(explode('.', $text, 2), 2, '');
        $grouped = ltrim(strrev(chunk_split(strrev($integer), 3, strrev(self::NBSP))), self::NBSP);

        return $sign . $grouped . ($fraction !== '' ? ',' . $fraction : '');
    }

    /**
     * Money and prices: at least two decimals («19 500,00», «33,335»).
     */
    public static function money(mixed $value): string
    {
        return self::number($value, 2);
    }

    /**
     * Quantity without trailing zeros («2,5», «1»).
     */
    public static function quantity(mixed $value): string
    {
        return self::number($value);
    }

    /**
     * «3 октября 2026 г.»; an empty date gives a blank to fill by hand.
     */
    public static function date(?string $date): string
    {
        if ($date === null || $date === '') {
            return self::BLANK_DATE;
        }

        [$year, $month, $day] = self::parts($date);

        if (!class_exists(IntlDateFormatter::class)) {
            throw new RuntimeException('The print forms need the PHP intl extension.');
        }

        $formatter = new IntlDateFormatter('ru_RU', IntlDateFormatter::NONE, IntlDateFormatter::NONE, 'UTC',
            IntlDateFormatter::GREGORIAN, self::LONG_DATE);

        return (string) $formatter->format(new DateTimeImmutable(sprintf('%04d-%02d-%02d', $year, $month, $day),
            new DateTimeZone('UTC')));
    }

    /**
     * «03.10.2026»; an empty date gives an empty string.
     */
    public static function numericDate(?string $date): string
    {
        if ($date === null || $date === '') {
            return '';
        }

        [$year, $month, $day] = self::parts($date);

        return sprintf('%02d.%02d.%04d', $day, $month, $year);
    }

    /**
     * The calendar date (Y-m-d) of a stored UTC date-time in the given time zone.
     */
    public static function localDate(string $utcDateTime, string $timeZone): string
    {
        try {
            $moment = new DateTimeImmutable($utcDateTime, new DateTimeZone('UTC'));

            return $moment->setTimezone(new DateTimeZone($timeZone))->format('Y-m-d');
        } catch (Exception) {
            throw new InvalidValue('Not a date-time or an unknown time zone.', 'invalidDate');
        }
    }

    /**
     * @return array{int, int, int} year, month, day
     */
    private static function parts(string $date): array
    {
        if (!preg_match('/^(\d{4})-(\d{2})-(\d{2})$/', $date, $m) || !checkdate((int) $m[2], (int) $m[3], (int) $m[1])) {
            throw new InvalidValue('Not a date (Y-m-d).', 'invalidDate');
        }

        return [(int) $m[1], (int) $m[2], (int) $m[3]];
    }
}
