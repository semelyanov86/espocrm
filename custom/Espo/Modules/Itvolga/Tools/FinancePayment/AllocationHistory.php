<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\FinancePayment;

use Espo\Entities\Note;
use Espo\ORM\Entity;
use Espo\ORM\EntityManager;
use stdClass;

/**
 * Changes of a payment's allocation table that are not an update of the payment itself: the rows given when the
 * payment is created, a row removed together with its document. They are written as the core writes audited fields
 * (an Update note of the payment with the table before and after), so the stream shows one format for every change.
 * Updates of the payment get their note from the core (`allocationList` is audited).
 */
class AllocationHistory
{
    public function __construct(private EntityManager $entityManager) {}

    /**
     * @param list<stdClass> $was canonical table before
     * @param list<stdClass> $became canonical table after
     */
    public function record(Entity $payment, array $was, array $became): void
    {
        $note = $this->entityManager->getRDBRepositoryByClass(Note::class)->getNew();

        $note
            ->setType(Note::TYPE_UPDATE)
            ->setParent($payment)
            ->setData([
                Note::DATA_ATTR_FIELDS => [PaymentProcessor::ALLOCATION_LIST],
                Note::DATA_ATTR_ATTRIBUTES => [
                    'was' => (object) [PaymentProcessor::ALLOCATION_LIST => $was],
                    'became' => (object) [PaymentProcessor::ALLOCATION_LIST => $became],
                ],
            ]);

        $this->entityManager->saveEntity($note);
    }
}
