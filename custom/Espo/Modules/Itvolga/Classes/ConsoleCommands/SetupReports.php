<?php

namespace Espo\Modules\Itvolga\Classes\ConsoleCommands;

use Espo\Core\Console\Command;
use Espo\Core\Console\Command\Params;
use Espo\Core\Console\IO;
use Espo\Modules\Itvolga\Tools\Report\Seed\StandardReports;

/**
 * Idempotent setup of the report module (stage 05.1, D-100): folders and standard reports of the registry
 * `app.itvolgaReports` (insert-only by seedKey). Part of `task model:apply`.
 *
 *   task espo -- itvolga-setup-reports            apply
 *   task espo -- itvolga-setup-reports --dry-run  show what would change
 */
class SetupReports implements Command
{
    public function __construct(private StandardReports $standardReports) {}

    public function run(Params $params, IO $io): void
    {
        $dryRun = $params->hasFlag('dryRun');
        [$changes, $errors] = $this->standardReports->apply($dryRun);

        $io->writeLine(($dryRun ? '[dry-run] ' : '') . ($changes ? implode("\n", $changes) : 'no changes'));

        foreach ($errors as $error) {
            $io->writeErrorLine($error);
        }

        if ($errors) {
            $io->setExitStatus(1);
        }
    }
}
