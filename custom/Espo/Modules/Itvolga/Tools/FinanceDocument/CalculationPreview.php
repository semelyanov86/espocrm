<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\FinanceDocument;

use Espo\Core\Acl;
use Espo\Core\Acl\Table;
use Espo\Core\Exceptions\Forbidden;
use Espo\Core\Exceptions\NotFound;
use Espo\Modules\Itvolga\Tools\Finance\Editing\DocumentEditor;
use Espo\Modules\Itvolga\Tools\Finance\Editing\HeaderInputs;
use Espo\Modules\Itvolga\Tools\Finance\Exceptions\InvalidValue;
use Espo\Modules\Itvolga\Tools\Finance\Exceptions\RuleNotSupported;
use Espo\Modules\Itvolga\Tools\Finance\Scale;
use Espo\Modules\Itvolga\Tools\FinancePayment\PaymentPreview;
use Espo\ORM\EntityManager;
use stdClass;

/**
 * Totals of the form as the server would save them (live totals of the item editor): the same edit rule and
 * calculation as a save, nothing is written. The browser does no arithmetic with money. For a payment: the allocated
 * sum and the rest of its table (PaymentPreview, stage 04.4).
 */
class CalculationPreview
{
    private const HEADER_ATTRIBUTES = ['taxMode', 'discountAmount', 'discountPercent', 'shippingAmount',
        'shippingTaxPercent', 'adjustment'];

    public function __construct(
        private EntityManager $entityManager,
        private Acl $acl,
        private DocumentTypes $types,
        private DocumentProcessor $processor,
        private ErrorMapper $errorMapper,
        private PaymentPreview $paymentPreview,
    ) {}

    /**
     * @throws Forbidden
     * @throws NotFound
     */
    public function preview(string $entityType, ?string $id, stdClass $attributes): stdClass
    {
        if ($paymentType = $this->types->findPayment($entityType)) {
            return $this->paymentPreview->preview($paymentType, $id, $attributes);
        }

        $type = $this->types->find($entityType) ?? throw new NotFound();
        $stored = null;

        if ($id !== null) {
            $document = $this->entityManager->getEntityById($entityType, $id) ?? throw new NotFound();

            if (!$this->acl->checkEntity($document, Table::ACTION_EDIT)) {
                throw new Forbidden();
            }
        } else {
            if (!$this->acl->checkScope($entityType, Table::ACTION_CREATE)) {
                throw new Forbidden();
            }

            $document = $this->entityManager->getNewEntity($entityType);
        }

        try {
            if ($id !== null) {
                $stored = $this->processor->storedDocument($document, $type);
            }

            // Raw values of the form: a float or a malformed number is refused here as on save (no entity coercion).
            $values = $this->processor->headerValues($document);

            foreach (self::HEADER_ATTRIBUTES as $attribute) {
                if (property_exists($attributes, $attribute)) {
                    $values[$attribute] = $attributes->$attribute;
                }
            }

            $header = HeaderInputs::fromArray($values);
            $lines = property_exists($attributes, DocumentProcessor::ITEM_LIST)
                ? $this->processor->parseItemList($attributes->{DocumentProcessor::ITEM_LIST})
                : null;

            $plan = (new DocumentEditor())->plan($stored, $header, $id === null ? ($lines ?? []) : $lines);
        } catch (InvalidValue|RuleNotSupported $e) {
            return (object) [
                'error' => (object) [
                    'message' => $this->errorMapper->message($e, $type),
                    'line' => $e->documentLine,
                    'field' => $e->field,
                ],
            ];
        }

        if (!$plan->recalculated || !$plan->totals) {
            return (object) ['recalculated' => false];
        }

        $totals = $plan->totals;
        $money = static fn ($value) => $value->toFixed(Scale::MONEY);

        return (object) [
            'recalculated' => true,
            'replacesSourceTotals' => $plan->replacesSourceTotals,
            'subtotal' => $money($totals->subtotal),
            'discountAmount' => $money($totals->discountAmount),
            'shippingAmount' => $money($totals->shippingAmount),
            'adjustment' => $money($totals->adjustment),
            'preTaxTotal' => $money($totals->preTaxTotal),
            'grandTotal' => $money($totals->grandTotal),
            'lines' => array_map(static fn ($line) => (object) [
                'amount' => $line->amount ? $money($line->amount) : null,
                'margin' => $line->margin ? $money($line->margin) : null,
            ], $plan->lines),
        ];
    }
}
