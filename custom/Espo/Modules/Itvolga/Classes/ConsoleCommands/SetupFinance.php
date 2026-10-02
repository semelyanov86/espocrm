<?php

namespace Espo\Modules\Itvolga\Classes\ConsoleCommands;

use Espo\Core\Console\Command;
use Espo\Core\Console\Command\Params;
use Espo\Core\Console\IO;
use Espo\Core\Exceptions\Error;
use Espo\Modules\Itvolga\Tools\FinanceDocument\DocumentTypes;
use Espo\Modules\Itvolga\Tools\FinanceDocument\LegalEntityProvider;
use Espo\Modules\Itvolga\Tools\FinanceDocument\NumberAllocator;
use Espo\ORM\EntityManager;

/**
 * Idempotent setup of finance records (stages 04.2–04.4): the single legal entity (D-04; a placeholder until the import
 * fills the requisites) and the number counters of the registry (app.itvolgaFinance: documents and payments).
 * Counters are created at firstNumber and only raised, never lowered: at switchover the importer (or an operator)
 * passes the re-read Vtiger cur_id values.
 *
 *   task espo -- itvolga-setup-finance                               apply
 *   task espo -- itvolga-setup-finance --dry-run                     show what would change
 *   task espo -- itvolga-setup-finance --next=Quote:31,Payment:995   raise counters
 */
class SetupFinance implements Command
{
    public function __construct(
        private EntityManager $entityManager,
        private DocumentTypes $types,
        private NumberAllocator $numberAllocator,
        private LegalEntityProvider $legalEntityProvider,
    ) {}

    public function run(Params $params, IO $io): void
    {
        $dryRun = $params->hasFlag('dryRun');
        $next = $this->parseNext($params->getOption('next'));
        $changes = [];

        if ($dryRun) {
            if ($this->legalEntityProvider->findDefaultId() === null) {
                $changes[] = 'legal entity + Default';
            }

            foreach ($this->types->numberSeries() as $series) {
                $current = $this->numberAllocator->current($series);
                $target = max($series->firstNumber, $next[$series->entityType] ?? 0);

                if ($current === null || (isset($next[$series->entityType]) && $next[$series->entityType] > $current)) {
                    $changes[] = "counter " . ($current === null ? '+' : '~') . " {$series->entityType}: $target";
                }
            }

            $io->writeLine('[dry-run] ' . ($changes ? implode("\n", $changes) : 'no changes'));

            return;
        }

        $this->entityManager->getTransactionManager()->run(function () use (&$changes, $next): void {
            if ($this->legalEntityProvider->ensure()) {
                $changes[] = 'legal entity + Default';
            }

            foreach ($this->types->numberSeries() as $series) {
                $change = $this->numberAllocator->ensure($series, $next[$series->entityType] ?? null);

                if ($change !== null) {
                    $changes[] = $change;
                }
            }
        });

        $io->writeLine($changes ? implode("\n", $changes) : 'no changes');
    }

    /**
     * @return array<string, int>
     */
    private function parseNext(?string $option): array
    {
        $result = [];

        $known = array_map(static fn ($series) => $series->entityType, $this->types->numberSeries());

        foreach (array_filter(explode(',', (string) $option)) as $pair) {
            [$entityType, $value] = array_pad(explode(':', $pair, 2), 2, '');

            if (!in_array($entityType, $known, true) || !ctype_digit($value) || (int) $value < 1) {
                throw new Error("Bad --next value '$pair': expected EntityType:number, for example Quote:25.");
            }

            $result[$entityType] = (int) $value;
        }

        return $result;
    }
}
