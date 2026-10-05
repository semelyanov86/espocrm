<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Mailing;

use DateTimeImmutable;
use Espo\Core\Utils\Json;
use Espo\Modules\Itvolga\Entities\Report;
use Espo\Modules\Itvolga\Tools\FinanceDocument\RowLock;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\DefinitionError;
use Espo\Modules\Itvolga\Tools\Report\Core\Mailing\MailingSettingsParser;
use Espo\ORM\EntityManager;
use Espo\ORM\Query\SelectBuilder;
use PDO;

/**
 * The state of a mailing a job keeps (D-122): which reports are due, the claim of one slot and the result of its
 * attempt. Writes are UPDATE queries of the runtime columns only — no save of the report, so the definition hook does
 * not check it with the rights of the job, `modifiedAt` stays.
 *
 * Claim, then work: under the lock of the report row the slot is read again and, still due, replaced by the next one in
 * the same short transaction. A second job (cron and `run-job` at once, the core rerun of a failed job) finds the slot
 * moved and leaves it. A process that dies after the claim loses that slot (at most one attempt).
 */
final class MailingRuntime
{
    public const BATCH = 50;

    public function __construct(
        private readonly EntityManager $entityManager,
        private readonly RowLock $rowLock,
        private readonly MailingClock $clock,
    ) {}

    /**
     * @return list<string>
     */
    public function dueIds(DateTimeImmutable $now): array
    {
        $query = SelectBuilder::create()
            ->from(Report::ENTITY_TYPE)
            ->select(['id'])
            ->where(['mailingNextRunAt<=' => $now->format('Y-m-d H:i:s'), 'deleted' => false])
            ->order([['mailingNextRunAt', 'ASC'], ['id', 'ASC']])
            ->limit(0, self::BATCH)
            ->build();

        return array_map('strval',
            $this->entityManager->getQueryExecutor()->execute($query)->fetchAll(PDO::FETCH_COLUMN));
    }

    /**
     * @return ?string the claimed slot (UTC), null when another job took it or the mailing is gone
     */
    public function claim(string $id, DateTimeImmutable $now): ?string
    {
        return $this->entityManager->getTransactionManager()->run(function () use ($id, $now): ?string {
            $report = $this->rowLock->one(Report::ENTITY_TYPE, $id);
            $scheduled = $report?->get('mailingNextRunAt');

            if (!is_string($scheduled) || $scheduled > $now->format('Y-m-d H:i:s')) {
                return null;
            }

            try {
                $settings = MailingSettingsParser::parse($report->get('mailing'));
            } catch (DefinitionError) {
                // A stored part the parser refuses is never due again; the attempt says why.
                $settings = null;
            }

            $this->update($id, [
                'mailingNextRunAt' => $this->clock->after($settings, $report->get('assignedUserId'), $scheduled, $now),
                'mailingLastRunAt' => $now->format('Y-m-d H:i:s'),
                'mailingLastResult' => Json::encode(['status' => 'running']),
            ]);

            return $scheduled;
        });
    }

    /**
     * @param array<string, mixed> $result outcome of the attempt (codes and counts only)
     */
    public function finish(string $id, array $result): void
    {
        $this->update($id, ['mailingLastResult' => Json::encode($result)]);
    }

    /**
     * @param array<string, mixed> $values
     */
    private function update(string $id, array $values): void
    {
        $this->entityManager->getQueryExecutor()->execute($this->entityManager->getQueryBuilder()
            ->update()
            ->in(Report::ENTITY_TYPE)
            ->set($values)
            ->where(['id' => $id])
            ->build());
    }
}
