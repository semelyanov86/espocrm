<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\FinancePayment;

use Espo\Core\ORM\Repository\Option\SaveOption;
use Espo\Core\Utils\Config;
use Espo\Modules\Itvolga\Tools\Finance\Decimal;
use Espo\Modules\Itvolga\Tools\Finance\Editing\Limits;
use Espo\Modules\Itvolga\Tools\Finance\Exceptions\InvalidValue;
use Espo\Modules\Itvolga\Tools\Finance\Payment\AllocationCalculator;
use Espo\Modules\Itvolga\Tools\Finance\Payment\AllocationShare;
use Espo\Modules\Itvolga\Tools\Finance\Payment\Direction;
use Espo\Modules\Itvolga\Tools\Finance\Payment\Settlement;
use Espo\Modules\Itvolga\Tools\FinanceDocument\DocumentTypes;
use Espo\Modules\Itvolga\Tools\FinanceDocument\ErrorMapper;
use Espo\Modules\Itvolga\Tools\FinanceDocument\PaymentType;
use Espo\ORM\Entity;
use Espo\ORM\EntityManager;

/**
 * Stored settlement of invoices and sales orders (owner decision 2026-10-02): paidAmount, balanceAmount and
 * settlementState, computed by AllocationCalculator (D-49: incoming allocations in status Executed or empty count;
 * balance = total − paid, negative when overpaid). Only this class writes them; the document status is never derived
 * from them (D-26). The three fields are audited: the core writes their changes to the document's audit log.
 *
 * Two ways in:
 * - payment side (payment save or removal, an imported allocation, itvolga-finance-settle): the caller holds the
 *   payment ledger and the document row; recompute() reads the document's allocations with a locking read (fresh
 *   under REPEATABLE READ, never waiting under the ledger) and saves the document;
 * - document side (DocumentProcessor, the total changed): applyTotal() keeps the stored paid sum of the locked row and
 *   re-derives balance and state — a document save never reads payments, so it never waits for them.
 */
class SettlementUpdater
{
    /** Save option of the settlement write of a document: the finance document hook skips it. */
    public const OPTION = 'itvolgaSettlement';
    public const FIELDS = ['paidAmount', 'balanceAmount', 'settlementState'];
    private const MONEY = ['paidAmount', 'balanceAmount'];
    /** DECIMAL(25,8) of the stored sums (MySQL runs non-strict, D-33: an overflow would be clamped silently). */
    private const LIMIT = [25, 8];

    private AllocationCalculator $calculator;

    public function __construct(
        private EntityManager $entityManager,
        private Config $config,
        private DocumentTypes $types,
    ) {
        $this->calculator = new AllocationCalculator();
    }

    public function paymentTypeOf(string $documentType): ?PaymentType
    {
        return $this->types->findPaymentByTarget($documentType);
    }

    /**
     * Document side: a new document (paid 0) or a changed total. `$storedPaid` comes from the locked row.
     */
    public function applyTotal(Entity $document, mixed $storedPaid): void
    {
        $paid = Decimal::ofNullable($storedPaid === '' ? null : $storedPaid);
        $total = Decimal::ofNullable($document->get('grandTotal'));

        $this->set($document, $this->calculator->fromPaid($total, $paid));
    }

    /**
     * Payment side: the document row is locked by the caller (and the payment ledger is held). Saves the document only
     * when its settlement changed; silent saves (import, --silent) write no audit notes.
     *
     * @return bool whether the settlement changed
     */
    public function recompute(Entity $document, bool $silent): bool
    {
        $type = $this->paymentTypeOf($document->getEntityType());

        if (!$type) {
            return false;
        }

        if (!$this->set($document, $this->settlement($document, $type))) {
            return false;
        }

        $this->entityManager->saveEntity($document, [
            self::OPTION => true,
            SaveOption::SKIP_MODIFIED_BY => true,
            SaveOption::SILENT => $silent,
        ]);

        return true;
    }

    /**
     * Settlement of a document from its live allocations and their payments. Locking read: it sees the latest
     * committed rows even when the transaction's snapshot is older; under the payment ledger nothing else holds these
     * rows, so it never waits. Sums are Decimal (the repository sum() returns floats).
     */
    public function settlement(Entity $document, PaymentType $type): Settlement
    {
        $link = $type->linkOf($document->getEntityType());

        $query = $this->entityManager
            ->getQueryBuilder()
            ->select()
            ->from($type->allocationEntityType)
            ->select(['amount', ['payment.direction', 'paymentDirection'], ['payment.status', 'paymentStatus']])
            ->join($type->parentLink)
            ->where([
                $link . 'Id' => $document->getId(),
                $type->parentLink . '.deleted' => false,
            ])
            ->forShare()
            ->build();

        $shares = [];

        foreach ($this->entityManager->getQueryExecutor()->execute($query)->fetchAll() as $row) {
            $shares[] = AllocationShare::of($row['amount'], Direction::from((string) $row['paymentDirection']),
                (string) $row['paymentStatus']);
        }

        return $this->calculator->settle(Decimal::ofNullable($document->get('grandTotal')), $shares);
    }

    /**
     * @return bool whether a value changed (decimals compared as numbers: 100.00 and 100.00000000 are equal)
     * @throws \Espo\Core\Exceptions\BadRequest a sum that does not fit its column: the whole save is rolled back
     */
    private function set(Entity $document, Settlement $settlement): bool
    {
        $values = [
            'paidAmount' => $settlement->paid,
            'balanceAmount' => $settlement->balance,
        ];

        foreach ($values as $attribute => $value) {
            try {
                Limits::check($value, self::LIMIT, $attribute);
            } catch (InvalidValue) {
                throw ErrorMapper::badRequest('financeSettlementTooLarge');
            }
        }
        $changed = false;
        $currency = (string) $this->config->get('defaultCurrency');

        foreach ($values as $attribute => $value) {
            $current = $document->get($attribute);

            if ($current === null || $current === '' || !$value->equals(Decimal::of($current))) {
                $document->set($attribute, $value->toString());
                $changed = true;
            }
        }

        foreach (self::MONEY as $attribute) {
            if ($document->get($attribute . 'Currency') !== $currency) {
                $document->set($attribute . 'Currency', $currency);
            }
        }

        if ($document->get('settlementState') !== $settlement->state->value) {
            $document->set('settlementState', $settlement->state->value);
            $changed = true;
        }

        return $changed;
    }
}
