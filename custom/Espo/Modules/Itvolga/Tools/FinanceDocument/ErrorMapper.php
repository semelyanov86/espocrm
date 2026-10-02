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
 * label, never with the refused value.
 */
class ErrorMapper
{
    private const FALLBACK = 'financeRejected';

    public function __construct(private Language $language) {}

    public function toBadRequest(InvalidValue|RuleNotSupported $e, DocumentType $type): BadRequest
    {
        [$label, $data] = $this->describe($e, $type);

        return BadRequest::createWithBody($label, Body::create()->withMessageTranslation($label, 'Global', $data));
    }

    public function message(InvalidValue|RuleNotSupported $e, DocumentType $type): string
    {
        [$label, $data] = $this->describe($e, $type);
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
    private function describe(InvalidValue|RuleNotSupported $e, DocumentType $type): array
    {
        $code = $e instanceof RuleNotSupported ? $e->rule : ($e->key ?? '');
        $label = 'finance' . str_replace(' ', '', ucwords(str_replace('-', ' ', $code)));

        if ($code === '' || $this->language->translateLabel($label, 'messages') === $label) {
            $label = self::FALLBACK;
        }

        return [$label, [
            'place' => $this->place($e->documentLine, $e->field, $type),
            'reference' => $e instanceof RuleNotSupported ? $e->reference : '',
        ]];
    }

    private function place(?int $line, ?string $field, DocumentType $type): string
    {
        $scope = $line === null ? $type->entityType : $type->itemEntityType;
        $fieldLabel = $field === null ? null : $this->language->translateLabel($field, 'fields', $scope);

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
