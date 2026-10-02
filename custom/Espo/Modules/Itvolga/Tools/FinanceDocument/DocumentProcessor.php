<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\FinanceDocument;

use Espo\Core\Exceptions\BadRequest;
use Espo\Core\Exceptions\Error;
use Espo\Core\ORM\Repository\Option\SaveOption;
use Espo\Core\Utils\Config;
use Espo\Modules\Itvolga\Tools\Finance\Decimal;
use Espo\Modules\Itvolga\Tools\Finance\Editing\DocumentEditor;
use Espo\Modules\Itvolga\Tools\Finance\Editing\EditPlan;
use Espo\Modules\Itvolga\Tools\Finance\Editing\HeaderInputs;
use Espo\Modules\Itvolga\Tools\Finance\Editing\LineInput;
use Espo\Modules\Itvolga\Tools\Finance\Editing\StoredDocument;
use Espo\Modules\Itvolga\Tools\Finance\Exceptions\InvalidValue;
use Espo\Modules\Itvolga\Tools\Finance\Exceptions\RuleNotSupported;
use Espo\Modules\Itvolga\Tools\Finance\Scale;
use Espo\ORM\Entity;
use Espo\ORM\EntityManager;
use Espo\ORM\Repository\Option\SaveOptions;
use stdClass;

/**
 * Save path of finance documents with line items (Quote, SalesOrder; registry app.itvolgaFinance).
 *
 * The document and its items are saved by one request: `itemList` (a non-stored list of line objects) carries the
 * complete item table. prepare() runs in the document's beforeSave inside its transaction (entityDefs
 * transactionalSave): it validates the lines, applies the edit rule (DocumentEditor), sets the totals and the number;
 * persist() runs in afterSave of the same transaction and writes the items. Any refusal rolls back the header, the
 * items and the number counter together. Items are written only here (WRITE_OPTION; other writes are refused by
 * Hooks/Common/FinanceItemGuard) and by the importer (SaveOption::IMPORT, values as in the source).
 */
class DocumentProcessor
{
    public const WRITE_OPTION = 'itvolgaFinanceWrite';
    public const ITEM_LIST = 'itemList';
    public const SOURCE_TOTALS = 'sourceTotals';

    private const HEADER_INPUTS = ['taxMode', ...HeaderInputs::DECIMALS];
    private const TOTALS = ['subtotal', 'preTaxTotal', 'grandTotal'];
    private const HEADER_MONEY = ['discountAmount', 'shippingAmount', 'adjustment', 'subtotal', 'preTaxTotal',
        'grandTotal'];
    private const ITEM_MONEY = ['unitPrice', 'discountAmount', 'purchaseCost', 'amount', 'margin'];
    private const ITEM_OUTPUT = ['description', ...LineInput::DECIMALS, 'amount', 'margin'];

    private DocumentEditor $editor;

    public function __construct(
        private EntityManager $entityManager,
        private Config $config,
        private NumberAllocator $numberAllocator,
        private LegalEntityProvider $legalEntityProvider,
        private ErrorMapper $errorMapper,
    ) {
        $this->editor = new DocumentEditor();
    }

