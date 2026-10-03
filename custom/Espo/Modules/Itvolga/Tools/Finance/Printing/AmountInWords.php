<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Finance\Printing;

use Espo\Modules\Itvolga\Tools\Finance\Decimal;
use Espo\Modules\Itvolga\Tools\Finance\Exceptions\InvalidValue;
use Espo\Modules\Itvolga\Tools\Finance\Scale;

/**
 * Amount in Russian words as the SalesPlatform print forms write it: «Девятнадцать тысяч пятьсот рублей 00 копеек»
 * (rubles in words, kopecks as two digits, first letter upper case). Works on the decimal string, three digits at a
 * time, so any DECIMAL(25,8) amount is exact; an amount with fractions of a kopeck is refused, never rounded.
 */
final class AmountInWords
{
    private const UNITS = [
        'm' => ['', 'один', 'два', 'три', 'четыре', 'пять', 'шесть', 'семь', 'восемь', 'девять'],
        'f' => ['', 'одна', 'две', 'три', 'четыре', 'пять', 'шесть', 'семь', 'восемь', 'девять'],
    ];
    private const TEENS = ['десять', 'одиннадцать', 'двенадцать', 'тринадцать', 'четырнадцать', 'пятнадцать',
        'шестнадцать', 'семнадцать', 'восемнадцать', 'девятнадцать'];
    private const TENS = ['', '', 'двадцать', 'тридцать', 'сорок', 'пятьдесят', 'шестьдесят', 'семьдесят',
        'восемьдесят', 'девяносто'];
    private const HUNDREDS = ['', 'сто', 'двести', 'триста', 'четыреста', 'пятьсот', 'шестьсот', 'семьсот',
        'восемьсот', 'девятьсот'];
    /** Word forms (1, 2–4, 5+) and gender of each group of three digits, from the lowest. */
    private const GROUPS = [
        [['рубль', 'рубля', 'рублей'], 'm'],
        [['тысяча', 'тысячи', 'тысяч'], 'f'],
        [['миллион', 'миллиона', 'миллионов'], 'm'],
        [['миллиард', 'миллиарда', 'миллиардов'], 'm'],
        [['триллион', 'триллиона', 'триллионов'], 'm'],
        [['квадриллион', 'квадриллиона', 'квадриллионов'], 'm'],
    ];
    private const KOPECKS = ['копейка', 'копейки', 'копеек'];

    public static function rubles(mixed $amount): string
    {
        $value = Decimal::of($amount);

        if ($value->significantScale() > Scale::MONEY) {
            throw new InvalidValue('An amount in words needs whole kopecks.', 'tooManyDecimals');
        }

        $negative = $value->isNegative();
        [$rubles, $kopecks] = explode('.', ($negative ? $value->negate() : $value)->toFixed(Scale::MONEY));
        $groups = str_split(str_pad($rubles, (int) ceil(strlen($rubles) / 3) * 3, '0', STR_PAD_LEFT), 3);

        if (count($groups) > count(self::GROUPS)) {
            throw new InvalidValue('The amount is too large to be written in words.', 'tooLarge');
        }

        $words = [];

        foreach ($groups as $i => $digits) {
            [$forms, $gender] = self::GROUPS[count($groups) - 1 - $i];
            $number = (int) $digits;
            $isRubles = $i === count($groups) - 1;

            if ($number === 0 && !$isRubles) {
                continue;
            }

            if ($number === 0 && ltrim($rubles, '0') === '') {
                $words[] = 'ноль';
            }

            array_push($words, ...self::hundreds($number, $gender));
            $words[] = self::form($number, $forms);
        }

        $words[] = $kopecks;
        $words[] = self::form((int) $kopecks, self::KOPECKS);
        $text = implode(' ', $words);

        if ($negative) {
            $text = 'минус ' . $text;
        }

        return mb_strtoupper(mb_substr($text, 0, 1)) . mb_substr($text, 1);
    }

    /**
     * @return list<string> words of 0…999 (none for 0)
     */
    private static function hundreds(int $number, string $gender): array
    {
        $words = [];
        $hundreds = intdiv($number, 100);
        $rest = $number % 100;

        if ($hundreds > 0) {
            $words[] = self::HUNDREDS[$hundreds];
        }

        if ($rest >= 10 && $rest < 20) {
            $words[] = self::TEENS[$rest - 10];

            return $words;
        }

        if ($rest >= 20) {
            $words[] = self::TENS[intdiv($rest, 10)];
        }

        if ($rest % 10 > 0) {
            $words[] = self::UNITS[$gender][$rest % 10];
        }

        return $words;
    }

    /**
     * @param array{string, string, string} $forms
     */
    private static function form(int $number, array $forms): string
    {
        $lastTwo = $number % 100;
        $last = $number % 10;

        if ($lastTwo >= 11 && $lastTwo <= 14) {
            return $forms[2];
        }

        return match (true) {
            $last === 1 => $forms[0],
            $last >= 2 && $last <= 4 => $forms[1],
            default => $forms[2],
        };
    }
}
