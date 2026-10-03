<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\FinancePayment;

use Espo\Core\Acl;
use Espo\Core\Acl\Table;
use Espo\Core\Exceptions\BadRequest;
use Espo\Core\Exceptions\Error;
use Espo\Core\ORM\Repository\Option\SaveOption;
use Espo\Core\Utils\Config;
use Espo\Core\Utils\Id\RecordIdGenerator;
use Espo\Modules\Itvolga\Tools\Finance\Decimal;
use Espo\Modules\Itvolga\Tools\Finance\Exceptions\InvalidValue;
use Espo\Modules\Itvolga\Tools\Finance\Exceptions\RuleNotSupported;
use Espo\Modules\Itvolga\Tools\Finance\Payment\AllocationEditor;
use Espo\Modules\Itvolga\Tools\Finance\Payment\AllocationInput;
use Espo\Modules\Itvolga\Tools\Finance\Payment\AllocationPlan;
use Espo\Modules\Itvolga\Tools\Finance\Payment\Direction;
use Espo\Modules\Itvolga\Tools\Finance\Scale;
use Espo\Modules\Itvolga\Tools\FinanceDocument\DocumentProcessor;
use Espo\Modules\Itvolga\Tools\FinanceDocument\ErrorMapper;
use Espo\Modules\Itvolga\Tools\FinanceDocument\LegalEntityProvider;
use Espo\Modules\Itvolga\Tools\FinanceDocument\NumberAllocator;
use Espo\Modules\Itvolga\Tools\FinanceDocument\PaymentType;
use Espo\Modules\Itvolga\Tools\FinanceDocument\RowLock;
use Espo\ORM\Entity;
use Espo\ORM\EntityManager;
use Espo\ORM\Repository\Option\RemoveOptions;
use Espo\ORM\Repository\Option\SaveOptions;
use stdClass;

/**
 * Save path of payments (stage 04.4, owner decisions 2026-10-02): the payment and its allocation table are saved by
 * one request — `allocationList`, the complete table, as `itemList` of documents (D-50) — in one transaction.
 *
 * Lock order of every write on the payment side (payment save, payment removal, an imported allocation, a removed
 * document, itvolga-finance-settle): the payment ledger (the NextNumber row of the payment numbering) → the payment
 * row → the documents of its rows, sorted by "EntityType:id" → allocation rows. The ledger serialises the payment side
 * (a handful of payments a day): two payments of one invoice or a payment against a document removal never deadlock,
 * and settlement reads of other payments' rows never wait. A document save (DocumentProcessor) takes only its own row
 * and never reads payments.
 *
 * prepare() runs in beforeSave: locks, rebases the counting inputs on the locked row, plans the table
 * (AllocationEditor), checks the documents, sets the number and the canonical table (audited: the core writes the
 * Update note with the table before and after). persist() runs in afterSave: writes the rows and recalculates the
 * settlement of every affected document. Any refusal rolls back the payment, its rows, the number and the notes.
 */
class PaymentProcessor
{
    public const ALLOCATION_LIST = 'allocationList';
    /** The write option of rows written here (shared with document items: Hooks/Common/FinanceItemGuard). */
    public const WRITE_OPTION = DocumentProcessor::WRITE_OPTION;
    /** Inputs taken from the locked row unless the save changes them. */
    private const COUNTING = ['amount', 'direction', 'status'];
    /** A change of these counts or stops counting every allocation of the payment (D-49). */
    private const SETTLING = ['direction', 'status'];

    private AllocationEditor $editor;

    public function __construct(
        private EntityManager $entityManager,
        private Config $config,
        private Acl $acl,
        private NumberAllocator $numberAllocator,
        private LegalEntityProvider $legalEntityProvider,
        private ErrorMapper $errorMapper,
        private SettlementUpdater $settlement,
        private AllocationRows $rows,
        private AllocationHistory $history,
        private RecordIdGenerator $idGenerator,
        private RowLock $rowLock,
    ) {
        $this->editor = new AllocationEditor();
    }

