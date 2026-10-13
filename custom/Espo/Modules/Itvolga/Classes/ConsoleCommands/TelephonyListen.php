<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Classes\ConsoleCommands;

use Espo\Core\Console\Command;
use Espo\Core\Console\Command\Params;
use Espo\Core\Console\IO;
use Espo\Core\Utils\Log;
use Espo\Modules\Itvolga\Tools\Telephony\Listener;
use Espo\Modules\Itvolga\Tools\Telephony\StatusFile;
use Monolog\Handler\NullHandler;

/**
 * `itvolga-telephony-listen` — the AMI listener of the live telephony (stage 07.1, D-166), run by systemd as the
 * EspoCRM user (unit itvolga-espo-telephony). Runs until SIGTERM; any failure ends it with a code (69 AMI, 75 retry,
 * 78 not configured: systemd does not restart) and systemd starts it again. The application log is muted: messages
 * of the ORM or PDO may quote values; the state is in data/itvolga-telephony-status.json.
 */
class TelephonyListen implements Command
{
    public function __construct(
        private Listener $listener,
        private Log $log,
    ) {}

    public function run(Params $params, IO $io): void
    {
        $this->log->pushHandler(new NullHandler());

        if (function_exists('pcntl_async_signals')) {
            pcntl_async_signals(true);
            pcntl_signal(SIGTERM, fn () => $this->listener->stop());
            pcntl_signal(SIGINT, fn () => $this->listener->stop());
        }

        $code = $this->listener->run(new StatusFile());
        $io->writeLine('telephony listener: exit ' . $code);
        $io->setExitStatus($code);
    }
}
