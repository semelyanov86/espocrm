<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Info;

use Espo\Modules\Itvolga\Tools\Report\Core\Definition\FieldInfo;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\WhereRules;

/**
 * Readable text of the conditions of a report for the report info of a letter (D-124): groups И/ИЛИ in brackets,
 * «Поле: оператор значения». Only the canonical where items are read — never `advanced`, the interface state in which
 * the author's client keeps names of records (the names come from ConditionWords, with the ACL of the reader).
 */
final class ConditionText
{
    private const NO_VALUE = ['isNull', 'isNotNull', 'any', 'isTrue', 'isFalse', 'ever', 'arrayIsEmpty',
        'arrayIsNotEmpty', 'isLinked', 'isNotLinked', 'isCurrentUser', 'isNotCurrentUser'];

    /**
     * @param array<string, mixed> $filters the condition tree of a checked definition
     * @param array<string, FieldInfo> $fields ref → field of every condition
     */
    public static function describe(array $filters, array $fields, ConditionWords $words): string
    {
        return self::group($filters, $fields, $words, 0);
    }

    /**
     * @param array<string, mixed> $group
     * @param array<string, FieldInfo> $fields
     */
    private static function group(array $group, array $fields, ConditionWords $words, int $depth): string
    {
        $parts = [];

        foreach ($group['items'] ?? [] as $item) {
            if (isset($item['items'])) {
                $inner = self::group($item, $fields, $words, $depth + 1);
                $parts[] = $inner !== '' ? '(' . $inner . ')' : '';

                continue;
            }

            $field = $fields[$item['field'] ?? ''] ?? null;

            if ($field !== null && is_array($item['where'] ?? null)) {
                $parts[] = $words->field($field) . ': ' . self::where($item['where'], $field, $words);
            }
        }

        return implode(' ' . $words->joiner($group['type'] ?? 'and') . ' ', array_filter($parts));
    }

    /**
     * @param array<string, mixed> $where
     */
    private static function where(array $where, FieldInfo $field, ConditionWords $words): string
    {
        $type = (string) ($where['type'] ?? '');

        if ($type === 'and' || $type === 'or') {
            return '(' . implode(' ' . $words->joiner($type) . ' ', array_map(
                fn ($sub) => is_array($sub) ? self::where($sub, $field, $words) : '', $where['value'] ?? [])) . ')';
        }

        if ($type === 'compareField') {
            return $words->compare((string) ($where['value']['operator'] ?? ''),
                (string) ($where['value']['field'] ?? ''));
        }

        $operator = $words->operator($type);

        if (in_array($type, self::NO_VALUE, true) || in_array($type, WhereRules::RELATIVE_DATE_TYPES, true)) {
            return $operator;
        }

        if (in_array($type, WhereRules::DAYS_TYPES, true)) {
            return $operator . ': ' . (int) ($where['value'] ?? 0);
        }

        $value = $where['value'] ?? null;
        $values = $words->values($field, is_array($value) ? array_values($value) : [$value]);

        return $operator . ' ' . implode($type === 'between' ? ' — ' : ', ', $values);
    }
}
