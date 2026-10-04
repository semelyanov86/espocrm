<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Definition;

use Espo\Modules\Itvolga\Tools\Report\Core\Granularity;

final class GroupLevel
{
    public function __construct(
        public readonly FieldInfo $field,
        public readonly ?Granularity $granularity,
        public readonly string $direction,
    ) {}

    /**
     * @return array<string, ?string>
     */
    public function toArray(): array
    {
        return ['field' => $this->field->ref->toString(), 'granularity' => $this->granularity?->value,
            'direction' => $this->direction];
    }
}
