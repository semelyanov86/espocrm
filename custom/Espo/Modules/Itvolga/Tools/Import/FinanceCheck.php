<?php

namespace Espo\Modules\Itvolga\Tools\Import;

use Espo\Core\ORM\Entity as CoreEntity;
use Espo\Modules\Itvolga\Tools\Finance\Exceptions\UnknownLegalEntity;
use Espo\Modules\Itvolga\Tools\Finance\Source\MarginCheck;
use Espo\Modules\Itvolga\Tools\Finance\Source\TotalCheck;
use Espo\Modules\Itvolga\Tools\FinanceDocument\DocumentTypes;
use Espo\Modules\Itvolga\Tools\FinanceDocument\LegalEntityProvider;
use Espo\Modules\Itvolga\Tools\FinanceDocument\SourceMarks;
use Espo\Modules\Itvolga\Tools\FinanceDocument\SourceVerification;
use stdClass;

/**
 * What the check pass of the import reports about a stored finance record (stage 06.3): the source verification of a
 * document (formula class, each total exact/rounded/mismatch, line margins, reasons as closed codes, the recomputed
 * totals when a total is not exact — the private report of rounding discrepancies), whether its stored source marks
 * are the computed ones, and whether the legal entity is the one its source spcompany resolves to.
 */
class FinanceCheck
{
    /** SourceVerifier reason → closed code (the reasons carry no source values, codes keep the report uniform). */
    private const REASONS = [
        'no lines' => 'no_lines',
        'document percent discount' => 'document_percent_discount',
        'percent discount' => 'line_percent_discount',
        'non-positive quantity' => 'non_positive_quantity',
        'negative unit price' => 'negative_unit_price',
        'negative discount (not' => 'negative_line_discount',
        'negative tax rate' => 'negative_tax_rate',
        'negative line sum' => 'negative_line_sum',
        'negative document discount' => 'negative_document_discount',
        'shipping amount' => 'shipping_amount',
        'shipping tax' => 'shipping_tax',
        'adjustment' => 'adjustment',
        'group tax with different' => 'group_tax_unsupported',
        'line tax on a document' => 'line_tax_after_upgrade',
    ];

    public function __construct(
        private DocumentTypes $types,
        private SourceVerification $verification,
        private LegalEntityProvider $legalEntities,
        private FinanceRules $rules,
    ) {}

    /**
     * @return ?array<string, mixed> null for an entity type that is not a finance document
     */
    public function document(CoreEntity $document): ?array
    {
        $type = $this->types->find($document->getEntityType());

        if (!$type) {
            return null;
        }

        if ($this->rules->isRecalculated($document)) {
            return ['recalculated' => true];
        }

        $result = $this->verification->verify($document, $type);

        if (!$result) {
            return ['formula' => null, 'reasons' => ['no_region_id']];
        }

        $margins = [];
        $marginLines = [];

        foreach ($result->margins as $i => $margin) {
            $margins[$margin->value] = ($margins[$margin->value] ?? 0) + 1;

            if ($margin === MarginCheck::Mismatch || $margin === MarginCheck::Absent) {
                $marginLines[] = $i + 1;
            }
        }

        $worst = $result->worstCheck();
        $block = [
            'formula' => $result->formulaClass->value,
            'checks' => array_map(static fn (TotalCheck $check) => $check->value, $result->checks),
            'worst' => $worst?->value ?? 'unverified',
            'margins' => $margins,
            'marginLines' => $marginLines,
            'reasons' => array_values(array_unique(array_map([$this, 'reason'], $result->reasons))),
            'marks' => SourceMarks::differs($document, SourceMarks::of($result)) ? 'differs' : 'equal',
        ];

        if ($worst !== null && $worst !== TotalCheck::Exact) { // the private report of rounding discrepancies
            $block['expected'] = [
                'subtotal' => $result->expectedSubtotal?->toString(),
                'preTaxTotal' => $result->expectedPreTaxTotal?->toString(),
                'taxAmount' => $result->expectedTaxAmount?->toString(),
                'grandTotal' => $result->expectedGrandTotal?->toString(),
            ];
        }

        return $block;
    }

    /**
     * 'ok' when the stored legal entity is the one the source spcompany resolves to, 'differs' otherwise; null for
     * records without a legal entity.
     */
    public function legalEntity(CoreEntity $record): ?string
    {
        if (!$this->types->find($record->getEntityType()) && !$this->types->findPayment($record->getEntityType())) {
            return null;
        }

        $data = $record->get('vtigerData');
        $value = $data instanceof stdClass ? ($data->{LegalEntityProvider::SOURCE_KEY} ?? null) : null;

        try {
            $id = $this->legalEntities->findIdForSource(is_string($value) ? $value : null);
        } catch (UnknownLegalEntity) {
            return 'differs';
        }

        return $id !== null && $record->get('legalEntityId') === $id ? 'ok' : 'differs';
    }

    private function reason(string $reason): string
    {
        foreach (self::REASONS as $needle => $code) {
            if (str_contains($reason, $needle)) {
                return $code;
            }
        }

        return 'other';
    }
}
