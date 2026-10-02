<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\FinanceDocument;

use Espo\Core\Exceptions\BadRequest;
use Espo\Core\Exceptions\Error\Body;
use Espo\Core\Utils\Language;
use Espo\Modules\Itvolga\Tools\Finance\Exceptions\InvalidValue;
use Espo\Modules\Itvolga\Tools\Finance\Exceptions\RuleNotSupported;

/**
 * Refusals of the finance core as translated messages (Global.messages.finance*) with the line and the field
 * label, never with the refused value. Field labels come from the record's scope (document, payment) or, for a line,
 * from the scope of its rows (items, allocations).
 */
class ErrorMapper
{
    private const FALLBACK = 'financeRejected';

    public function __construct(private Language $language) {}

    public function toBadRequest(InvalidValue|RuleNotSupported $e, DocumentType $type): BadRequest
    {
        return $this->toBadRequestIn($e, $type->entityType, $type->itemEntityType);
    }

    public function message(InvalidValue|RuleNotSupported $e, DocumentType $type): string
    {
        return $this->messageIn($e, $type->entityType, $type->itemEntityType);
    }

    public function toBadRequestIn(InvalidValue|RuleNotSupported $e, string $scope, string $lineScope): BadRequest
    {
        [$label, $data] = $this->describe($e, $scope, $lineScope);

        return BadRequest::createWithBody($label, Body::create()->withMessageTranslation($label, 'Global', $data));
    }

    public function messageIn(InvalidValue|RuleNotSupported $e, string $scope, string $lineScope): string
    {
        [$label, $data] = $this->describe($e, $scope, $lineScope);
        $text = $this->language->translateLabel($label, 'messages');

        foreach ($data as $key => $value) {
            $text = str_replace('{' . $key . '}', $value, $text);
        }

        return $text;
    }

    /**
     * A translated error without a core exception (configuration, unknown product …).
     *
     * @param array<string, string> $data
     */
    public static function badRequest(string $label, array $data = []): BadRequest
    {
        return BadRequest::createWithBody($label, Body::create()->withMessageTranslation($label, 'Global', $data));
    }

    /**
     * @return array{string, array<string, string>}
     */
    private function describe(InvalidValue|RuleNotSupported $e, string $scope, string $lineScope): array
    {
        $code = $e instanceof RuleNotSupported ? $e->rule : ($e->key ?? '');
        $label = 'finance' . str_replace(' ', '', ucwords(str_replace('-', ' ', $code)));

        if ($code === '' || $this->language->translateLabel($label, 'messages') === $label) {
            $label = self::FALLBACK;
        }

        return [$label, [
            'place' => $this->place($e->documentLine, $e->field, $scope, $lineScope),
            'reference' => $e instanceof RuleNotSupported ? $e->reference : '',
        ]];
    }

    private function place(?int $line, ?string $field, string $scope, string $lineScope): string
    {
        $fieldScope = $line === null ? $scope : $lineScope;
        $fieldLabel = $field === null ? null : $this->language->translateLabel($field, 'fields', $fieldScope);

        if ($line !== null) {
            $text = $this->language->translateLabel($fieldLabel === null ? 'financePlaceLine' : 'financePlaceLineField',
                'labels');

            return str_replace(['{line}', '{field}'], [(string) $line, (string) $fieldLabel], $text);
        }

        if ($fieldLabel !== null) {
            return str_replace('{field}', $fieldLabel,
                $this->language->translateLabel('financePlaceField', 'labels'));
        }

        return $this->language->translateLabel('financePlaceDocument', 'labels');
    }
}
