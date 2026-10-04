<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Calculation;

use Espo\Modules\Itvolga\Tools\Finance\Decimal;

/**
 * Parser of the report calculation language (stage 05.1, D-91): decimal numbers ("1.5"), column references
 * ("{grandTotal}", "{account.cEmployees}"), + - * /, unary minus, parentheses and round(x, n) with 0 ≤ n ≤ 8.
 * Nothing else — no functions, variables or strings — so an expression can never reach SQL or PHP code.
 *
 *   expression := term (('+' | '-') term)*
 *   term       := unary (('*' | '/') unary)*
 *   unary      := '-' unary | primary
 *   primary    := NUMBER | REFERENCE | '(' expression ')' | 'round' '(' expression ',' INTEGER ')'
 */
final class Parser
{
    public const MAX_LENGTH = 500;
    public const MAX_DEPTH = 20;
    private const REFERENCE = '/\G\{([a-zA-Z][a-zA-Z0-9]*(?:\.[a-zA-Z][a-zA-Z0-9]*)?)\}/';
    private const NUMBER = '/\G\d+(?:\.\d+)?/';
    private const SPACE = '/\G\s+/';

    /** @var list<array{string, string, int}> type, text, 1-based position */
    private array $tokens = [];
    private int $index = 0;
    private int $depth = 0;

    public static function parse(string $text): Expression
    {
        $parser = new self();
        $parser->tokenize($text);
        $node = $parser->expression();

        if ($parser->peek()[0] !== 'end') {
            throw new ParseError('unexpectedToken', $parser->peek()[2]);
        }

        return new Expression($text, $node);
    }

    private function tokenize(string $text): void
    {
        if (trim($text) === '') {
            throw new ParseError('empty');
        }

        if (mb_strlen($text) > self::MAX_LENGTH) {
            throw new ParseError('tooLong');
        }

        $offset = 0;
        $length = strlen($text);

        while ($offset < $length) {
            $position = mb_strlen(substr($text, 0, $offset)) + 1;

            if (preg_match(self::SPACE, $text, $m, 0, $offset)) {
                $offset += strlen($m[0]);

                continue;
            }

            if (preg_match(self::NUMBER, $text, $m, 0, $offset)) {
                $this->tokens[] = ['number', $m[0], $position];
                $offset += strlen($m[0]);

                continue;
            }

            if (preg_match(self::REFERENCE, $text, $m, 0, $offset)) {
                $this->tokens[] = ['reference', $m[1], $position];
                $offset += strlen($m[0]);

                continue;
            }

            if (substr($text, $offset, 5) === 'round') {
                $this->tokens[] = ['round', 'round', $position];
                $offset += 5;

                continue;
            }

            $char = $text[$offset];

            if (str_contains('+-*/(),', $char)) {
                $this->tokens[] = [$char, $char, $position];
                $offset++;

                continue;
            }

            throw new ParseError('unexpectedCharacter', $position);
        }

        $this->tokens[] = ['end', '', mb_strlen($text) + 1];
    }

    /**
     * @return array{string, string, int}
     */
    private function peek(): array
    {
        return $this->tokens[$this->index];
    }

    /**
     * @return array{string, string, int}
     */
    private function take(string $type): array
    {
        $token = $this->peek();

        if ($token[0] !== $type) {
            throw new ParseError($token[0] === 'end' ? 'unexpectedEnd' : 'unexpectedToken', $token[2]);
        }

        $this->index++;

        return $token;
    }

    /**
     * @return array<int, mixed>
     */
    private function expression(): array
    {
        if (++$this->depth > self::MAX_DEPTH) {
            throw new ParseError('tooDeep', $this->peek()[2]);
        }

        $node = $this->term();

        while (in_array($this->peek()[0], ['+', '-'], true)) {
            $operator = $this->take($this->peek()[0])[0];
            $node = ['op', $operator, $node, $this->term()];
        }

        $this->depth--;

        return $node;
    }

    /**
     * @return array<int, mixed>
     */
    private function term(): array
    {
        $node = $this->unary();

        while (in_array($this->peek()[0], ['*', '/'], true)) {
            $operator = $this->take($this->peek()[0])[0];
            $node = ['op', $operator, $node, $this->unary()];
        }

        return $node;
    }

    /**
     * @return array<int, mixed>
     */
    private function unary(): array
    {
        if ($this->peek()[0] === '-') {
            $this->take('-');

            if (++$this->depth > self::MAX_DEPTH) {
                throw new ParseError('tooDeep', $this->peek()[2]);
            }

            $node = ['neg', $this->unary()];
            $this->depth--;

            return $node;
        }

        return $this->primary();
    }

    /**
     * @return array<int, mixed>
     */
    private function primary(): array
    {
        $token = $this->peek();

        switch ($token[0]) {
            case 'number':
                $this->take('number');

                return ['num', Decimal::of($token[1])];

            case 'reference':
                $this->take('reference');

                return ['ref', $token[1], $token[2]];

            case '(':
                $this->take('(');
                $node = $this->expression();
                $this->take(')');

                return $node;

            case 'round':
                $this->take('round');
                $this->take('(');
                $node = $this->expression();
                $this->take(',');
                $scaleToken = $this->take('number');

                if (!ctype_digit($scaleToken[1]) || (int) $scaleToken[1] > 8) {
                    throw new ParseError('badRoundScale', $scaleToken[2]);
                }

                $this->take(')');

                return ['round', $node, (int) $scaleToken[1]];
        }

        throw new ParseError($token[0] === 'end' ? 'unexpectedEnd' : 'unexpectedToken', $token[2]);
    }
}
