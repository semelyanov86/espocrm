<?php

// Deliberately WITHOUT declare(strict_types=1): the engine would coerce a float argument of a typed parameter here,
// which is how EspoCRM code (non-strict) will call the finance core.

namespace Itvolga\Tests\Finance\Support;

use Espo\Modules\Itvolga\Tools\Finance\Decimal;

final class NonStrictCaller
{
    /**
     * @return list<callable(): mixed>
     */
    public static function floatOperations(): array
    {
        $one = Decimal::of('1');

        return [
            static fn () => $one->add(0.1),
            static fn () => $one->sub(0.1),
            static fn () => $one->mul(0.1),
            static fn () => $one->percent(12.5),
            static fn () => $one->compare(0.5),
            static fn () => $one->equals(1.0),
            static fn () => Decimal::of(0.1),
        ];
    }
}
