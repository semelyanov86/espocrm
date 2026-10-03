<?php

declare(strict_types=1);

namespace Itvolga\Tests\Finance;

use Espo\Modules\Itvolga\Tools\Finance\Exceptions\InvalidValue;
use Espo\Modules\Itvolga\Tools\Finance\Printing\Formatter;

/**
 * Print notation of numbers and dates (stage 05): exact, comma decimals, non-breaking-space thousand groups.
 */
final class PrintFormatterTest extends TestCase
{
    private const S = Formatter::NBSP;

    public function testMoneyKeepsEverySignificantDecimalAndNeverRounds(): void
    {
        $this->assertSame('19' . self::S . '500,00', Formatter::money('19500.00000000'));
        $this->assertSame('0,00', Formatter::money('0'));
        $this->assertSame('33,335', Formatter::money('33.33500000'));
        $this->assertSame('1' . self::S . '500,12345678', Formatter::money('1500.12345678'));
        $this->assertSame('-100,00', Formatter::money('-100'));
        $this->assertSame('1' . self::S . '234' . self::S . '567,10', Formatter::money('1234567.1'));
        $this->assertSame('999,00', Formatter::money('999'));
    }

    public function testQuantityHasNoTrailingZeros(): void
    {
        $this->assertSame('2,5', Formatter::quantity('2.500'));
        $this->assertSame('1', Formatter::quantity('1.000'));
        $this->assertSame('0,25', Formatter::quantity('0.250'));
        $this->assertSame('1' . self::S . '000', Formatter::quantity('1000.000'));
    }

    public function testRejectsFloats(): void
    {
        $this->assertThrows(InvalidValue::class, fn () => Formatter::money(1.5), 'Float');
    }

    public function testDatesInRussianWithLowerCaseMonth(): void
    {
        $this->assertSame('3 октября 2026 г.', Formatter::date('2026-10-03'));
        $this->assertSame('31 декабря 2016 г.', Formatter::date('2016-12-31'));
        $this->assertSame('1 января 2017 г.', Formatter::date('2017-01-01'));
        // Every month: day without a leading zero, the month in lower case (ICU genitive), the year and «г.».
        for ($month = 1; $month <= 12; $month++) {
            $text = Formatter::date(sprintf('2026-%02d-09', $month));
            $this->assertTrue((bool) preg_match('/^9 \p{Ll}+[ая] 2026 г\.$/u', $text), "month $month: $text");
        }
        $this->assertSame(Formatter::BLANK_DATE, Formatter::date(null));
        $this->assertSame(Formatter::BLANK_DATE, Formatter::date(''));
        $this->assertSame('03.10.2026', Formatter::numericDate('2026-10-03'));
        $this->assertSame('', Formatter::numericDate(null));
        $this->assertThrows(InvalidValue::class, fn () => Formatter::date('2026-02-30'));
        $this->assertThrows(InvalidValue::class, fn () => Formatter::date('03.10.2026'));
    }

    public function testLocalDateOfAStoredUtcMoment(): void
    {
        // createdAt is stored in UTC; a quote created at 01:30 Moscow time belongs to the next calendar day.
        $this->assertSame('2026-10-03', Formatter::localDate('2026-10-02 22:30:00', 'Europe/Moscow'));
        $this->assertSame('2026-10-02', Formatter::localDate('2026-10-02 20:59:59', 'Europe/Moscow'));
        $this->assertSame('2026-10-02', Formatter::localDate('2026-10-02 22:30:00', 'UTC'));
        $this->assertThrows(InvalidValue::class, fn () => Formatter::localDate('2026-10-02 22:30:00', 'Nowhere/City'));
    }
}
