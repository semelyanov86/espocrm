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
 * Idempotent setup of finance documents (stage 04.2): the single legal entity (D-04; a placeholder until the import
 * fills the requisites) and the number counters of the registry (app.itvolgaFinance). Counters are created at
 * firstNumber and only raised, never lowered: at switchover the importer (or an operator) passes the re-read Vtiger
 * cur_id values.
 *
 *   task espo -- itvolga-setup-finance                               apply
 *   task espo -- itvolga-setup-finance --dry-run                     show what would change
 *   task espo -- itvolga-setup-finance --next=Quote:31,SalesOrder:18 raise counters
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

            foreach ($this->types->all() as $type) {
                $current = $this->numberAllocator->current($type);
                $target = max($type->firstNumber, $next[$type->entityType] ?? 0);

                if ($current === null || (isset($next[$type->entityType]) && $next[$type->entityType] > $current)) {
                    $changes[] = "counter " . ($current === null ? '+' : '~') . " {$type->entityType}: $target";
                }
            }

            $io->writeLine('[dry-run] ' . ($changes ? implode("\n", $changes) : 'no changes'));

            return;
        }

        $this->entityManager->getTransactionManager()->run(function () use (&$changes, $next): void {
            if ($this->legalEntityProvider->ensure()) {
                $changes[] = 'legal entity + Default';
            }

            foreach ($this->types->all() as $type) {
                $change = $this->numberAllocator->ensure($type, $next[$type->entityType] ?? null);

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

        foreach (array_filter(explode(',', (string) $option)) as $pair) {
            [$entityType, $value] = array_pad(explode(':', $pair, 2), 2, '');

            if (!$this->types->find($entityType) || !ctype_digit($value) || (int) $value < 1) {
                throw new Error("Bad --next value '$pair': expected EntityType:number, for example Quote:25.");
            }

            $result[$entityType] = (int) $value;
        }

        return $result;
    }
}
