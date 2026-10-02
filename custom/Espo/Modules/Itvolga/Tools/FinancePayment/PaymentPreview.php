<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\FinancePayment;

use Espo\Core\Acl;
use Espo\Core\Acl\Table;
use Espo\Core\Exceptions\Forbidden;
use Espo\Core\Exceptions\NotFound;
use Espo\Modules\Itvolga\Tools\Finance\Exceptions\InvalidValue;
use Espo\Modules\Itvolga\Tools\Finance\Exceptions\RuleNotSupported;
use Espo\Modules\Itvolga\Tools\Finance\Payment\AllocationEditor;
use Espo\Modules\Itvolga\Tools\Finance\Payment\Direction;
use Espo\Modules\Itvolga\Tools\FinanceDocument\ErrorMapper;
use Espo\Modules\Itvolga\Tools\FinanceDocument\PaymentType;
use Espo\ORM\Entity;
use Espo\ORM\EntityManager;
use stdClass;

/**
 * Allocated sum and the rest of an unsaved payment form (POST /FinanceDocument/Payment/calculate): the same edit rule
 * as a save (AllocationEditor), nothing is locked or written. The browser does no arithmetic with money. Documents
 * are checked by the save (existence and access), the preview does not reveal them.
 */
class PaymentPreview
{
    private const INPUTS = ['amount', 'direction'];

    public function __construct(
        private EntityManager $entityManager,
        private Acl $acl,
        private PaymentProcessor $processor,
        private AllocationRows $rows,
        private ErrorMapper $errorMapper,
    ) {}

    /**
     * @throws Forbidden
     * @throws NotFound
     */
    public function preview(PaymentType $type, ?string $id, stdClass $attributes): stdClass
    {
        $payment = $id !== null ? $this->stored($type, $id) : null;

        if (!$payment && !$this->acl->checkScope($type->entityType, Table::ACTION_CREATE)) {
            throw new Forbidden();
        }

        $values = [];

        foreach (self::INPUTS as $attribute) {
            $values[$attribute] = property_exists($attributes, $attribute)
                ? $attributes->$attribute
                : ($payment?->get($attribute) ?? ($attribute === 'direction' ? Direction::Incoming->value : null));
        }

        $stored = $payment
            ? array_values(array_map(fn (Entity $row) => $this->rows->toInput($row, $type),
                $this->rows->find($payment->getId(), $type)))
            : [];

        try {
            $direction = Direction::tryFrom((string) $values['direction'])
                ?? throw new InvalidValue('Unknown direction.', 'notInOptions', null, 'direction');
            $input = property_exists($attributes, PaymentProcessor::ALLOCATION_LIST)
                ? $this->processor->parseAllocationList($attributes->{PaymentProcessor::ALLOCATION_LIST}, $type)
                : null;
            $plan = (new AllocationEditor())->plan($values['amount'], $direction, $stored, $input, $payment === null);
        } catch (InvalidValue|RuleNotSupported $e) {
            return (object) [
                'error' => (object) [
                    'message' => $this->errorMapper->messageIn($e, $type->entityType, $type->allocationEntityType),
                    'line' => $e->documentLine,
                    'field' => $e->field,
                ],
            ];
        }

        return (object) [
            'allocatedAmount' => $plan->allocated->toString(),
            'unallocatedAmount' => $plan->remainder->toString(),
        ];
    }

    /**
     * @throws Forbidden
     * @throws NotFound
     */
    private function stored(PaymentType $type, string $id): Entity
    {
        $payment = $this->entityManager->getEntityById($type->entityType, $id) ?? throw new NotFound();

        if (!$this->acl->checkEntity($payment, Table::ACTION_EDIT)) {
            throw new Forbidden();
        }

        return $payment;
    }
}
