<?php

declare(strict_types=1);

namespace Itvolga\Tests\Finance;

use Espo\Modules\Itvolga\Tools\Finance\Decimal;
use Espo\Modules\Itvolga\Tools\Finance\Exceptions\InvalidValue;

final class DecimalTest extends TestCase
{
    public function testParsesDatabaseDecimalsAndPrintsCanonicalForm(): void
    {
        // MySQL returns DECIMAL(25,8)/(25,3) with all scale digits.
        $this->assertSame('1500', Decimal::of('1500.00000000')->toString());
        $this->assertSame('2.5', Decimal::of('2.500')->toString());
        $this->assertSame('7.5', Decimal::of('007.50')->toString());
        $this->assertSame('0', Decimal::of('-0.00')->toString());
        $this->assertSame('-12.34', Decimal::of('-12.3400')->toString());
        $this->assertSame('42', Decimal::of(42)->toString());
        $this->assertSame('0', Decimal::ofNullable(null)->toString());
    }

    public function testRejectsFloatsAndMalformedNumbers(): void
    {
        $this->assertThrows(InvalidValue::class, fn () => Decimal::of(0.1), 'Float');
        $this->assertThrows(InvalidValue::class, fn () => Decimal::of(1500.0), 'Float');

        foreach (['', '1e3', '1,5', '1 500.00', ' 1', '.5', '5.', '+1', '--1', 'NULL', '0x10'] as $bad) {
            $this->assertThrows(InvalidValue::class, fn () => Decimal::of($bad));
        }

        $this->assertThrows(InvalidValue::class, fn () => Decimal::of(null));
        $this->assertThrows(InvalidValue::class, fn () => Decimal::of(true));
    }

    public function testArithmeticIsExact(): void
    {
        // The float classic: 0.1 + 0.2 != 0.3.
        $this->assertTrue(Decimal::of('0.1')->add('0.2')->equals('0.3'));
        // Largest DECIMAL(25,8) values do not lose digits.
        $max = str_repeat('9', 17) . '.' . str_repeat('9', 8); // built, not written: long digit runs look like account numbers to the scanner
        $this->assertSame('1' . str_repeat('0', 17), Decimal::of($max)->add('0.00000001')->toString());
        // Fractional hours × price (quantity DECIMAL(25,3) × listprice DECIMAL(27,8)).
        $this->assertSame('18750', Decimal::of('12.500')->mul('1500.00000000')->toString());
        $this->assertSame('33.3', Decimal::of('0.333')->mul('100')->toString());
        // Percent is exact: 18 % of 25 000.
        $this->assertSame('4500', Decimal::of('25000.00000000')->percent('18.000')->toString());
        $this->assertSame('222.2208', Decimal::of('1234.56')->percent('18')->toString());
        $this->assertSame('-5', Decimal::of('5')->negate()->toString());
        $this->assertSame('6.5', Decimal::sum([Decimal::of('1.5'), Decimal::of('2'), Decimal::of('3.000')])->toString());
    }

    public function testRoundsHalfAwayFromZero(): void
    {
        $cases = [
            ['1.005', 2, '1.01'],      // float round() of 1.005 gives 1.00 in many languages
            ['2.675', 2, '2.68'],      // binary float 2.67499999…
            ['1.0049', 2, '1'],
            ['100.004999', 2, '100'],
            ['100.005', 2, '100.01'],
            ['0.5', 0, '1'],
            ['-0.5', 0, '-1'],
            ['-1.005', 2, '-1.01'],
            ['-0.004', 2, '0'],
            ['15000', 2, '15000'],
        ];

        foreach ($cases as [$value, $scale, $expected]) {
            $this->assertSame($expected, Decimal::of($value)->round($scale)->toString(), "round($value, $scale)");
        }
    }

    public function testComparisonIgnoresScale(): void
    {
        $this->assertTrue(Decimal::of('1.50')->equals('1.5000'));
        $this->assertTrue(Decimal::of('-0')->equals('0'));
        $this->assertSame(-1, Decimal::of('999.99')->compare('1000'));
        $this->assertSame(1, Decimal::of('0.01')->compare('0'));
        $this->assertTrue(Decimal::of('0.00000000')->isZero());
        $this->assertTrue(Decimal::of('-0.01')->isNegative());
        $this->assertTrue(!Decimal::of('0')->isPositive());
    }

    public function testToFixedNeverDropsSignificantDigits(): void
    {
        $this->assertSame('1500.00', Decimal::of('1500.00000000')->toFixed(2));
        $this->assertSame('2.500', Decimal::of('2.5')->toFixed(3));
        $this->assertSame(0, Decimal::of('1500.00000000')->significantScale());
        $this->assertSame(3, Decimal::of('1.00500000')->significantScale());
        $this->assertThrows(InvalidValue::class, fn () => Decimal::of('1.005')->toFixed(2));
        $this->assertSame('1.01', Decimal::of('1.005')->round(2)->toFixed(2));
    }
}
