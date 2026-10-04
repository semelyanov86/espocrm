<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Filter;

use Espo\Modules\Itvolga\Tools\Report\Core\Definition\FieldInfo;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\WhereRules;

/**
 * Turns the checked condition tree of a report into one raw where item of the EspoCRM core for a run (reports.md §4,
 * D-89, D-92). Relative periods become absolute on/before/after/between in the run's time zone (datetime fields carry
 * `dateTime` and `timeZone`, the core converts the local days to UTC); "current user" becomes the user's id; a field
 * of a related entity is wrapped into the module item `itvolgaRelated` (EXISTS over the related records the user may
 * read); a comparison of two date fields into `itvolgaFieldCompare`. The result goes through the core strict
 * where checker and converter, which check every attribute against the field ACL once more.
 */
final class WhereTranslator
{
    public const RELATED = 'itvolgaRelated';
    public const FIELD_COMPARE = 'itvolgaFieldCompare';

    /**
     * @param array<string, mixed> $tree normalised tree (DefinitionParser)
     * @param array<string, FieldInfo> $fields
     * @return ?array<string, mixed> null when there is no condition
     */
    public static function translate(array $tree, array $fields, RunContext $context): ?array
    {
        return self::node($tree, $fields, $context);
    }

    /**
     * @param array<string, mixed> $node
     * @param array<string, FieldInfo> $fields
     * @return ?array<string, mixed>
     */
    private static function node(array $node, array $fields, RunContext $context): ?array
    {
        if (isset($node['items'])) {
            $items = array_values(array_filter(array_map(
                fn ($item) => self::node($item, $fields, $context),
                $node['items'],
            )));

            if ($items === []) {
                return null;
            }

            return count($items) === 1 ? $items[0] : ['type' => $node['type'], 'value' => $items];
        }

        $field = $fields[$node['field']];
        $item = self::item($node['where'], $field, $context);

        if ($field->ref->link === null) {
            return $item;
        }

        return ['type' => self::RELATED, 'attribute' => 'id', 'value' => ['link' => $field->ref->link,
            'where' => [$item]]];
    }

    /**
     * @param array<string, mixed> $where
     * @return array<string, mixed>
     */
    private static function item(array $where, FieldInfo $field, RunContext $context): array
    {
        $type = $where['type'];

        if ($type === 'and' || $type === 'or') {
            return ['type' => $type, 'value' => array_map(fn ($w) => self::item($w, $field, $context),
                $where['value'])];
        }

        $attribute = $where['attribute'];
        $isDateTime = $field->family() === FieldInfo::FAMILY_DATETIME;

        if ($type === 'isCurrentUser') {
            return $field->family() === FieldInfo::FAMILY_LINK_MULTIPLE ?
                ['type' => 'linkedWith', 'attribute' => $attribute, 'value' => [$context->userId]] :
                ['type' => 'equals', 'attribute' => $attribute, 'value' => $context->userId];
        }

        if ($type === 'isNotCurrentUser') {
            return ['type' => 'or', 'value' => [
                ['type' => 'notEquals', 'attribute' => $attribute, 'value' => $context->userId],
                ['type' => 'isNull', 'attribute' => $attribute],
            ]];
        }

        if ($type === 'compareField') {
            return ['type' => self::FIELD_COMPARE, 'attribute' => $attribute, 'value' => [
                'operator' => $where['value']['operator'],
                'attribute' => $where['value']['field'],
                'timeZone' => $context->timeZone,
            ]];
        }

        if ($isDateTime && in_array($type, ['past', 'future'], true)) {
            return ['type' => $type, 'attribute' => $attribute, 'dateTime' => true, 'timeZone' => $context->timeZone];
        }

        if (in_array($type, WhereRules::RELATIVE_DATE_TYPES, true) || in_array($type, WhereRules::DAYS_TYPES, true)) {
            [$kind, $first, $second] = RelativePeriod::resolve($type, $where['value'] ?? null, $context);
            $item = match ($kind) {
                'range' => $first === $second ?
                    ['type' => 'on', 'attribute' => $attribute, 'value' => $first] :
                    ['type' => 'between', 'attribute' => $attribute, 'value' => [$first, $second]],
                default => ['type' => $kind, 'attribute' => $attribute, 'value' => $first],
            };

            return self::dated($item, $isDateTime, $context);
        }

        $item = ['type' => $type, 'attribute' => $attribute];

        if (array_key_exists('value', $where)) {
            $item['value'] = $where['value'];
        }

        return $field->isDate() ? self::dated($item, $isDateTime, $context) : $item;
    }

    /**
     * Date fields: `on` is a plain comparison of the date column; datetime fields: the core converts local days.
     *
     * @param array<string, mixed> $item
     * @return array<string, mixed>
     */
    private static function dated(array $item, bool $isDateTime, RunContext $context): array
    {
        if (!$isDateTime) {
            return $item;
        }

        return $item + ['dateTime' => true, 'timeZone' => $context->timeZone];
    }
}
