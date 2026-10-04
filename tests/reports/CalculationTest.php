<?php

declare(strict_types=1);

namespace Itvolga\Tests\Reports;

use Espo\Modules\Itvolga\Tools\Finance\Decimal;
use Espo\Modules\Itvolga\Tools\Report\Core\Calculation\ParseError;
use Espo\Modules\Itvolga\Tools\Report\Core\Calculation\Parser;
use Espo\Modules\Itvolga\Tools\Report\Core\DecimalMath;
use Itvolga\Tests\Finance\TestCase;

/**
 * The calculation language of tabular reports (D-91): exact decimals, precedence, empty values, division by zero,
 * rejected input with the position of the problem.
 */
final class CalculationTest extends TestCase
{
    public function testPrecedenceParenthesesAndUnaryMinus(): void
    {
        $this->assertDecimal('7', Parser::parse('1 + 2 * 3')->evaluate([]));
        $this->assertDecimal('9', Parser::parse('(1 + 2) * 3')->evaluate([]));
        $this->assertDecimal('-1', Parser::parse('-(3 - 2)')->evaluate([]));
        $this->assertDecimal('1', Parser::parse('6 / 3 / 2')->evaluate([]));
        $this->assertDecimal('5', Parser::parse('10 - 3 - 2')->evaluate([]));
        $this->assertDecimal('4', Parser::parse('--4')->evaluate([]));
    }

    public function testReferencesAreExactDecimals(): void
    {
        $expression = Parser::parse('{grandTotal} - {paidAmount}');
        $values = ['grandTotal' => Decimal::of('19500.10'), 'paidAmount' => Decimal::of('0.20')];

        $this->assertDecimal('19499.9', $expression->evaluate($values));
        $this->assertSame(['grandTotal', 'paidAmount'], $expression->references());
        $this->assertSame(['account.cEmployees'], Parser::parse('{account.cEmployees} * 2')->references());
        $this->assertDecimal('0.3', Parser::parse('{a} + {b}')->evaluate(['a' => Decimal::of('0.1'), 'b' => Decimal::of('0.2')]));
    }

    public function testEmptyOperandAndDivisionByZeroGiveEmpty(): void
    {
        $this->assertSame(null, Parser::parse('{a} + 1')->evaluate(['a' => null]));
        $this->assertSame(null, Parser::parse('{a} + 1')->evaluate([]));
        $this->assertSame(null, Parser::parse('1 / {a}')->evaluate(['a' => Decimal::of('0.00')]));
        $this->assertSame(null, Parser::parse('round(1 / 0, 2)')->evaluate([]));
    }

    public function testDivisionKeepsEightDecimalsAndRoundHalfAwayFromZero(): void
    {
        $this->assertDecimal('0.14285714', Parser::parse('1 / 7')->evaluate([]));
        $this->assertDecimal('0.66666667', Parser::parse('2 / 3')->evaluate([]));
        $this->assertDecimal('0.67', Parser::parse('round(2 / 3, 2)')->evaluate([]));
        $this->assertDecimal('-2.5', Parser::parse('round(-2.45, 1)')->evaluate([]));
        $this->assertSame(2, Parser::parse('round({a}, 2)')->roundScale());
        $this->assertSame(null, Parser::parse('round({a}, 2) + 1')->roundScale());
    }

    public function testRejectsAnythingOutsideTheLanguage(): void
    {
        $cases = [
            '' => ['empty', 0], '   ' => ['empty', 0], '1 +' => ['unexpectedEnd', 4], '1 2' => ['unexpectedToken', 3],
            'abs(1)' => ['unexpectedCharacter', 1], '{a' => ['unexpectedCharacter', 1], '{1a}' => ['unexpectedCharacter', 1],
            '{a.b.c}' => ['unexpectedCharacter', 1], '1,5' => ['unexpectedToken', 2], 'round(1)' => ['unexpectedToken', 8],
            'round(1, 9)' => ['badRoundScale', 10], 'round(1, 1.5)' => ['badRoundScale', 10], '(1' => ['unexpectedEnd', 3],
            '1 ; DROP' => ['unexpectedCharacter', 3], "'x'" => ['unexpectedCharacter', 1], '1e3' => ['unexpectedCharacter', 2],
            '()' => ['unexpectedToken', 2], '{a}()' => ['unexpectedToken', 4],
        ];

        foreach ($cases as $text => [$key, $position]) {
            $error = $this->assertThrows(ParseError::class, fn () => Parser::parse((string) $text));
            assert($error instanceof ParseError);
            $this->assertSame([$key, $position], [$error->key, $error->position], "'$text'");
        }

        $this->assertThrows(ParseError::class, fn () => Parser::parse(str_repeat('1+', 300) . '1'), 'tooLong');
        $this->assertThrows(ParseError::class, fn () => Parser::parse(str_repeat('(', 25) . '1' . str_repeat(')', 25)), 'tooDeep');
        $this->assertThrows(ParseError::class, fn () => Parser::parse(str_repeat('-', 30) . '1'), 'tooDeep');
    }

    public function testSummariesSkipEmptyValuesAndAverageIsExact(): void
    {
        $summary = DecimalMath::summarize([Decimal::of('10'), null, Decimal::of('2.5'), Decimal::of('-1')]);

        $this->assertDecimal('11.5', $summary['SUM']);
        $this->assertDecimal('3.83333333', $summary['AVG']);
        $this->assertDecimal('-1', $summary['MIN']);
        $this->assertDecimal('10', $summary['MAX']);
        $this->assertSame(3, $summary['COUNT']);

        $empty = DecimalMath::summarize([null]);
        $this->assertSame([null, null, null, null, 0], array_values($empty));
    }
}
