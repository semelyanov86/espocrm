<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\FinanceDocument;

use Espo\Modules\Itvolga\Tools\Finance\Decimal;
use Espo\Modules\Itvolga\Tools\Finance\Document;
use Espo\Modules\Itvolga\Tools\Finance\Line;
use Espo\Modules\Itvolga\Tools\Finance\Source\SourceDocument;
use Espo\Modules\Itvolga\Tools\Finance\Source\SourceVerifier;
use Espo\Modules\Itvolga\Tools\Finance\Source\Verification;
use Espo\ORM\Entity;
use Espo\ORM\EntityManager;
use stdClass;

/**
 * `sourceFormula` and `totalsCheck` of an imported document (D-46): SourceVerifier classifies the stored totals by
 * the lines; the stored values are never changed (D-05). Needs the source `region_id` in vtigerData (NULL and 0 are
 * both meaningful): without the key the document is not classified rather than guessed.
 */
class SourceVerification
{
    public function __construct(
        private EntityManager $entityManager,
        private DocumentProcessor $processor,
    ) {}

    public function verify(Entity $document, DocumentType $type): ?Verification
    {
        $data = $document->get('vtigerData');

        if (!$data instanceof stdClass || !property_exists($data, 'region_id')) {
            return null;
        }

        $regionId = $data->region_id === null ? null : (int) $data->region_id;
        $lines = [];

        foreach ($this->items($document, $type) as $item) {
            $extra = $item->get('vtigerData');
            $extra = $extra instanceof stdClass ? $extra : (object) [];

            $lines[] = Line::fromSource(
                $item->get('quantity'),
                $item->get('unitPrice'),
                $item->get('discountAmount'),
                $item->get('discountPercent'),
                $item->get('taxRate'),
                self::decimalOrNull($extra->tax2 ?? null),
                self::decimalOrNull($extra->tax3 ?? null),
                $item->get('purchaseCost'),
                $item->get('margin'),
            );
        }

        $header = $this->processor->header($document);
        $source = SourceDocument::of(
            Document::of(
                $header->taxMode,
                $lines,
                $header->value('discountAmount'),
                $header->value('discountPercent'),
                $header->value('shippingAmount'),
                $header->value('shippingTaxPercent'),
                $header->value('adjustment'),
            ),
            $regionId,
            $document->get('subtotal'),
            $document->get('preTaxTotal'),
            $document->get('grandTotal'),
        );

        return (new SourceVerifier())->verify($source);
    }

    public static function totalsCheck(Verification $verification): string
    {
        return $verification->worstCheck()?->value ?? 'unverified';
    }

    /**
     * @return iterable<Entity>
     */
    private function items(Entity $document, DocumentType $type): iterable
    {
        return $this->entityManager
            ->getRDBRepository($type->itemEntityType)
            ->where([$type->parentLink . 'Id' => $document->getId()])
            ->order('order')
            ->find();
    }

    private static function decimalOrNull(mixed $value): ?Decimal
    {
        return $value === null || $value === '' ? null : Decimal::of(is_int($value) ? $value : (string) $value);
    }
}
