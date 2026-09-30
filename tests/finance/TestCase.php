<?php

declare(strict_types=1);

namespace Itvolga\Tests\Finance;

use Espo\Modules\Itvolga\Tools\Finance\Decimal;
use Throwable;

/**
 * Minimal assertions for tests/finance/run.php (no test framework is installed in this repository).
 */
abstract class TestCase
{
    public function setUp(): void {}

    protected function assertTrue(bool $condition, string $message = 'expected true'): void
    {
        if (!$condition) {
            throw new AssertionFailed($message);
        }
    }

    protected function assertSame(mixed $expected, mixed $actual, string $message = ''): void
    {
        if ($expected !== $actual) {
            throw new AssertionFailed(trim($message . ' expected ' . self::show($expected) . ', got ' . self::show($actual)));
        }
    }

    protected function assertDecimal(string $expected, ?Decimal $actual, string $message = ''): void
    {
        if ($actual === null || !$actual->equals($expected)) {
            throw new AssertionFailed(trim("$message expected $expected, got " . ($actual?->toString() ?? 'null')));
        }
    }

    /**
     * @param class-string<Throwable> $class
     */
    protected function assertThrows(string $class, callable $callback, ?string $contains = null): Throwable
    {
        try {
            $callback();
        } catch (Throwable $e) {
            if (!$e instanceof $class) {
                throw new AssertionFailed("expected $class, got " . $e::class . ': ' . $e->getMessage());
            }

            if ($contains !== null && !str_contains($e->getMessage(), $contains)) {
                throw new AssertionFailed("message '{$e->getMessage()}' does not contain '$contains'");
            }

            return $e;
        }

        throw new AssertionFailed("expected $class, nothing thrown");
    }

    protected function skip(string $reason): never
    {
        throw new Skipped($reason);
    }

    private static function show(mixed $value): string
    {
        if ($value instanceof \UnitEnum) {
            return $value::class . '::' . $value->name;
        }

        return str_replace("\n", ' ', var_export($value, true));
    }
}
