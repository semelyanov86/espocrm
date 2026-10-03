<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\FinancePrint;

use Espo\Core\Acl;
use Espo\Core\Exceptions\Forbidden;
use Espo\Core\Utils\Config;
use Espo\Core\Utils\Language\LanguageFactory;
use Espo\Modules\Itvolga\Tools\Finance\Printing\Formatter;
use Espo\Modules\Itvolga\Tools\FinanceDocument\DocumentProcessor;
use Espo\Modules\Itvolga\Tools\FinanceDocument\DocumentType;
use Espo\Modules\Itvolga\Tools\FinanceDocument\LegalEntityProvider;
use Espo\ORM\Entity;
use Espo\ORM\EntityManager;
use Espo\ORM\Type\AttributeType;

/**
 * Stored values a print form shows (stage 05), read without any write: the record, its lines with the units of their
 * products, the seller (the record's legal entity), the buyer (the account, the payer) and, on a quote, its manager.
 * Every value goes through the user's access like the record view: a related record the form prints must be readable,
 * a field the user may not read prints empty (a forbidden link — its whole block), and a forbidden amount refuses the
 * print (a form without its sums would mislead).
 * Values stay as stored (decimal strings); Presenter formats them.
 */
class PrintData
{
    private const LANGUAGE = 'ru_RU';
    private const SELLER = ['name', 'inn', 'kpp', 'okpo', 'bankAccount', 'bankName', 'bic', 'corrAccount', 'director',
        'bookkeeper', 'phoneNumber', 'website', 'addressPostalCode', 'addressState', 'addressCity', 'addressStreet',
        'logoId'];
    private const BUYER = ['name', 'cInn', 'cKpp', 'phoneNumber', 'billingAddressPostalCode', 'billingAddressState',
        'billingAddressCity', 'billingAddressStreet'];
    private const TOTALS = ['subtotal', 'shippingAmount', 'preTaxTotal', 'adjustment', 'grandTotal'];
    private const DOCUMENT = ['number', 'name', 'accountId', 'accountName', 'legalEntityId', 'contactName',
        'assignedUserId', 'assignedUserName', 'termsAndConditions', 'billingAddressPostalCode', 'billingAddressState',
        'billingAddressCity', 'billingAddressStreet'];
    private const LINE_AMOUNTS = ['quantity', 'unitPrice', 'discountAmount', 'discountPercent', 'amount'];
    /** Attributes of the printed line name: the product link and the saved name (loadItemList falls back to it). */
    private const LINE_NAMES = ['productName', 'name'];

    public function __construct(
        private EntityManager $entityManager,
        private Acl $acl,
        private DocumentProcessor $documentProcessor,
        private LegalEntityProvider $legalEntityProvider,
        private LanguageFactory $languageFactory,
        private Config $config,
    ) {}

    /**
     * Quote, SalesOrder, Invoice, Act.
     *
     * @return array<string, mixed> input of Presenter::document()
     * @throws Forbidden the account or the legal entity is not readable; an amount of the document is forbidden
     */
    public function document(Entity $document, DocumentType $type, PrintForm $form): array
    {
        $dates = array_filter([$form->dateField, $form->extraDateField]);
        $values = $this->values($document, [...self::DOCUMENT, ...self::TOTALS, ...$dates], self::TOTALS);
        $account = $this->readable('Account', $values['accountId']);
        $buyer = $account ? $this->values($account, self::BUYER) : [];

        return [
            'number' => $values['number'],
            'subject' => $values['name'],
            'date' => $this->date($document, $form->dateField, $values),
            'extraDate' => $form->extraDateField ? $this->date($document, $form->extraDateField, $values) : null,
            'seller' => $this->seller($document, $values['legalEntityId']),
            'buyer' => [
                'name' => $buyer['name'] ?? $values['accountName'],
                'inn' => $buyer['cInn'] ?? null,
                'kpp' => $buyer['cKpp'] ?? null,
                'phone' => $buyer['phoneNumber'] ?? null,
                'documentAddress' => $this->address($values),
                'accountAddress' => $this->address($buyer),
            ],
            'lines' => $this->lines($document, $type),
            'totals' => array_intersect_key($values, array_flip(self::TOTALS)),
            'terms' => $document->hasAttribute('termsAndConditions') ? $values['termsAndConditions'] : null,
            'contact' => $values['contactName'],
            'manager' => $this->manager($values['assignedUserId'], $values['assignedUserName']),
        ];
    }

    /**
     * Cash receipt order of a payment.
     *
     * @return array<string, mixed> input of Presenter::cashReceipt()
     * @throws Forbidden the payer or the legal entity is not readable; the amount is forbidden
     */
    public function payment(Entity $payment, PrintForm $form): array
    {
        $values = $this->values($payment, ['number', 'documentNumber', 'amount', 'payerId', 'payerType', 'purpose',
            'legalEntityId', $form->dateField], ['amount']);
        $payer = $values['payerType'] ? $this->readable($values['payerType'], $values['payerId']) : null;

        return [
            'number' => $values['number'],
            'documentNumber' => $values['documentNumber'],
            'date' => $this->date($payment, $form->dateField, $values),
            'amount' => $values['amount'],
            'payer' => $payer ? $this->values($payer, ['name'])['name'] : null,
            'purpose' => $values['purpose'],
            'seller' => $this->seller($payment, $values['legalEntityId']),
        ];
    }

