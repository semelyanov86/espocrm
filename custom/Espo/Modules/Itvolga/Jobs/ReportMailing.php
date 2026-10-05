<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Jobs;

use Espo\Core\Job\JobDataLess;
use Espo\Core\Utils\Log;
use Espo\Modules\Itvolga\Tools\Report\Mailing\MailingClock;
use Espo\Modules\Itvolga\Tools\Report\Mailing\MailingProcessor;
use Espo\Modules\Itvolga\Tools\Report\Mailing\MailingRuntime;
use Throwable;

/**
 * Scheduled mailing of reports (D-122): the core scheduled job «ItvolgaReportMailing» every 15 minutes (created by
 * `itvolga-setup-reports`; forced: `task espo -- run-job ItvolgaReportMailing`). Every report whose next run has come is
 * claimed (its next slot written first), processed and its outcome recorded; a failure of one report is logged by its
 * id and class and does not stop the others. The job never throws, so the core does not rerun it and no letter goes
 * twice.
 */
class ReportMailing implements JobDataLess
{
    public function __construct(
        private MailingRuntime $runtime,
        private MailingProcessor $processor,
        private Log $log,
    ) {}

    public function run(): void
    {
        $now = MailingClock::now();

        try {
            $ids = $this->runtime->dueIds($now);
        } catch (Throwable $e) {
            $this->log->error('Report mailing: due reports not read: ' . $e::class);

            return;
        }

        foreach ($ids as $id) {
            try {
                if ($this->runtime->claim($id, $now) === null) {
                    continue;
                }
            } catch (Throwable $e) {
                $this->log->error("Report mailing $id: claim failed: " . $e::class);

                continue;
            }

            try {
                $outcome = $this->processor->process($id);
            } catch (Throwable $e) {
                $this->log->error("Report mailing $id: " . $e::class . ' at ' . basename($e->getFile()) . ':' .
                    $e->getLine());
                $outcome = ['status' => 'failed', 'error' => 'internalError'];
            }

            try {
                $this->runtime->finish($id, $outcome, $now);
            } catch (Throwable $e) {
                $this->log->error("Report mailing $id: outcome not saved: " . $e::class);
            }
        }
    }
}