    /**
     * @throws BadRequest refused input (translated message with the row and the field)
     * @throws Error configuration missing; an imported payment of an unknown legal entity or with a table
     */
    public function prepare(Entity $payment, PaymentType $type, SaveOptions $options): ?PaymentPlan
    {
        $import = (bool) $options->get(SaveOption::IMPORT);
        $this->legalEntityProvider->assign($payment, $import);
        $this->setCurrency($payment);

        $isNew = $payment->isNew();
        $listGiven = $payment->has(self::ALLOCATION_LIST) &&
            ($isNew || $payment->isAttributeChanged(self::ALLOCATION_LIST));

        if ($import && $listGiven && $payment->get(self::ALLOCATION_LIST)) {
            throw new Error("{$type->entityType} vtigerId {$payment->get('vtigerId')}: the importer writes " .
                "{$type->allocationEntityType} records, not the allocation table.");
        }

        $listGiven = $listGiven && !$import;

        if (!$isNew && !$listGiven && !$this->countingChanged($payment)) {
            $this->setName($payment);

            return null;
        }

        if (!$this->numberAllocator->lock($type->series())) {
            throw new Error("Numbering of {$type->entityType} is not configured: run itvolga-setup-finance.");
        }

        $stored = [];

        if (!$isNew) {
            $current = $this->rowLock->one($type->entityType, $payment->getId())
                ?? throw new Error("{$type->entityType} {$payment->getId()} not found.");

            $this->rebaseOnLockedRow($payment, $current);
            $stored = $this->rows->find($payment->getId(), $type, true);
        }

        $settling = !$isNew && $this->settlingChanged($payment);
        $storedInputs = array_values(array_map(fn (Entity $row) => $this->rows->toInput($row, $type), $stored));

        try {
            $direction = Direction::tryFrom((string) $payment->get('direction'))
                ?? throw new InvalidValue('Unknown direction.', 'notInOptions', null, 'direction');
            $input = $listGiven ? $this->parseAllocationList($payment->get(self::ALLOCATION_LIST), $type) : null;
            $plan = $this->editor->plan($payment->get('amount'), $direction, $storedInputs, $input, $isNew);
        } catch (InvalidValue|RuleNotSupported $e) {
            throw $this->errorMapper->toBadRequestIn($e, $type->entityType, $type->allocationEntityType);
        }

        $documents = $this->rows->lockDocuments($plan->documents());
        $this->checkTargets($plan, $type, $stored, $documents, $import);

        $settle = $settling
            ? AllocationPlan::sortedKeys([...$plan->affected, ...array_map(
                static fn ($row) => $row->input->targetKey(), $plan->rows)])
            : $plan->affected;

        if ($isNew && !$import) {
            $payment->set('number', $this->numberAllocator->allocate($type->series()));
        }

        $this->setName($payment);

        $newIds = [];

        foreach ($plan->rows as $index => $row) {
            if ($row->input->id === null) {
                $newIds[$index] = $this->idGenerator->generate();
            }
        }

        if ($listGiven) {
            $this->setTable($payment, $type, $plan, $stored, $documents, $newIds);
        }

        $silent = $import || (bool) $options->get(SaveOption::SILENT) || (bool) $options->get(SaveOption::NO_STREAM);

        return new PaymentPlan($plan, $stored, $documents, $newIds, $settle, $isNew, $silent);
    }