    /**
     * @throws BadRequest refused input (translated message with line and field)
     * @throws Error configuration missing (legal entity, numbering)
     */
    public function prepare(Entity $document, DocumentType $type, SaveOptions $options): ?SavePlan
    {
        $this->setLegalEntity($document);

        if ($options->get(SaveOption::IMPORT)) {
            // The importer keeps number, totals and items as in the source (D-05, D-17); SourceVerification classifies.
            return null;
        }

        $isNew = $document->isNew();
        $itemListGiven = $document->has(self::ITEM_LIST) && ($isNew || $document->isAttributeChanged(self::ITEM_LIST));

        if (!$isNew && !$itemListGiven && !$this->headerChanged($document)) {
            return null;
        }

        $stored = null;
        $current = null;
        $items = [];

        if (!$isNew) {
            // Serialises concurrent saves of the document; its stored state is read under the lock.
            $current = $this->entityManager
                ->getRDBRepository($type->entityType)
                ->where(['id' => $document->getId()])
                ->forUpdate()
                ->findOne() ?? throw new Error("{$type->entityType} {$document->getId()} not found.");
            $items = $this->findItems($document->getId(), $type);
        }

        try {
            if ($current) {
                $stored = new StoredDocument($this->header($current), $this->storedLines($items),
                    $this->hasSourceTotals($current));
                $this->rebaseOnLockedRow($document, $current);
            }

            $lines = $itemListGiven ? $this->parseItemList($document->get(self::ITEM_LIST)) : null;
            $plan = $this->editor->plan($stored, $this->header($document), $lines);
            $productNames = $this->productNames($plan, $items);
        } catch (InvalidValue|RuleNotSupported $e) {
            throw $this->errorMapper->toBadRequest($e, $type);
        }

        if ($plan->recalculated) {
            $this->applyTotals($document, $plan, $current, $items);
        }

        $this->setCurrency($document, self::HEADER_MONEY);

        if ($isNew) {
            $document->set('number', $this->numberAllocator->allocate($type));
        }

        return new SavePlan($plan, $items, $productNames);
    }

    public function persist(Entity $document, DocumentType $type, SavePlan $plan): void
    {
        $options = [self::WRITE_OPTION => true, SaveOption::SILENT => true];

        foreach ($plan->edit->lines as $planned) {
            $input = $planned->input;
            $item = $input->id !== null
                ? $plan->items[$input->id]
                : $this->entityManager->getRDBRepository($type->itemEntityType)->getNew();

            if ($item->isNew()) {
                $item->set($type->parentLink . 'Id', $document->getId());
            }

            if ($item->isNew() || $item->get('productId') !== $input->productId) {
                $item->set('name', $plan->productNames[$input->productId]);
            }

            $item->set(['order' => $planned->order, 'productId' => $input->productId,
                'description' => $input->description]);

            foreach (LineInput::DECIMALS as $field) {
                $item->set($field, $input->value($field)->toString());
            }

            if ($planned->amount !== null && $planned->margin !== null) {
                $item->set('amount', $planned->amount->toFixed(Scale::MONEY));
                $item->set('margin', $planned->margin->toFixed(Scale::MONEY));
            }

            $this->setCurrency($item, self::ITEM_MONEY);

            if ($item->isNew() || $this->isChanged($item)) {
                $this->entityManager->saveEntity($item, $options);
            }
        }

        foreach ($plan->edit->removedIds as $id) {
            $this->entityManager->removeEntity($plan->items[$id], $options);
        }
    }

    /**
     * The item table of a document for the client and the API (values as stored, decimal strings).
     *
     * @return list<stdClass>
     */
    public function loadItemList(Entity $document, DocumentType $type): array
    {
        $items = $this->findItems((string) $document->getId(), $type);
        $productNames = $this->namesOf(array_map(static fn (Entity $item) => (string) $item->get('productId'), $items));
        $list = [];

        foreach ($items as $item) {
            $row = (object) [
                'id' => $item->getId(),
                'order' => $item->get('order'),
                'productId' => $item->get('productId'),
                'productName' => $productNames[$item->get('productId')] ?? $item->get('name'),
            ];

            foreach (self::ITEM_OUTPUT as $field) {
                $row->$field = $item->get($field);
            }

            $list[] = $row;
        }

        return $list;
    }

    /**
     * Saved state of a document for the editor (without a lock; the save path takes one).
     */
    public function storedDocument(Entity $document, DocumentType $type): StoredDocument
    {
        $items = $this->findItems((string) $document->getId(), $type);

        return new StoredDocument($this->header($document), $this->storedLines($items),
            $this->hasSourceTotals($document));
    }

    public function header(Entity $document): HeaderInputs
    {
        return HeaderInputs::fromArray($this->headerValues($document));
    }

