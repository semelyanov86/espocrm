<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Finance;

use Espo\Modules\Itvolga\Tools\Finance\Exceptions\InvalidValue;

/**
 * Quote, SalesOrder, Invoice or Act: tax regime, lines and header adjustments (NULL read as zero).
 */
final class Document
{
    /**
     * @param list<Line> $lines
     */
    public function __construct(
        public readonly TaxMode $taxMode,
        public readonly array $lines,
        public readonly Decimal $discountAmount,
        public readonly Decimal $discountPercent,
        public readonly Decimal $shippingAmount,
        public readonly Decimal $shippingTaxPercent,
        public readonly Decimal $adjustment,
    ) {
        foreach ($lines as $line) {
            if (!$line instanceof Line) {
                throw new InvalidValue('Document lines must be Line objects.');
            }
        }
    }

    /**
     * @param list<Line> $lines
     */
    public static function of(
        TaxMode|string $taxMode,
        array $lines,
        mixed $discountAmount = null,
        mixed $discountPercent = null,
        mixed $shippingAmount = null,
        mixed $shippingTaxPercent = null,
        mixed $adjustment = null,
    ): self {
        return new self(
            $taxMode instanceof TaxMode ? $taxMode : TaxMode::fromSource($taxMode),
            array_values($lines),
            Decimal::ofNullable($discountAmount),
            Decimal::ofNullable($discountPercent),
            Decimal::ofNullable($shippingAmount),
            Decimal::ofNullable($shippingTaxPercent),
            Decimal::ofNullable($adjustment),
        );
    }

    public function hasLineTax(): bool
    {
        foreach ($this->lines as $line) {
            if (!$line->taxPercent->isZero()) {
                return true;
            }
        }

        return false;
    }

    public function netSum(): Decimal
    {
        return Decimal::sum(array_map(static fn (Line $line) => $line->net(), $this->lines));
    }
}
