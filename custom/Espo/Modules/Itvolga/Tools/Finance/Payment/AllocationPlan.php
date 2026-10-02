<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Finance\Payment;

use Espo\Modules\Itvolga\Tools\Finance\Decimal;

/**
 * What a save does with the allocation table of a payment.
 */
final class AllocationPlan
{
    /**
     * @param list<PlannedAllocation> $rows the table after the save, in order
     * @param list<AllocationInput> $removed stored rows that the save removes
     * @param list<string> $affected target keys ("Invoice:<id>") whose paid sum changes, sorted
     */
    public function __construct(
        public readonly array $rows,
        public readonly array $removed,
        public readonly array $affected,
        public readonly Decimal $allocated,
        public readonly Decimal $remainder,
    ) {}

    public function changed(): bool
    {
        if ($this->removed !== []) {
            return true;
        }

        foreach ($this->rows as $row) {
            if ($row->changed()) {
                return true;
            }
        }

        return false;
    }

    /**
     * Every document of the stored and the planned rows, sorted: the documents a save locks.
     *
     * @return list<string>
     */
    public function documents(): array
    {
        $keys = [];

        foreach ($this->rows as $row) {
            $keys[] = $row->input->targetKey();

            if ($row->previous) {
                $keys[] = $row->previous->targetKey();
            }
        }

        foreach ($this->removed as $row) {
            $keys[] = $row->targetKey();
        }

        return self::sortedKeys($keys);
    }

    /**
     * @param iterable<string> $keys
     * @return list<string> unique, in the global lock order (entity type, then id)
     */
    public static function sortedKeys(iterable $keys): array
    {
        $keys = array_values(array_unique([...$keys]));
        sort($keys, SORT_STRING);

        return $keys;
    }
}
