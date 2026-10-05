<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Export;

use Espo\Core\Exceptions\Forbidden;
use Espo\Core\Exceptions\NotFound;
use Espo\Core\Job\JobSchedulerFactory;
use Espo\Entities\User;
use Espo\Modules\Itvolga\Entities\Report;
use Espo\Modules\Itvolga\Jobs\ReportExport;
use Espo\Modules\Itvolga\Tools\Report\Core\Export\ExportRequest;
use Espo\Modules\Itvolga\Tools\Report\Query\ReportQuery;
use Espo\Modules\Itvolga\Tools\Report\Run\ReportRunner;
use Espo\ORM\EntityManager;

/**
 * Export and print of a report result for the current user (D-116, D-120, D-125): the right to export, read access to
 * the report, then one run of all rows within the limits in a reading transaction — the definition and the conditions
 * checked with his ACL — and the file built outside of it. A background export checks the same now and queues a job
 * that checks them again when it runs.
 */
final class ExportService
{
    public function __construct(
        private readonly ReportRunner $runner,
        private readonly ReportFiles $files,
        private readonly AttachmentStore $store,
        private readonly ExportAccess $access,
        private readonly EntityManager $entityManager,
        private readonly JobSchedulerFactory $jobSchedulerFactory,
    ) {}

    /**
     * @param array<string, mixed> $raw
     * @return array<string, mixed> {id, name, type} of the attachment, or {scheduled: true}
     * @throws Forbidden
     * @throws NotFound
     */
    public function export(string $reportId, array $raw, User $user): array
    {
        $request = ExportRequest::parse($raw, ReportFiles::FORMATS);
        $this->access->assert($user);
        $report = $this->runner->loadReadable($reportId, $user);

        if ($request->background) {
            // The definition and the conditions are checked now, so a mistake is answered at once.
            $this->runner->prepare($report, $request->runParams, $user, true);

            $this->jobSchedulerFactory
                ->create()
                ->setClassName(ReportExport::class)
                ->setData([
                    'reportId' => $report->getId(),
                    'userId' => $user->getId(),
                    'format' => $request->format,
                    'runParams' => $request->runParams,
                ])
                ->schedule();

            return ['scheduled' => true];
        }

        $result = $this->result($report, $request->runParams, $user);
        $file = $this->files->build($result, $user, $request->format, (string) $report->get('name'));
        $attachment = $this->store->exportFile($file, $user->getId());

        return ['id' => $attachment->getId(), 'name' => $attachment->getName(), 'type' => $attachment->getType()];
    }

    /**
     * @param array<string, mixed> $raw
     * @return array{title: string, orientation: string, html: string}
     * @throws Forbidden
     * @throws NotFound
     */
    public function printView(string $reportId, array $raw, User $user): array
    {
        $request = ExportRequest::parse($raw, []);
        $this->access->assert($user);
        $report = $this->runner->loadReadable($reportId, $user);

        return $this->files->printView($this->result($report, $request->runParams, $user), $user,
            (string) $report->get('name'));
    }

    /**
     * All rows of a report within its limits (or without them — noLimit) for a user, in one reading transaction. The
     * caller has checked what the user may see of the report itself.
     *
     * @param array<string, mixed> $runParams
     * @return array<string, mixed>
     */
    public function result(Report $report, array $runParams, User $user): array
    {
        return $this->run($report, $runParams, $user)[1];
    }

    /**
     * The prepared query (its definition as the user's schema parsed it) and the result of all rows.
     *
     * @param array<string, mixed> $runParams
     * @return array{ReportQuery, array<string, mixed>}
     */
    public function run(Report $report, array $runParams, User $user): array
    {
        return $this->entityManager->getTransactionManager()->run(function () use ($report, $runParams, $user): array {
            $query = $this->runner->prepare($report, $runParams, $user, true);

            return [$query, $this->runner->execute($query, $report)];
        });
    }
}
