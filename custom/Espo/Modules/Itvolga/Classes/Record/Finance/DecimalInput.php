<?php

namespace Espo\Modules\Itvolga\Classes\Record\Finance;

use Espo\Core\Record\Input\Data;
use Espo\Core\Record\Input\Filter;
use Espo\Core\Utils\Metadata;
use Espo\Modules\Itvolga\Tools\Finance\Editing\LineInput;
use Espo\Modules\Itvolga\Tools\Finance\Exceptions\InvalidValue;
use Espo\Modules\Itvolga\Tools\Finance\Payment\AllocationInput;
use Espo\Modules\Itvolga\Tools\FinanceDocument\DocumentProcessor;
use Espo\Modules\Itvolga\Tools\FinanceDocument\DocumentTypes;
use Espo\Modules\Itvolga\Tools\FinanceDocument\ErrorMapper;
use Espo\Modules\Itvolga\Tools\FinancePayment\PaymentProcessor;

/**
 * Money and other decimals of finance documents and payments arrive as decimal strings (or integers), never as JSON
 * floats: the core sanitizer would turn a float into a string that may already have lost digits, and the ORM silently
 * stores a malformed string as NULL. Runs on the raw input of create, update and mass update, before any of that; the
 * rows of the record's table (`itemList` of a document, `allocationList` of a payment) are checked as well.
 */
class DecimalInput implements Filter
{
    private const PATTERN = '/^-?\d+(\.\d+)?$/';

    public function __construct(
        private string $entityType,
        private Metadata $metadata,
        private DocumentTypes $types,
        private ErrorMapper $errorMapper,
    ) {}

    public function filter(Data $data): void
    {
        $table = $this->table();

        if (!$table) {
            return;
        }

        [$listAttribute, $decimals, $lineScope] = $table;

        try {
            foreach ($data->getAttributeList() as $attribute) {
                if ($this->isDecimalField($attribute)) {
                    $this->check($data->get($attribute), $attribute, null);
                }
            }

            $rows = $data->get($listAttribute);

            if (is_array($rows)) {
                foreach (array_values($rows) as $index => $row) {
                    foreach ($decimals as $field) {
                        $this->check(((array) $row)[$field] ?? null, $field, $index + 1);
                    }
                }
            }
        } catch (InvalidValue $e) {
            throw $this->errorMapper->toBadRequestIn($e, $this->entityType, $lineScope);
        }
    }

    /**
     * @return ?array{string, list<string>, string} the table attribute, its decimal inputs and the scope of its rows
     */
    private function table(): ?array
    {
        if ($type = $this->types->find($this->entityType)) {
            return [DocumentProcessor::ITEM_LIST, LineInput::DECIMALS, $type->itemEntityType];
        }

        if ($type = $this->types->findPayment($this->entityType)) {
            return [PaymentProcessor::ALLOCATION_LIST, AllocationInput::DECIMALS, $type->allocationEntityType];
        }

        return null;
    }

    private function isDecimalField(string $attribute): bool
    {
        $fieldType = $this->metadata->get(['entityDefs', $this->entityType, 'fields', $attribute, 'type']);

        return $fieldType === 'decimal' || $fieldType === 'currency';
    }

    private function check(mixed $value, string $field, ?int $line): void
    {
        if ($value === null || $value === '' || is_int($value)) {
            return;
        }

        if (is_float($value)) {
            throw new InvalidValue("$field: float", 'float', $line, $field);
        }

        if (!is_string($value) || !preg_match(self::PATTERN, $value)) {
            throw new InvalidValue("$field: not a decimal", 'notDecimal', $line, $field);
        }
    }
}
