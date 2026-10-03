<?php

namespace Espo\Modules\Itvolga\Classes\ConsoleCommands;

use Espo\Core\Console\Command;
use Espo\Core\Console\Command\Params;
use Espo\Core\Console\IO;
use Espo\Core\Exceptions\Error;
use Espo\Modules\Itvolga\Tools\Finance\Decimal;
use Espo\Modules\Itvolga\Tools\FinanceDocument\DocumentTypes;
use Espo\Modules\Itvolga\Tools\FinanceDocument\NumberAllocator;
use Espo\Modules\Itvolga\Tools\FinanceDocument\NumberSeries;
use Espo\Modules\Itvolga\Tools\FinanceDocument\RowLock;
use Espo\Modules\Itvolga\Tools\FinancePayment\SettlementUpdater;
use Espo\ORM\EntityManager;

/**
 * Stored settlement of invoices and sales orders recalculated from their allocations (stage 04.4): initialises the
 * documents saved before the stage, repairs what a write past the hooks left behind (SQL, restore) and closes the
 * import of stage 06.3 (allocations are imported silently, then this command settles every document). Each document
 * is settled in its own transaction under the payment ledger, the lock order of a payment save. Prints counts only.
 *
 *   task espo -- itvolga-finance-settle                              all documents, audited changes
 *   task espo -- itvolga-finance-settle --entity=Invoice --id=a,b     selected documents
 *   task espo -- itvolga-finance-settle --dry-run                     count what would change
 *   task espo -- itvolga-finance-settle --silent                      without audit notes (initialisation, import)
 */
class FinanceSettle implements Command
{
    public function __construct(
        private EntityManager $entityManager,
        private DocumentTypes $types,
        private NumberAllocator $numberAllocator,
        private SettlementUpdater $settlement,
        private RowLock $rowLock,
    ) {}

    public function run(Params $params, IO $io): void
    {
        $only = $params->getOption('entity');
        $ids = array_values(array_filter(explode(',', (string) $params->getOption('id'))));
        $dryRun = $params->hasFlag('dryRun');
        $silent = $params->hasFlag('silent');
        $counts = [];

        foreach ($this->types->payments() as $paymentType) {
            foreach (array_keys($paymentType->targets) as $entityType) {
                if ($only !== null && $only !== $entityType) {
                    continue;
                }

                $where = $ids !== [] ? ['id' => $ids] : [];
                $documentIds = array_map(
                    static fn ($document) => $document->getId(),
                    [...$this->entityManager->getRDBRepository($entityType)->select(['id'])->where($where)->find()],
                );

                foreach ($documentIds as $id) {
                    $state = $this->entityManager->getTransactionManager()->run(
                        fn () => $this->settleOne($paymentType->series(), $entityType, $id, $dryRun, $silent));

                    $counts["$entityType $state"] = ($counts["$entityType $state"] ?? 0) + 1;
                }
            }
        }

        if ($only !== null && $counts === [] && !$this->types->findPaymentByTarget($only)) {
            throw new Error("Unknown --entity '$only': expected Invoice or SalesOrder.");
        }

        ksort($counts);

        foreach ($counts as $key => $count) {
            $io->writeLine(($dryRun ? '[dry-run] ' : '') . "$key: $count");
        }

        if ($counts === []) {
            $io->writeLine('no documents');
        }
    }

    private function settleOne(
        NumberSeries $series,
        string $entityType,
        string $id,
        bool $dryRun,
        bool $silent,
    ): string {
        $this->numberAllocator->lock($series);

        $document = $this->rowLock->one($entityType, $id);

        if (!$document) {
            return 'gone';
        }

        if ($dryRun) {
            $settlement = $this->settlement->settlement($document, $this->settlement->paymentTypeOf($entityType));
            $same = static fn ($stored, Decimal $value) => $stored !== null && $stored !== '' &&
                $value->equals(Decimal::of($stored));

            return $document->get('settlementState') === $settlement->state->value &&
                $same($document->get('paidAmount'), $settlement->paid) &&
                $same($document->get('balanceAmount'), $settlement->balance) ? 'unchanged' : 'would change';
        }

        return $this->settlement->recompute($document, $silent) ? 'changed' : 'unchanged';
    }
}