    public function persist(Entity $payment, PaymentType $type, PaymentPlan $plan): void
    {
        $options = [self::WRITE_OPTION => true, SaveOption::SILENT => true];
        $repository = $this->entityManager->getRDBRepository($type->allocationEntityType);
        $edit = $plan->edit;

        foreach ($edit->rows as $index => $planned) {
            if (!$planned->changed()) {
                continue;
            }

            $input = $planned->input;
            $row = $input->id !== null ? $plan->stored[$input->id] : $repository->getNew();

            if ($row->isNew()) {
                $row->set([
                    'id' => $plan->newIds[$index],
                    $type->parentLink . 'Id' => $payment->getId(),
                    'source' => 'manual',
                ]);
            }

            foreach ($type->targets as $documentType => $link) {
                $row->set($link . 'Id', $documentType === $input->targetType ? $input->targetId : null);
            }

            $document = $plan->documents[$input->targetKey()] ?? null;

            $row->set([
                'amount' => $input->amount->toFixed(Scale::MONEY),
                'amountCurrency' => (string) $this->config->get('defaultCurrency'),
                'order' => $planned->order,
                'name' => $this->rowName($payment, $document),
            ]);

            $this->entityManager->saveEntity($row, $options);
        }

        foreach ($edit->removed as $removed) {
            $this->entityManager->removeEntity($plan->stored[(string) $removed->id], $options);
        }

        foreach ($plan->settle as $key) {
            if (isset($plan->documents[$key])) {
                $this->settlement->recompute($plan->documents[$key], $plan->silent);
            }
        }

        if ($plan->isNew && $edit->rows !== [] && !$plan->silent) {
            // The core writes no Update note for a new record: the rows given at creation are recorded explicitly.
            $this->history->record($payment, [], $payment->get(self::ALLOCATION_LIST) ?? []);
        }
    }

    /**
     * beforeRemove of a payment: the ledger, the payment and the documents of its rows are locked, then the rows of a
     * locking read are removed here — not by the core cascade, whose plain read may come from a snapshot older than the
     * lock (core hooks read before this one) and miss a row another save committed meanwhile.
     *
     * @return array<string, Entity> locked documents by key
     */
    public function prepareRemoval(Entity $payment, PaymentType $type): array
    {
        if (!$this->numberAllocator->lock($type->series())) {
            return [];
        }

        $this->rowLock->one($type->entityType, $payment->getId());

        $rows = $this->rows->find($payment->getId(), $type, true);
        $keys = array_map(fn (Entity $row) => $this->rows->toInput($row, $type)->targetKey(), $rows);
        $documents = $this->rows->lockDocuments(AllocationPlan::sortedKeys($keys));

        foreach ($rows as $row) {
            $this->rows->removeWithOwner($row, $payment);
        }

        return $documents;
    }

    /**
     * afterRemove of a payment: its rows are gone (cascade), the documents get their new settlement.
     *
     * @param array<string, Entity> $documents
     */
    public function completeRemoval(array $documents, RemoveOptions $options): void
    {
        foreach ($documents as $document) {
            $this->settlement->recompute($document, (bool) $options->get(SaveOption::SILENT));
        }
    }

    /**
     * The table of a stored payment for the client and the API, with the allocated sum and the rest.
     *
     * @return array{list<stdClass>, Decimal, Decimal}
     */
    public function loadTable(Entity $payment, PaymentType $type): array
    {
        $rows = $payment->isNew() ? [] : $this->rows->find((string) $payment->getId(), $type);
        $inputs = array_map(fn (Entity $row) => $this->rows->toInput($row, $type), $rows);
        $list = $this->rows->presentStored($rows, $type, $this->rows->findDocuments($inputs));
        $allocated = Decimal::sum(array_map(static fn (AllocationInput $row) => $row->amount, $inputs));

        return [$list, $allocated, Decimal::ofNullable($payment->get('amount'))->sub($allocated)];
    }

    /**
     * @return list<AllocationInput>
     */
    public function parseAllocationList(mixed $value, PaymentType $type): array
    {
        if (!is_array($value)) {
            throw new InvalidValue('allocationList must be a list of rows.', 'badAllocationList');
        }

        $rows = [];

        foreach (array_values($value) as $index => $row) {
            if (!is_array($row) && !$row instanceof stdClass) {
                throw new InvalidValue('Row ' . ($index + 1) . ': not an object.', 'badAllocation', $index + 1);
            }

            $rows[] = AllocationInput::fromArray((array) $row, $index + 1, $type->targetAttributes());
        }

        return $rows;
    }

