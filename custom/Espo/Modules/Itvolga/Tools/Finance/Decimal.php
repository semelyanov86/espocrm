<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Finance;

use Espo\Modules\Itvolga\Tools\Finance\Exceptions\InvalidValue;
use Stringable;

/**
 * Exact decimal number (bcmath). Floats are rejected on input and never produced: amounts travel as strings.
 *
 * A value keeps the scale it was written with; add, sub, mul and percent are exact, rounding happens only
 * through round() (half away from zero — «0,5 вверх» of D-29, symmetric for negative values like MySQL ROUND).
 * Every operand goes through of(): parameters are `mixed` on purpose, so that a float from code without
 * strict_types is rejected instead of being coerced to int or string by the engine.
 */
final class Decimal implements Stringable
{
    private const PATTERN = '/^-?\d+(\.\d+)?$/';

    private function __construct(
        private readonly string $value,
        private readonly int $scale,
    ) {}

    /**
     * @param mixed $value decimal string ("1500.00", "-0.5"), int or Decimal; float and other types are rejected
     */
    public static function of(mixed $value): self
    {
        if ($value instanceof self) {
            return $value;
        }

        if (is_int($value)) {
            return new self((string) $value, 0);
        }

        if (is_float($value)) {
            throw new InvalidValue('Float values are not accepted: pass the amount as a decimal string.');
        }

        if (!is_string($value)) {
            throw new InvalidValue('Unsupported decimal value type: ' . get_debug_type($value) . '.');
        }

        if (!preg_match(self::PATTERN, $value)) {
            throw new InvalidValue("Not a decimal number: '$value'.");
        }

        $dot = strpos($value, '.');
        $scale = $dot === false ? 0 : strlen($value) - $dot - 1;

        // bcadd normalises leading zeros and "-0" without changing the value.
        return new self(bcadd($value, '0', $scale), $scale);
    }

    /**
     * Null (SQL NULL, missing value) as zero; everything else as of().
     */
    public static function ofNullable(mixed $value): self
    {
        return $value === null ? self::zero() : self::of($value);
    }

    public static function zero(): self
    {
        return new self('0', 0);
    }

    /**
     * @param iterable<Decimal> $values
     */
    public static function sum(iterable $values): self
    {
        $result = self::zero();

        foreach ($values as $value) {
            $result = $result->add($value);
        }

        return $result;
    }

    public function add(mixed $other): self
    {
        $other = self::of($other);
        $scale = max($this->scale, $other->scale);

        return new self(bcadd($this->value, $other->value, $scale), $scale);
    }

    public function sub(mixed $other): self
    {
        $other = self::of($other);
        $scale = max($this->scale, $other->scale);

        return new self(bcsub($this->value, $other->value, $scale), $scale);
    }

    public function mul(mixed $other): self
    {
        $other = self::of($other);
        $scale = $this->scale + $other->scale;

        return new self(bcmul($this->value, $other->value, $scale), $scale);
    }

    /**
     * this × percent / 100, exact (division by 100 only moves the decimal point).
     */
    public function percent(mixed $percent): self
    {
        $product = $this->mul($percent);
        $scale = $product->scale + 2;

        return new self(bcdiv($product->value, '100', $scale), $scale);
    }

    public function negate(): self
    {
        return new self(bcsub('0', $this->value, $this->scale), $this->scale);
    }

    /**
     * Half away from zero to the given number of decimals. A value that already fits is returned unchanged in value.
     */
    public function round(int $scale): self
    {
        if ($scale < 0) {
            throw new InvalidValue('Negative rounding scale.');
        }

        if ($this->scale <= $scale) {
            return new self(bcadd($this->value, '0', $scale), $scale);
        }

        // bcadd truncates towards zero: adding ±0.5 of the last kept digit first gives half away from zero.
        $half = '0.' . str_repeat('0', $scale) . '5';

        if ($this->isNegative()) {
            $half = '-' . $half;
        }

        return new self(bcadd(bcadd($this->value, $half, $this->scale + 1), '0', $scale), $scale);
    }

    public function compare(mixed $other): int
    {
        $other = self::of($other);

        return bccomp($this->value, $other->value, max($this->scale, $other->scale));
    }

    public function equals(mixed $other): bool
    {
        return $this->compare($other) === 0;
    }

    public function isZero(): bool
    {
        return bccomp($this->value, '0', $this->scale) === 0;
    }

    public function isNegative(): bool
    {
        return bccomp($this->value, '0', $this->scale) < 0;
    }

    public function isPositive(): bool
    {
        return bccomp($this->value, '0', $this->scale) > 0;
    }

    /**
     * Number of significant decimals (trailing zeros do not count): "1500.00000000" has 0.
     */
    public function significantScale(): int
    {
        $text = $this->toString();
        $dot = strpos($text, '.');

        return $dot === false ? 0 : strlen($text) - $dot - 1;
    }

    /**
     * Fixed notation with exactly $scale decimals; refuses to drop significant digits (use round() first).
     */
    public function toFixed(int $scale): string
    {
        if ($this->significantScale() > $scale) {
            throw new InvalidValue("Value {$this->toString()} has more than $scale significant decimals.");
        }

        return bcadd($this->value, '0', $scale);
    }

    /**
     * Canonical shortest form: no trailing zeros, no "-0" ("1500.00000000" → "1500").
     */
    public function toString(): string
    {
        $text = $this->value;

        if (str_contains($text, '.')) {
            $text = rtrim(rtrim($text, '0'), '.');
        }

        return $text === '-0' ? '0' : $text;
    }

    public function __toString(): string
    {
        return $this->toString();
    }
}
