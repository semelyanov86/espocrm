<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Finance;

/**
 * Document line (vtiger_inventoryproductrel): values as stored, NULL read as zero.
 */
final class Line
{
    public function __construct(
        public readonly Decimal $quantity,
        public readonly Decimal $unitPrice,
        public readonly Decimal $discountAmount,
        public readonly Decimal $discountPercent,
        /** tax1 + tax2 + tax3, percent. */
        public readonly Decimal $taxPercent,
        /** Purchase cost of the whole line (Vtiger multiplies the unit cost by the quantity). */
        public readonly Decimal $purchaseCost,
        /** Stored margin of a source line; null for lines created in EspoCRM. */
        public readonly ?Decimal $margin = null,
    ) {}

    public static function of(
        mixed $quantity,
        mixed $unitPrice,
        mixed $discountAmount = null,
        mixed $discountPercent = null,
        mixed $taxPercent = null,
        mixed $purchaseCost = null,
        mixed $margin = null,
    ): self {
        return new self(
            Decimal::of($quantity),
            Decimal::of($unitPrice),
            Decimal::ofNullable($discountAmount),
            Decimal::ofNullable($discountPercent),
            Decimal::ofNullable($taxPercent),
            Decimal::ofNullable($purchaseCost),
            $margin === null ? null : Decimal::of($margin),
        );
    }

    /**
     * Source line with separate tax columns; tax2/tax3 are empty in the data but still added, as Vtiger does.
     */
    public static function fromSource(
        mixed $quantity,
        mixed $listPrice,
        mixed $discountAmount,
        mixed $discountPercent,
        mixed $tax1,
        mixed $tax2,
        mixed $tax3,
        mixed $purchaseCost,
        mixed $margin,
    ): self {
        $tax = Decimal::ofNullable($tax1)->add(Decimal::ofNullable($tax2))->add(Decimal::ofNullable($tax3));

        return self::of($quantity, $listPrice, $discountAmount, $discountPercent, $tax, $purchaseCost, $margin);
    }

    public function gross(): Decimal
    {
        return $this->quantity->mul($this->unitPrice);
    }

    /**
     * Exact line sum after the line discount: qty × price − discount amount − qty × price × discount % / 100
     * (the formula that reproduces every live source document, finance-contract.md §4).
     */
    public function net(): Decimal
    {
        $gross = $this->gross();

        return $gross->sub($this->discountAmount)->sub($gross->percent($this->discountPercent));
    }
}