    /**
     * A row that changes what is paid on a document — new, moved (both documents), with another amount, removed —
     * needs a live document the user may read: settlement of a document is not changed through a payment by a user
     * who may not read the document. One message for a missing and an unreadable document, so the existence of a
     * document is not revealed. A row only renumbered changes no document.
     *
     * @param array<string, Entity> $stored
     * @param array<string, Entity> $documents
     */
    private function checkTargets(
        AllocationPlan $plan,
        PaymentType $type,
        array $stored,
        array $documents,
        bool $import,
    ): void {
        $touched = [];

        foreach ($plan->rows as $row) {
            if ($row->isNew() || $row->targetChanged() || $row->amountChanged()) {
                $touched[] = [$row->input, $row->order, true];
            }

            if ($row->targetChanged()) {
                $touched[] = [$row->previous, $row->order, false];
            }
        }

        foreach ($plan->removed as $removed) {
            $touched[] = [$removed, (int) $stored[(string) $removed->id]->get('order'), false];
        }

        foreach ($touched as [$input, $order, $required]) {
            $document = $documents[$input->targetKey()] ?? null;

            if ($document ? $import || $this->acl->checkEntity($document, Table::ACTION_READ) : !$required) {
                continue;
            }

            throw $this->errorMapper->toBadRequestIn(
                new InvalidValue("Row $order: no such document.", 'allocationUnknownTarget', $order,
                    $type->linkOf($input->targetType)),
                $type->entityType,
                $type->allocationEntityType,
            );
        }
    }

    /**
     * The canonical table before (fetched, from the locked rows) and after the save: the audited field the core
     * compares and writes to the Update note. An unchanged table is set back to the stored one: no note, no writes.
     *
     * @param array<string, Entity> $stored
     * @param array<string, Entity> $documents
     * @param array<int, string> $newIds
     */
    private function setTable(
        Entity $payment,
        PaymentType $type,
        AllocationPlan $plan,
        array $stored,
        array $documents,
        array $newIds,
    ): void {
        $was = $this->rows->presentStored($stored, $type, $documents);

        if (!$payment->isNew()) {
            $payment->setFetched(self::ALLOCATION_LIST, $was);
        }

        if (!$payment->isNew() && !$plan->changed()) {
            $payment->set(self::ALLOCATION_LIST, $was);

            return;
        }

        $became = [];

        foreach ($plan->rows as $index => $row) {
            $became[] = $this->rows->present($row->input, $row->input->id ?? $newIds[$index], $row->order, $type,
                $documents);
        }

        $payment->set(self::ALLOCATION_LIST, $became);
    }

    private function countingChanged(Entity $payment): bool
    {
        foreach (self::COUNTING as $attribute) {
            if ($payment->isAttributeChanged($attribute)) {
                return true;
            }
        }

        return false;
    }

    private function settlingChanged(Entity $payment): bool
    {
        foreach (self::SETTLING as $attribute) {
            if ($payment->isAttributeChanged($attribute)) {
                return true;
            }
        }

        return false;
    }

    /**
     * The entity was loaded before the lock; the ORM writes only attributes that differ from the fetched values.
     * Unchanged counting inputs take the locked row's values; changed ones keep this save's values (as documents do).
     */
    private function rebaseOnLockedRow(Entity $payment, Entity $current): void
    {
        foreach (self::COUNTING as $attribute) {
            $value = $current->get($attribute);

            if (!$payment->isAttributeChanged($attribute)) {
                $payment->set($attribute, $value);
            }

            $payment->setFetched($attribute, $value);
        }
    }

    private function setName(Entity $payment): void
    {
        if ($payment->get('name') !== $payment->get('number')) {
            $payment->set('name', $payment->get('number'));
        }
    }

    private function rowName(Entity $payment, ?Entity $document): string
    {
        return trim($payment->get('number') . ' → ' . ($document?->get('number') ?: $document?->get('name')));
    }

    private function setCurrency(Entity $payment): void
    {
        $currency = (string) $this->config->get('defaultCurrency');

        if ($payment->get('amountCurrency') !== $currency) {
            $payment->set('amountCurrency', $currency);
        }
    }
}