    /**
     * @return list<array<string, ?string>>
     * @throws Forbidden an amount of the lines is forbidden
     */
    private function lines(Entity $document, DocumentType $type): array
    {
        $forbidden = $this->acl->getScopeForbiddenAttributeList($type->itemEntityType);
        $documentForbidden = $this->acl->getScopeForbiddenAttributeList($document->getEntityType());

        if (in_array(DocumentProcessor::ITEM_LIST, $documentForbidden, true) || array_intersect(self::LINE_AMOUNTS, $forbidden) !== []) {
            throw new Forbidden("No read access to the lines of the $type->entityType.");
        }

        $items = $this->documentProcessor->loadItemList($document, $type);
        $units = $this->units(array_map(static fn ($item) => (string) $item->productId, $items));
        $lines = [];

        foreach ($items as $item) {
            $line = ['unit' => $units[$item->productId] ?? null];

            foreach ([...self::LINE_AMOUNTS, 'description'] as $field) {
                $line[$field] = in_array($field, $forbidden, true) ? null : $item->$field;
            }

            // The printed name is the product's or, without a product, the line's saved name: both must be readable.
            $line['name'] = array_intersect(self::LINE_NAMES, $forbidden) === [] ? $item->productName : null;
            $lines[] = $line;
        }

        return $lines;
    }

    /**
     * Russian labels of the units of the products (SalesPlatform printed the translated usage unit).
     *
     * @param list<string> $productIds
     * @return array<string, string> by product id; products without a readable unit are absent
     */
    private function units(array $productIds): array
    {
        $productIds = array_values(array_unique(array_filter($productIds)));

        if ($productIds === [] || in_array('unit', $this->acl->getScopeForbiddenAttributeList('Product'), true)) {
            return [];
        }

        $language = $this->languageFactory->create(self::LANGUAGE);
        $products = $this->entityManager
            ->getRDBRepository('Product')
            ->select(['id', 'unit'])
            ->where(['id' => $productIds])
            ->find();
        $units = [];

        foreach ($products as $product) {
            $unit = (string) $product->get('unit');

            if ($unit !== '') {
                $units[$product->getId()] = $language->translateOption($unit, 'unit', 'Product');
            }
        }

        return $units;
    }

    /**
     * The legal entity of the record; a record without one (payments of the bank import) — the single legal entity,
     * unless the user may not read the record's legal entity field.
     *
     * @return array<string, mixed>
     * @throws Forbidden
     */
    private function seller(Entity $record, ?string $legalEntityId): array
    {
        if ($legalEntityId === null && in_array('legalEntityId',
                $this->acl->getScopeForbiddenAttributeList($record->getEntityType()), true)) {
            return [];
        }

        $legalEntity = $this->readable(LegalEntityProvider::ENTITY_TYPE,
            $legalEntityId ?? $this->legalEntityProvider->findDefaultId());

        return $legalEntity ? $this->values($legalEntity, self::SELLER) : [];
    }

    /**
     * The manager of a quote: the name as the record shows it; e-mail and phone only of a user the reader may see.
     *
     * @return ?array<string, ?string>
     */
    private function manager(?string $userId, ?string $userName): ?array
    {
        $user = $userId ? $this->entityManager->getEntityById('User', $userId) : null;

        if (!$user || !$this->acl->checkEntityRead($user)) {
            return $userName ? ['name' => $userName] : null;
        }

        $values = $this->values($user, ['name', 'emailAddress', 'phoneNumber']);

        return ['name' => $values['name'] ?? $userName, 'email' => $values['emailAddress'],
            'phone' => $values['phoneNumber']];
    }

    /**
     * A related record the form prints; a missing one is skipped, an unreadable one refuses the print.
     *
     * @throws Forbidden
     */
    private function readable(string $entityType, ?string $id): ?Entity
    {
        $entity = $id ? $this->entityManager->getEntityById($entityType, $id) : null;

        if ($entity && !$this->acl->checkEntityRead($entity)) {
            throw new Forbidden("No read access to the $entityType of the printed record.");
        }

        return $entity;
    }

    /**
     * Attribute values the user may read (a forbidden one is null); a forbidden required attribute refuses the print.
     *
     * @param list<string> $attributes
     * @param list<string> $required
     * @return array<string, mixed>
     * @throws Forbidden
     */
    private function values(Entity $entity, array $attributes, array $required = []): array
    {
        $forbidden = $this->acl->getScopeForbiddenAttributeList($entity->getEntityType());
        $values = [];

        foreach ($attributes as $attribute) {
            if (!in_array($attribute, $forbidden, true)) {
                $values[$attribute] = $entity->get($attribute);

                continue;
            }

            if (in_array($attribute, $required, true)) {
                throw new Forbidden("No read access to a printed field of {$entity->getEntityType()}.");
            }

            $values[$attribute] = null;
        }

        return $values;
    }

    /**
     * @param array<string, mixed> $values billingAddress* attributes of a document or an account
     * @return array<string, ?string> postalCode, state, city, street
     */
    private function address(array $values): array
    {
        return [
            'postalCode' => $values['billingAddressPostalCode'] ?? null,
            'state' => $values['billingAddressState'] ?? null,
            'city' => $values['billingAddressCity'] ?? null,
            'street' => $values['billingAddressStreet'] ?? null,
        ];
    }

    /**
     * Y-m-d of a date field; a date-time field (createdAt) gives its calendar date in the system time zone.
     *
     * @param array<string, mixed> $values readable values of the record
     */
    private function date(Entity $entity, string $field, array $values): ?string
    {
        $value = $values[$field] ?? null;

        if (!$value) {
            return null;
        }

        if ($entity->getAttributeType($field) === AttributeType::DATETIME) {
            return Formatter::localDate($value, $this->config->get('timeZone') ?? 'UTC');
        }

        return $value;
    }
}
