<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Classes\FieldProcessing\Report;

use Espo\Core\FieldProcessing\Loader;
use Espo\Core\FieldProcessing\Loader\Params;
use Espo\Core\Select\SelectBuilderFactory;
use Espo\Entities\User;
use Espo\Modules\Itvolga\Entities\ReportMetricSet;
use Espo\ORM\Entity;
use Espo\ORM\EntityManager;
use PDO;

/**
 * `usedInMetrics` of the reports list (D-115): whether a key-metrics set the user may read has a row of the report.
 * The sets are read once per list request; nothing is stored, so deleting and restoring sets or reports needs no upkeep.
 *
 * @implements Loader<Entity>
 */
class MetricUsageLoader implements Loader
{
    /** @var ?array<string, true> */
    private ?array $used = null;

    public function __construct(
        private EntityManager $entityManager,
        private SelectBuilderFactory $selectBuilderFactory,
        private User $user,
    ) {}

    public function process(Entity $entity, Params $params): void
    {
        if ($params->hasSelect() && !$params->hasInSelect('usedInMetrics')) {
            return;
        }

        $entity->set('usedInMetrics', isset($this->used()[$entity->getId()]));
    }

    /**
     * @return array<string, true>
     */
    private function used(): array
    {
        if ($this->used !== null) {
            return $this->used;
        }

        $query = $this->selectBuilderFactory
            ->create()
            ->from(ReportMetricSet::ENTITY_TYPE)
            ->forUser($this->user)
            ->withStrictAccessControl()
            ->buildQueryBuilder()
            ->select(['rows'])
            ->build();
        $this->used = [];

        foreach ($this->entityManager->getQueryExecutor()->execute($query)->fetchAll(PDO::FETCH_COLUMN) as $json) {
            foreach (json_decode((string) $json, true) ?: [] as $row) {
                if (is_array($row) && ($row['source'] ?? null) === 'report' && is_string($row['reportId'] ?? null)) {
                    $this->used[$row['reportId']] = true;
                }
            }
        }

        return $this->used;
    }
}
