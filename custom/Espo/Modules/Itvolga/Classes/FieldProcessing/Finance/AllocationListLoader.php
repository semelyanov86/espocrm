<?php

namespace Espo\Modules\Itvolga\Classes\FieldProcessing\Finance;

use Espo\Core\FieldProcessing\Loader;
use Espo\Core\FieldProcessing\Loader\Params;
use Espo\Core\Utils\Config;
use Espo\Modules\Itvolga\Tools\FinanceDocument\DocumentTypes;
use Espo\Modules\Itvolga\Tools\FinancePayment\PaymentProcessor;
use Espo\ORM\Entity;

/**
 * Fills the non-stored allocation table of a payment and its allocated / unallocated sums on read (and before an
 * update, so that an unchanged table is not taken for an edit: the loaded values are also the fetched ones). The
 * unallocated rest is derived, never stored: a document removal frees it without writing the payment.
 *
 * @implements Loader<Entity>
 */
class AllocationListLoader implements Loader
{
    private const SUMS = ['allocatedAmount', 'unallocatedAmount'];

    public function __construct(
        private DocumentTypes $types,
        private PaymentProcessor $processor,
        private Config $config,
    ) {}

    public function process(Entity $entity, Params $params): void
    {
        $type = $this->types->findPayment($entity->getEntityType());

        if (!$type) {
            return;
        }

        $wanted = [PaymentProcessor::ALLOCATION_LIST, ...self::SUMS];

        if ($params->hasSelect() && !array_filter($wanted, static fn ($field) => $params->hasInSelect($field))) {
            return;
        }

        [$list, $allocated, $unallocated] = $this->processor->loadTable($entity, $type);
        $currency = (string) $this->config->get('defaultCurrency');
        $values = [
            PaymentProcessor::ALLOCATION_LIST => $list,
            'allocatedAmount' => $allocated->toString(),
            'unallocatedAmount' => $unallocated->toString(),
            'allocatedAmountCurrency' => $currency,
            'unallocatedAmountCurrency' => $currency,
        ];

        foreach ($values as $attribute => $value) {
            $entity->set($attribute, $value);
            $entity->setFetched($attribute, $value);
        }
    }
}
