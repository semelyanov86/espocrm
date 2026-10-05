<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Seed;

use Espo\Core\Utils\Language;
use Espo\Core\Utils\Metadata;
use Espo\Entities\ScheduledJob;
use Espo\ORM\EntityManager;
use Espo\ORM\Query\SelectBuilder;
use PDO;

/**
 * The scheduled job of report mailings (D-122): a ScheduledJob record «ItvolgaReportMailing» with the scheduling of
 * `app.scheduledJobs`, inserted when missing (looked up by `job`, also among deleted ones, as the seed of D-100). An
 * existing record is never changed: an administrator may have switched it off, changed its period or removed it.
 */
final class MailingJob
{
    public const JOB = 'ItvolgaReportMailing';

    public function __construct(
        private readonly EntityManager $entityManager,
        private readonly Metadata $metadata,
        private readonly Language $language,
    ) {}

    /**
     * @return ?string the change, or null
     */
    public function apply(bool $dryRun): ?string
    {
        $query = SelectBuilder::create()
            ->from(ScheduledJob::ENTITY_TYPE)
            ->select(['id'])
            ->where(['job' => self::JOB])
            ->withDeleted()
            ->build();

        if ($this->entityManager->getQueryExecutor()->execute($query)->fetch(PDO::FETCH_ASSOC)) {
            return null;
        }

        $scheduling = (string) $this->metadata->get(['app', 'scheduledJobs', self::JOB, 'scheduling']);

        if (!$dryRun) {
            $job = $this->entityManager->getRDBRepositoryByClass(ScheduledJob::class)->getNew();
            $job
                ->setJob(self::JOB)
                ->setActive()
                ->setScheduling($scheduling)
                ->setName((string) $this->language->translateOption(self::JOB, 'job', 'ScheduledJob'));
            $this->entityManager->saveEntity($job);
        }

        return 'scheduled job ' . self::JOB . " ($scheduling)";
    }
}
