<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Finance\Editing;

use Espo\Modules\Itvolga\Tools\Finance\Decimal;
use Espo\Modules\Itvolga\Tools\Finance\Exceptions\InvalidValue;
use Espo\Modules\Itvolga\Tools\Finance\Line;

/**
 * One document line as the user (item editor, API) or the database gives it: the item id (null for a new line),
 * product, description and the calculation inputs. Amount and margin are outputs and never read from the input.
 */
final class LineInput
{
    /** Calculation inputs of a line; a change of any of them recalculates the document. */
    public const DECIMALS = ['quantity', 'unitPrice', 'discountAmount', 'discountPercent', 'taxRate', 'purchaseCost'];

    private const REQUIRED = ['quantity', 'unitPrice'];

    /**
     * @param array<string, Decimal> $values keyed by DECIMALS
     */
    public function __construct(
        public readonly ?string $id,
        public readonly string $productId,
        public readonly ?string $description,
        public readonly array $values,
    ) {}

    /**
     * @param array<string, mixed> $raw decimal strings or ints; a float is refused (it may already have lost digits)
     * @param int $line 1-based position, for messages
     */
    public static function fromArray(array $raw, int $line): self
    {
        $id = $raw['id'] ?? null;
        $productId = $raw['productId'] ?? null;
        $description = $raw['description'] ?? null;

        if ($id !== null && (!is_string($id) || $id === '')) {
            throw new InvalidValue("Line $line: bad id.", 'badLine', $line, 'id');
        }

        if (!is_string($productId) || $productId === '') {
            throw new InvalidValue("Line $line: product is required.", 'required', $line, 'product');
        }

        if ($description !== null && !is_string($description)) {
            throw new InvalidValue("Line $line: bad description.", 'badLine', $line, 'description');
        }

        $values = [];

        foreach (self::DECIMALS as $field) {
            $required = in_array($field, self::REQUIRED, true);
            $values[$field] = self::decimal($raw[$field] ?? null, $field, $line, $required);
        }

        return new self($id, $productId, $description, $values);
    }

    public function value(string $field): Decimal
    {
        return $this->values[$field];
    }

    public function withId(?string $id): self
    {
        return new self($id, $this->productId, $this->description, $this->values);
    }

    public function toLine(): Line
    {
        return Line::of(
            $this->values['quantity'],
            $this->values['unitPrice'],
            $this->values['discountAmount'],
            $this->values['discountPercent'],
            $this->values['taxRate'],
            $this->values['purchaseCost'],
        );
    }

    /**
     * Canonical text of the calculation inputs ("1.000" and "1" are the same value).
     */
    public function calculationKey(): string
    {
        return implode('|', array_map(static fn (Decimal $value) => $value->toString(), $this->values));
    }

    private static function decimal(mixed $value, string $field, int $line, bool $required): Decimal
    {
        if ($value === null || $value === '') {
            if ($required) {
                throw new InvalidValue("Line $line: $field is required.", 'required', $line, $field);
            }

            return Decimal::zero();
        }

        return Values::decimal($value, $field, $line);
    }
}