    /**
     * @return array<string, mixed> calculation inputs of the header as stored on the entity
     */
    public function headerValues(Entity $document): array
    {
        $values = [];

        foreach (self::HEADER_INPUTS as $attribute) {
            $values[$attribute] = $document->get($attribute);
        }

        return $values;
    }

    /**
     * @return list<LineInput>
     */
    public function parseItemList(mixed $value): array
    {
        if (!is_array($value)) {
            throw new InvalidValue('itemList must be a list of lines.', 'badItemList');
        }

        $lines = [];

        foreach (array_values($value) as $index => $row) {
            if (!is_array($row) && !$row instanceof stdClass) {
                throw new InvalidValue('Line ' . ($index + 1) . ': not an object.', 'badLine', $index + 1);
            }

            $lines[] = LineInput::fromArray((array) $row, $index + 1);
        }

        return $lines;
    }

    /**
     * The stored totals are still the source system's: never recalculated in EspoCRM (no vtigerData.sourceTotals —
     * once there, the document stays calculated whatever marks are written later) and imported (sourceFormula set by
     * SourceVerification, or an imported record not verified yet).
     */
    public function hasSourceTotals(Entity $document): bool
    {
        $data = $document->get('vtigerData');

        if ($data instanceof stdClass && isset($data->{self::SOURCE_TOTALS})) {
            return false;
        }

        return (string) $document->get('sourceFormula') !== '' || $document->get('vtigerId') !== null;
    }

    /**
     * The entity was loaded before the lock, and the ORM writes only attributes that differ from the fetched values.
     * Calculation inputs, totals and source marks are brought to the locked row: unchanged ones take the row's values
     * (calculation and the response see what another save committed in between), changed ones keep this save's
     * values and are compared with the row, so exactly the differences from what is stored are written.
     */
    private function rebaseOnLockedRow(Entity $document, Entity $current): void
    {
        foreach ([...self::HEADER_INPUTS, ...self::TOTALS, 'sourceFormula', 'totalsCheck'] as $attribute) {
            $value = $current->get($attribute);

            if (!$document->isAttributeChanged($attribute)) {
                $document->set($attribute, $value);
            }

            $document->setFetched($attribute, $value);
        }
    }

    private function headerChanged(Entity $document): bool
    {
        foreach (self::HEADER_INPUTS as $attribute) {
            if ($document->isAttributeChanged($attribute)) {
                return true;
            }
        }

        return false;
    }

    /**
     * @param array<string, Entity> $items
     * @return list<LineInput>
     */
    private function storedLines(array $items): array
    {
        $lines = [];

        foreach (array_values($items) as $index => $item) {
            $raw = ['id' => $item->getId(), 'productId' => $item->get('productId'),
                'description' => $item->get('description')];

            foreach (LineInput::DECIMALS as $field) {
                $raw[$field] = $item->get($field);
            }

            $lines[] = LineInput::fromArray($raw, $index + 1);
        }

        return $lines;
    }

    /**
     * @return array<string, Entity> by id, in line order
     */
    private function findItems(string $documentId, DocumentType $type): array
    {
        $collection = $this->entityManager
            ->getRDBRepository($type->itemEntityType)
            ->where([$type->parentLink . 'Id' => $documentId])
            ->order('order')
            ->order('createdAt')
            ->find();

        $items = [];

        foreach ($collection as $item) {
            $items[$item->getId()] = $item;
        }

        return $items;
    }

    /**
     * Names of the products of new lines and of lines whose product changed; a missing product is refused.
     *
     * @param array<string, Entity> $items
     * @return array<string, string>
     */
    private function productNames(EditPlan $plan, array $items): array
    {
        $needed = [];

        foreach ($plan->lines as $planned) {
            $id = $planned->input->id;

            if ($id === null || $items[$id]->get('productId') !== $planned->input->productId) {
                $needed[$planned->order] = $planned->input->productId;
            }
        }

        $names = $this->namesOf(array_values($needed));

        foreach ($needed as $line => $productId) {
            if (!isset($names[$productId])) {
                throw new InvalidValue("Line $line: product not found.", 'unknownProduct', $line, 'product');
            }
        }

        return $names;
    }

