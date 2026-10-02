<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Finance\Editing;

use Espo\Modules\Itvolga\Tools\Finance\Decimal;

/**
 * A line to save: its input (id null — a new item), its position and, when the document was recalculated, the new
 * amount and margin. Null amount and margin keep the stored values.
 */
final class PlannedLine
{
    public function __construct(
        public readonly LineInput $input,
        public readonly int $order,
        public readonly ?Decimal $amount,
        public readonly ?Decimal $margin,
    ) {}
}
