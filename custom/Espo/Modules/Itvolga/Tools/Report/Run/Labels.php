<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Run;

use Espo\Core\Utils\Language;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\Aggregate;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\Definition;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\FieldInfo;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\GroupLevel;

/**
 * Standard headers of a result in the user's language: «Контрагент → Город» for a related field, «Сумма: Итого» for an
 * aggregate, «Дата счёта (месяц)» for a date group; an override of the report (labels) wins when not empty.
 */
final class Labels
{
    public function __construct(
        private readonly Language $language,
        private readonly Definition $definition,
    ) {}

    public function field(FieldInfo $field): string
    {
        $label = $this->language->translate($field->ref->field, 'fields', $field->entityType);

        if ($field->ref->link === null) {
            return $label;
        }

        return $this->language->translate($field->ref->link, 'links', $this->definition->entityType) . ' → ' . $label;
    }

    public function column(FieldInfo $field): string
    {
        return $this->definition->labels['c:' . $field->ref->toString()] ?? $this->field($field);
    }

    public function group(int $index, GroupLevel $group): string
    {
        $default = $this->field($group->field);

        if ($group->granularity !== null) {
            $default .= ' (' . $this->language->translateOption($group->granularity->value, 'granularity', 'Report') .
                ')';
        }

        return $this->definition->labels['g:' . ($index + 1)] ?? $default;
    }

    public function aggregate(Aggregate $aggregate): string
    {
        $override = $this->definition->labels['a:' . $aggregate->key()] ?? null;

        if ($override !== null) {
            return $override;
        }

        $function = $this->language->translateOption($aggregate->function, 'aggregateFunction', 'Report');

        return $aggregate->field === null ? $function : $function . ': ' . $this->field($aggregate->field);
    }

    public function function(string $function): string
    {
        return $this->language->translateOption($function, 'aggregateFunction', 'Report');
    }
}
