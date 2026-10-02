<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Finance\Payment;

/**
 * A row of the allocation table after planning: its input (with the id of the stored row it keeps, or none for a new
 * row), the stored row it replaces and its position.
 */
final class PlannedAllocation
{
    public function __construct(
        public readonly AllocationInput $input,
        /** 1-based position in the table. */
        public readonly int $order,
        public readonly ?AllocationInput $previous,
        public readonly ?int $previousOrder,
    ) {}

    public function isNew(): bool
    {
        return $this->previous === null;
    }

    /** The payment moved to another document (re-applied, as related_to was edited in Vtiger). */
    public function targetChanged(): bool
    {
        return $this->previous !== null && $this->previous->targetKey() !== $this->input->targetKey();
    }

    public function amountChanged(): bool
    {
        return $this->previous !== null && !$this->previous->amount->equals($this->input->amount);
    }

    public function changed(): bool
    {
        return $this->isNew() || $this->targetChanged() || $this->amountChanged() ||
            $this->previousOrder !== $this->order;
    }
}
