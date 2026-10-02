<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\FinancePayment;

use Espo\Core\Acl;
use Espo\Core\Acl\Table;
use Espo\Core\Exceptions\Forbidden;
use Espo\Core\Exceptions\NotFound;
use Espo\Core\Utils\Config;
use Espo\Entities\User;
use Espo\Modules\Itvolga\Tools\Finance\Decimal;
use Espo\Modules\Itvolga\Tools\Finance\Payment\AllocationInput;
use Espo\Modules\Itvolga\Tools\Finance\Scale;
use Espo\Modules\Itvolga\Tools\FinanceDocument\PaymentType;
use Espo\ORM\EntityManager;
use stdClass;

/**
 * «Добавить платёж» on an invoice or a sales order, as in Vtiger (SPPayments Edit view; owner decision 2026-10-02):
 * the payer is the document's account, the amount is the document's total (two decimals), the table has one row
 * for the whole amount to this document, and the payment is assigned to the current user (the default of the Vtiger
 * field and of a new EspoCRM record; a prefilled form gets no client defaults). Nothing is saved and no number is taken until the user saves the form;
 * partial payments are entered by changing the amount. A document without a positive total gets no row (an
 * allocation is always positive, D-49).
 */
class PaymentPrefill
{
    public function __construct(
        private EntityManager $entityManager,
        private Acl $acl,
        private Config $config,
        private AllocationRows $rows,
        private User $user,
    ) {}

    /**
     * @throws Forbidden
     * @throws NotFound
     */
    public function attributes(string $from, string $id, PaymentType $type): stdClass
    {
        $link = $type->linkOf($from) ?? throw new NotFound();
        $document = $this->entityManager->getEntityById($from, $id) ?? throw new NotFound();

        if (
            !$this->acl->checkEntity($document, Table::ACTION_READ) ||
            !$this->acl->checkScope($type->entityType, Table::ACTION_CREATE)
        ) {
            throw new Forbidden();
        }

        $amount = Decimal::ofNullable($document->get('grandTotal'))->round(Scale::MONEY);
        $attributes = (object) [
            'amount' => $amount->toFixed(Scale::MONEY),
            'amountCurrency' => (string) $this->config->get('defaultCurrency'),
            PaymentProcessor::ALLOCATION_LIST => [],
            'assignedUserId' => $this->user->getId(),
            'assignedUserName' => $this->user->getName(),
        ];

        if ($document->get('accountId')) {
            $attributes->payerType = 'Account';
            $attributes->payerId = $document->get('accountId');
            $attributes->payerName = $document->get('accountName');
        }

        if ($amount->isPositive()) {
            $row = new AllocationInput(null, $from, $id, $amount);
            $attributes->{PaymentProcessor::ALLOCATION_LIST} = [
                $this->rows->present($row, null, 1, $type, [$row->targetKey() => $document]),
            ];
        }

        $forbidden = $this->acl->getScopeForbiddenAttributeList($type->entityType, Table::ACTION_EDIT);

        foreach ($forbidden as $attribute) {
            unset($attributes->$attribute);
        }

        return $attributes;
    }
}
