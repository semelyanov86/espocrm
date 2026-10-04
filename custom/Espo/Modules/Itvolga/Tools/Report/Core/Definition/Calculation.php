<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Definition;

use Espo\Modules\Itvolga\Tools\Report\Core\Calculation\Expression;

final class Calculation
{
    /**
     * @param list<string> $functions totals of the calculation: SUM, AVG, MIN, MAX
     */
    public function __construct(
        public readonly string $id,
        public readonly string $label,
        public readonly Expression $expression,
        public readonly array $functions,
    ) {}

    /**
     * @return array<string, mixed>
     */
    public function toArray(): array
    {
        return ['id' => $this->id, 'label' => $this->label, 'expression' => $this->expression->text,
            'functions' => $this->functions];
    }
}
