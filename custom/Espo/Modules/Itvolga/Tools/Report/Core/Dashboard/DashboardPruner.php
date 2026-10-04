<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Dashboard;

use Closure;

/**
 * Removes dashlets from a dashboard layout (D-113): the tabs `[{name, id?, layout: [{id, name, x, y, …}]}]` and the
 * options by dashlet id. Every tab is looked through; other dashlets, their places and options, and the properties
 * of the tabs stay as they are; malformed entries are kept untouched.
 */
final class DashboardPruner
{
    /**
     * @param mixed $layout tabs (decoded JSON)
     * @param mixed $options dashlet id → options (decoded JSON)
     * @param Closure(string, array<string, mixed>): bool $isTarget dashlet name and its options → remove it
     * @return ?array{list<mixed>, array<string, mixed>, list<string>} new layout, new options, removed ids; null when
     *     nothing is removed
     */
    public static function prune(mixed $layout, mixed $options, Closure $isTarget): ?array
    {
        $layout = is_array($layout) ? $layout : [];
        $options = is_array($options) ? $options : [];
        $removed = [];

        foreach ($layout as $t => $tab) {
            if (!is_array($tab) || !is_array($tab['layout'] ?? null)) {
                continue;
            }

            $kept = [];

            foreach ($tab['layout'] as $item) {
                $id = is_array($item) ? ($item['id'] ?? null) : null;
                $name = is_array($item) ? ($item['name'] ?? null) : null;
                $itemOptions = is_string($id) && is_array($options[$id] ?? null) ? $options[$id] : [];

                if (is_string($id) && is_string($name) && $isTarget($name, $itemOptions)) {
                    $removed[] = $id;

                    continue;
                }

                $kept[] = $item;
            }

            $layout[$t]['layout'] = $kept;
        }

        if ($removed === []) {
            return null;
        }

        foreach ($removed as $id) {
            unset($options[$id]);
        }

        return [array_values($layout), $options, $removed];
    }
}
