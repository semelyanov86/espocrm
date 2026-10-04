<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Definition;

/**
 * Which where items a condition of a field may hold (reports.md §4): the core search types the field views of
 * EspoCRM produce for the field family, plus the report types the core lacks (relative periods, "current user",
 * comparison with another date field). Values are checked by shape; they reach SQL only as ORM parameters.
 */
final class WhereRules
{
    public const MAX_DEPTH = 3;
    public const MAX_DAYS = 3650;
    public const MAX_LIST = 500;
    public const MAX_TEXT = 1000;

    /** Report period types resolved by the module at run time (D-92). */
    public const RELATIVE_DATE_TYPES = ['today', 'yesterday', 'tomorrow', 'past', 'future', 'lastSevenDays',
        'currentWeek', 'lastWeek', 'nextWeek', 'currentMonth', 'lastMonth', 'nextMonth', 'currentQuarter',
        'lastQuarter', 'nextQuarter', 'currentYear', 'lastYear', 'nextYear', 'currentFiscalYear', 'lastFiscalYear',
        'currentFiscalQuarter', 'lastFiscalQuarter'];
    public const DAYS_TYPES = ['lastXDays', 'nextXDays', 'olderThanXDays', 'afterXDays', 'xDaysAgo', 'inXDays'];
    public const COMPARE_OPERATORS = ['equals', 'notEquals', 'lessThan', 'greaterThan', 'lessThanOrEquals',
        'greaterThanOrEquals'];

    private const TEXT = ['equals', 'notEquals', 'like', 'notLike', 'startsWith', 'endsWith', 'contains', 'notContains',
        'in', 'notIn', 'isNull', 'isNotNull', 'any'];
    private const ENUM = ['equals', 'notEquals', 'in', 'notIn', 'isNull', 'isNotNull', 'any'];
    private const NUMBER = ['equals', 'notEquals', 'greaterThan', 'lessThan', 'greaterThanOrEquals',
        'lessThanOrEquals', 'between', 'isNull', 'isNotNull'];
    private const BOOL = ['isTrue', 'isFalse'];
    private const DATE_ABSOLUTE = ['on', 'notOn', 'after', 'before', 'between', 'isNull', 'isNotNull', 'ever'];
    private const LINK = ['equals', 'notEquals', 'in', 'notIn', 'isNull', 'isNotNull'];
    private const USER_LINK = ['isCurrentUser', 'isNotCurrentUser'];
    private const MULTI_ENUM = ['arrayAnyOf', 'arrayNoneOf', 'arrayAllOf', 'arrayIsEmpty', 'arrayIsNotEmpty', 'any'];
    private const LINK_MULTIPLE = ['linkedWith', 'notLinkedWith', 'linkedWithAll', 'isLinked', 'isNotLinked'];
    private const NO_VALUE = ['isNull', 'isNotNull', 'any', 'isTrue', 'isFalse', 'ever', 'arrayIsEmpty',
        'arrayIsNotEmpty', 'isLinked', 'isNotLinked', 'isCurrentUser', 'isNotCurrentUser'];

    /**
     * Checks one stored where item of a condition and returns it normalised (unknown keys dropped).
     *
     * @return array<string, mixed>
     */
    public static function normalize(mixed $item, FieldInfo $field, string $path, int $depth = 1): array
    {
        if (!is_array($item) || !is_string($item['type'] ?? null)) {
            throw new DefinitionError('badCondition', $path);
        }

        $type = $item['type'];

        if (in_array($type, ['and', 'or'], true)) {
            if ($depth >= self::MAX_DEPTH || !is_array($item['value'] ?? null) || !array_is_list($item['value']) ||
                count($item['value']) > 20) {
                throw new DefinitionError('badCondition', $path);
            }

            return ['type' => $type, 'value' => array_map(
                fn ($sub, $i) => self::normalize($sub, $field, "$path.value[$i]", $depth + 1),
                $item['value'],
                array_keys($item['value']),
            )];
        }

        if (!in_array($type, self::typesFor($field), true)) {
            throw new DefinitionError('operatorNotAllowed', $path, ['operator' => $type]);
        }

        $attribute = $item['attribute'] ?? null;

        if (!is_string($attribute) || !in_array($attribute, $field->whereAttributes, true)) {
            throw new DefinitionError('badCondition', $path);
        }

        $result = ['type' => $type, 'attribute' => $attribute];

        if (!in_array($type, self::NO_VALUE, true) && !in_array($type, self::RELATIVE_DATE_TYPES, true)) {
            $result['value'] = self::value($type, $item['value'] ?? null, $field, $path);
        }

        if ($field->isDate()) {
            $result[$field->family() === FieldInfo::FAMILY_DATETIME ? 'dateTime' : 'date'] = true;
        }

        return $result;
    }

