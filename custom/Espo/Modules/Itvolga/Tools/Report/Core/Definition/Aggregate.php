<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Definition;

/**
 * COUNT of records of the main entity (no field) or SUM/AVG/MIN/MAX of a numeric field; key() is its id in labels,
 * the group sort, HAVING and the result ("COUNT", "SUM:grandTotal", "AVG:items.quantity").
 */
final class Aggregate
{
    public const FUNCTIONS = ['COUNT', 'SUM', 'AVG', 'MIN', 'MAX'];

    public function __construct(
        public readonly string $function,
        public readonly ?FieldInfo $field = null,
    ) {}

    public function key(): string
    {
        return $this->field === null ? $this->function : $this->function . ':' . $this->field->ref->toString();
    }

    /**
     * @return array<string, ?string>
     */
    public function toArray(): array
    {
        return ['function' => $this->function, 'link' => $this->field?->ref->link, 'field' => $this->field?->ref->field];
    }
}
