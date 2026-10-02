<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Finance\Editing;

use Espo\Modules\Itvolga\Tools\Finance\Decimal;
use Espo\Modules\Itvolga\Tools\Finance\Document;
use Espo\Modules\Itvolga\Tools\Finance\Exceptions\InvalidValue;
use Espo\Modules\Itvolga\Tools\Finance\TaxMode;

/**
 * Calculation inputs of a document header: tax mode, discount (amount or percent), shipping, shipping tax and
 * adjustment, as entered. A change of any of them recalculates the document.
 */
final class HeaderInputs
{
    public const DECIMALS = ['discountAmount', 'discountPercent', 'shippingAmount', 'shippingTaxPercent', 'adjustment'];

    /**
     * @param array<string, Decimal> $values keyed by DECIMALS
     */
    public function __construct(
        public readonly TaxMode $taxMode,
        public readonly array $values,
    ) {}

    /**
     * @param array<string, mixed> $raw NULL or '' read as zero; an empty tax mode is the default «individual»
     */
    public static function fromArray(array $raw): self
    {
        $mode = $raw['taxMode'] ?? null;

        if ($mode === null || $mode === '') {
            $mode = TaxMode::Individual->value;
        }

        if (!is_string($mode) || !TaxMode::tryFrom($mode)) {
            throw new InvalidValue('Unknown tax mode.', 'taxMode', null, 'taxMode');
        }

        $values = [];

        foreach (self::DECIMALS as $field) {
            $value = $raw[$field] ?? null;
            $values[$field] = $value === null || $value === ''
                ? Decimal::zero()
                : Values::decimal($value, $field, null);
        }

        return new self(TaxMode::from($mode), $values);
    }

    public function value(string $field): Decimal
    {
        return $this->values[$field];
    }

    public function equals(self $other): bool
    {
        if ($this->taxMode !== $other->taxMode) {
            return false;
        }

        foreach (self::DECIMALS as $field) {
            if (!$this->values[$field]->equals($other->values[$field])) {
                return false;
            }
        }

        return true;
    }

    /**
     * @param list<LineInput> $lines
     */
    public function toDocument(array $lines): Document
    {
        return Document::of(
            $this->taxMode,
            array_map(static fn (LineInput $line) => $line->toLine(), $lines),
            $this->values['discountAmount'],
            $this->values['discountPercent'],
            $this->values['shippingAmount'],
            $this->values['shippingTaxPercent'],
            $this->values['adjustment'],
        );
    }
}