    /**
     * @return list<string>
     */
    public static function typesFor(FieldInfo $field): array
    {
        return match ($field->family()) {
            FieldInfo::FAMILY_TEXT, FieldInfo::FAMILY_LONG_TEXT => self::TEXT,
            FieldInfo::FAMILY_ENUM => self::ENUM,
            FieldInfo::FAMILY_NUMBER => self::NUMBER,
            FieldInfo::FAMILY_BOOL => self::BOOL,
            FieldInfo::FAMILY_DATE, FieldInfo::FAMILY_DATETIME =>
                [...self::DATE_ABSOLUTE, ...self::RELATIVE_DATE_TYPES, ...self::DAYS_TYPES,
                    ...($field->linkKind === FieldInfo::LINK_NONE ? ['compareField'] : [])],
            FieldInfo::FAMILY_LINK => [...self::LINK, ...($field->isUserLink() ? self::USER_LINK : [])],
            FieldInfo::FAMILY_LINK_PARENT => ['equals', 'notEquals', 'isNull', 'isNotNull'],
            FieldInfo::FAMILY_MULTI_ENUM => self::MULTI_ENUM,
            FieldInfo::FAMILY_LINK_MULTIPLE => [...self::LINK_MULTIPLE, ...($field->foreignEntityType === 'User' ?
                ['isCurrentUser'] : [])],
            default => [],
        };
    }

    private static function value(string $type, mixed $value, FieldInfo $field, string $path): mixed
    {
        if (in_array($type, self::DAYS_TYPES, true)) {
            $number = is_int($value) ? $value : (is_string($value) && ctype_digit($value) ? (int) $value : -1);

            if ($number < 0 || $number > self::MAX_DAYS) {
                throw new DefinitionError('badConditionValue', $path);
            }

            return $number;
        }

        if ($type === 'compareField') {
            if (!is_array($value) || !in_array($value['operator'] ?? null, self::COMPARE_OPERATORS, true) ||
                FieldRef::parse($value['field'] ?? null)?->isRelated() !== false) {
                throw new DefinitionError('badConditionValue', $path);
            }

            return ['operator' => $value['operator'], 'field' => $value['field']];
        }

        if (in_array($type, ['in', 'notIn', 'arrayAnyOf', 'arrayNoneOf', 'arrayAllOf', 'linkedWith', 'notLinkedWith',
            'linkedWithAll'], true)) {
            if (!is_array($value) || !array_is_list($value) || count($value) > self::MAX_LIST) {
                throw new DefinitionError('badConditionValue', $path);
            }

            return array_map(fn ($v) => self::scalar($v, $field, $path), $value);
        }

        if ($type === 'between') {
            if (!is_array($value) || !array_is_list($value) || count($value) !== 2) {
                throw new DefinitionError('badConditionValue', $path);
            }

            return [self::scalar($value[0], $field, $path), self::scalar($value[1], $field, $path)];
        }

        $scalar = self::scalar($value, $field, $path);

        if ($scalar === null) {
            throw new DefinitionError('badConditionValue', $path);
        }

        return $scalar;
    }

    private static function scalar(mixed $value, FieldInfo $field, string $path): string|int|bool|null
    {
        if ($value === null) {
            return null;
        }

        if ($field->family() === FieldInfo::FAMILY_NUMBER) {
            if (is_int($value) || is_string($value) && preg_match('/^-?\d{1,20}(\.\d{1,10})?$/', $value)) {
                return $value;
            }

            throw new DefinitionError('badConditionValue', $path);
        }

        if ($field->isDate()) {
            if (is_string($value) && preg_match('/^\d{4}-\d{2}-\d{2}( \d{2}:\d{2}(:\d{2})?)?$/', $value)) {
                return $value;
            }

            throw new DefinitionError('badConditionValue', $path);
        }

        if (is_string($value) && mb_strlen($value) <= self::MAX_TEXT || is_bool($value) || is_int($value)) {
            return $value;
        }

        throw new DefinitionError('badConditionValue', $path);
    }
}
