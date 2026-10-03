<?php

declare(strict_types=1);

namespace Itvolga\Tests\Finance;

use Espo\Modules\Itvolga\Tools\Finance\Exceptions\InvalidValue;
use Espo\Modules\Itvolga\Tools\Finance\Printing\AmountInWords;

/**
 * Amount in words of the print forms (stage 05): the wording of SalesPlatform `num2str` (rubles in words, kopecks as
 * two digits), exact on decimal strings.
 */
final class AmountInWordsTest extends TestCase
{
    public function testWritesTheSalesPlatformWording(): void
    {
        $cases = [
            '19500.00' => 'Девятнадцать тысяч пятьсот рублей 00 копеек',
            '0' => 'Ноль рублей 00 копеек',
            '0.01' => 'Ноль рублей 01 копейка',
            '1' => 'Один рубль 00 копеек',
            '2.02' => 'Два рубля 02 копейки',
            '5.05' => 'Пять рублей 05 копеек',
            '11.11' => 'Одиннадцать рублей 11 копеек',
            '14.14' => 'Четырнадцать рублей 14 копеек',
            '21.21' => 'Двадцать один рубль 21 копейка',
            '22.22' => 'Двадцать два рубля 22 копейки',
            '112' => 'Сто двенадцать рублей 00 копеек',
            '1000' => 'Одна тысяча рублей 00 копеек',
            '2000' => 'Две тысячи рублей 00 копеек',
            '1001' => 'Одна тысяча один рубль 00 копеек',
            '11000' => 'Одиннадцать тысяч рублей 00 копеек',
            '21000' => 'Двадцать одна тысяча рублей 00 копеек',
            '1000000' => 'Один миллион рублей 00 копеек',
            '2001002.21' => 'Два миллиона одна тысяча два рубля 21 копейка',
            '999999.99' => 'Девятьсот девяносто девять тысяч девятьсот девяносто девять рублей 99 копеек',
            '4650.5' => 'Четыре тысячи шестьсот пятьдесят рублей 50 копеек',
            '1500.00000000' => 'Одна тысяча пятьсот рублей 00 копеек',
            '-100' => 'Минус сто рублей 00 копеек',
        ];

        // Long digit runs are built, not written (scripts/check-secrets.sh flags 10+ digits).
        $cases['1' . str_repeat('0', 9)] = 'Один миллиард рублей 00 копеек';

        foreach ($cases as $amount => $words) {
            $this->assertSame($words, AmountInWords::rubles((string) $amount), "$amount:");
        }
    }

    public function testIsExactBeyondFloatPrecision(): void
    {
        // 17 integer digits (DECIMAL(25,8)) with kopecks: a float would lose the last digits.
        $amount = '1' . str_repeat('0', 15) . '1.01';

        $this->assertSame('Десять квадриллионов один рубль 01 копейка', AmountInWords::rubles($amount));
    }

    public function testRefusesFractionsOfAKopeckAndFloats(): void
    {
        $this->assertThrows(InvalidValue::class, fn () => AmountInWords::rubles('1.005'), 'whole kopecks');
        $this->assertThrows(InvalidValue::class, fn () => AmountInWords::rubles(1.5), 'Float');
        $this->assertThrows(InvalidValue::class, fn () => AmountInWords::rubles('1' . str_repeat('0', 18)), 'too large');
    }
}