    /**
     * @param list<string> $productIds
     * @return array<string, string>
     */
    private function namesOf(array $productIds): array
    {
        $productIds = array_values(array_unique(array_filter($productIds)));

        if ($productIds === []) {
            return [];
        }

        $names = [];
        $products = $this->entityManager
            ->getRDBRepository('Product')
            ->select(['id', 'name'])
            ->where(['id' => $productIds])
            ->find();

        foreach ($products as $product) {
            $names[$product->getId()] = (string) $product->get('name');
        }

        return $names;
    }

    /**
     * @param array<string, Entity> $items
     */
    private function applyTotals(Entity $document, EditPlan $plan, ?Entity $current, array $items): void
    {
        $totals = $plan->totals;

        if (!$totals) {
            return;
        }

        if ($plan->replacesSourceTotals && $current) {
            // Owner decision 2026-10-01: the source totals are kept once — never replaced — then the document is
            // calculated in EspoCRM. Compared with the locked row, so a stale loaded copy is never written.
            $data = $current->get('vtigerData');
            $document->setFetched('vtigerData', $data);
            $data = $data instanceof stdClass ? clone $data : (object) [];

            if (!isset($data->{self::SOURCE_TOTALS})) {
                $data->{self::SOURCE_TOTALS} = $this->sourceSnapshot($current, $items);
                $document->set('vtigerData', $data);
            }
        }

        $document->set([
            'subtotal' => $totals->subtotal->toFixed(Scale::MONEY),
            'preTaxTotal' => $totals->preTaxTotal->toFixed(Scale::MONEY),
            'grandTotal' => $totals->grandTotal->toFixed(Scale::MONEY),
            'sourceFormula' => '',
            'totalsCheck' => '',
        ]);
    }

    /**
     * @param array<string, Entity> $items
     * @return array<string, mixed>
     */
    private function sourceSnapshot(Entity $current, array $items): array
    {
        $snapshot = [];

        foreach ([...self::TOTALS, ...self::HEADER_INPUTS, 'sourceFormula', 'totalsCheck'] as $attribute) {
            $snapshot[$attribute] = $current->get($attribute);
        }

        $snapshot['lines'] = [];

        foreach ($items as $item) {
            $line = ['id' => $item->getId(), 'vtigerId' => $item->get('vtigerId'), 'order' => $item->get('order')];

            foreach ([...LineInput::DECIMALS, 'amount', 'margin'] as $field) {
                $line[$field] = $item->get($field);
            }

            $snapshot['lines'][] = $line;
        }

        $snapshot['recalculatedAt'] = gmdate('Y-m-d H:i:s');

        return $snapshot;
    }

    private function setLegalEntity(Entity $document): void
    {
        if (
            !$document->isNew() &&
            $document->get('legalEntityId') &&
            !$document->isAttributeChanged('legalEntityId')
        ) {
            return;
        }

        $id = $this->legalEntityProvider->findDefaultId()
            ?? throw new Error('The legal entity is not configured: run itvolga-setup-finance.');

        if ($document->get('legalEntityId') !== $id) {
            // One legal entity (D-04, D-48): every document belongs to it.
            $document->set('legalEntityId', $id);
        }
    }

    /**
     * @param list<string> $attributes
     */
    private function setCurrency(Entity $entity, array $attributes): void
    {
        $currency = (string) $this->config->get('defaultCurrency');

        foreach ($attributes as $attribute) {
            if ($entity->get($attribute . 'Currency') !== $currency) {
                $entity->set($attribute . 'Currency', $currency);
            }
        }
    }

    private function isChanged(Entity $item): bool
    {
        $attributes = ['name', 'order', 'productId', 'description', ...LineInput::DECIMALS, 'amount', 'margin'];

        foreach ($attributes as $attribute) {
            if ($item->isAttributeChanged($attribute)) {
                return true;
            }
        }

        return false;
    }
}
