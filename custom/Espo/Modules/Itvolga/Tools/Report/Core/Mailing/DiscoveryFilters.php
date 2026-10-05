<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Mailing;

/**
 * Conditions of the search for «generate for» users (D-122): the report's conditions with «текущий пользователь» /
 * «не текущий пользователь» taken as true. In the search that user would be the owner, and a report like «my tasks»
 * (responsible = current user) would find the owner only; each found user's own run applies the condition to himself.
 * A true condition leaves an AND group and makes an OR group true, so the search can only widen, never what a
 * recipient gets.
 */
final class DiscoveryFilters
{
    private const CURRENT_USER = ['isCurrentUser', 'isNotCurrentUser'];

    /**
     * @param array<string, mixed> $filters a canonical condition tree (group {type, items})
     * @return array<string, mixed>
     */
    public static function withoutCurrentUser(array $filters): array
    {
        return self::group($filters) ?? ['type' => 'and', 'items' => []];
    }

    /**
     * @param array<string, mixed> $group
     * @return ?array<string, mixed> null — always true
     */
    private static function group(array $group): ?array
    {
        $type = ($group['type'] ?? 'and') === 'or' ? 'or' : 'and';
        $items = [];

        foreach ($group['items'] ?? [] as $item) {
            $kept = isset($item['items']) ? self::group($item) : self::condition($item);

            if ($kept === null) {
                if ($type === 'or') {
                    return null;
                }

                continue;
            }

            $items[] = $kept;
        }

        return $items === [] && ($group['items'] ?? []) !== [] ? null : ['type' => $type, 'items' => $items];
    }

    /**
     * @param array<string, mixed> $item
     * @return ?array<string, mixed>
     */
    private static function condition(array $item): ?array
    {
        $where = self::where($item['where'] ?? []);

        if ($where === null) {
            return null;
        }

        $item['where'] = $where;

        return $item;
    }

    /**
     * @param array<string, mixed> $where
     * @return ?array<string, mixed> null — always true
     */
    private static function where(array $where): ?array
    {
        $type = $where['type'] ?? null;

        if (in_array($type, self::CURRENT_USER, true)) {
            return null;
        }

        if ($type !== 'and' && $type !== 'or') {
            return $where;
        }

        $value = [];

        foreach ($where['value'] ?? [] as $sub) {
            $kept = is_array($sub) ? self::where($sub) : null;

            if ($kept === null) {
                if ($type === 'or') {
                    return null;
                }

                continue;
            }

            $value[] = $kept;
        }

        if ($value === []) {
            return null;
        }

        $where['value'] = $value;

        return $where;
    }
}
