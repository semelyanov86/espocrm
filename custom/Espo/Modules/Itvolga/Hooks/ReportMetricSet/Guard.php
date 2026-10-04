<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Hooks\ReportMetricSet;

use Espo\Core\Exceptions\Conflict;
use Espo\Core\Exceptions\Error\Body;
use Espo\Core\Hook\Hook\BeforeSave;
use Espo\Core\ORM\Entity as CoreEntity;
use Espo\Entities\User;
use Espo\Modules\Itvolga\Entities\ReportMetricSet;
use Espo\Modules\Itvolga\Tools\FinanceDocument\RowLock;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\DefinitionError;
use Espo\Modules\Itvolga\Tools\Report\Core\Metric\MetricRow;
use Espo\Modules\Itvolga\Tools\Report\Core\Metric\MetricRowsParser;
use Espo\Modules\Itvolga\Tools\Report\ErrorMapper;
use Espo\Modules\Itvolga\Tools\Report\Metric\MetricSources;
use Espo\ORM\Entity;
use Espo\ORM\EntityManager;
use Espo\ORM\Repository\Option\SaveOptions;

/**
 * Every save of a key-metrics set (D-111): the name is trimmed and unique among live sets (409; the unique index of
 * the repository closes the race); the rows are checked and stored in their canonical form. A row whose source is new
 * or changed must be one the saving user may build (report readable and tabular, numeric column, entity and filter
 * allowed); an unchanged row is not checked again — its source may have been removed or closed since, which must not
 * keep the author from renaming the set or reordering the rows (values are always computed for the viewer). The save is
 * compared with the row as committed now, under its lock.
 *
 * @implements BeforeSave<ReportMetricSet>
 */
class Guard implements BeforeSave
{
    public function __construct(
        private EntityManager $entityManager,
        private RowLock $rowLock,
        private MetricSources $sources,
        private User $user,
    ) {}

    public function beforeSave(Entity $entity, SaveOptions $options): void
    {
        assert($entity instanceof CoreEntity);

        $name = trim((string) $entity->get('name'));
        $entity->set('name', $name);
        $committed = [];

        if (!$entity->isNew()) {
            $current = $this->rowLock->one(ReportMetricSet::ENTITY_TYPE, $entity->getId());

            if ($current) {
                if (!$entity->isAttributeChanged('rows')) {
                    $entity->set('rows', $current->get('rows'));
                }

                $committed = $this->sourceKeys($current->get('rows'));
            }
        }

        if ($entity->isNew() || $entity->isAttributeChanged('name')) {
            $this->checkName($entity, $name);
        }

        try {
            $rows = MetricRowsParser::parse($entity->get('rows'));
        } catch (DefinitionError $e) {
            throw ErrorMapper::toHttp($e);
        }

        foreach ($rows as $i => $row) {
            if (($committed[$row->id] ?? null) !== $row->sourceKey()) {
                $this->sources->check($row, "rows[$i]", $this->user);
            }
        }

        $entity->set('rows', json_decode((string) json_encode(array_map(fn (MetricRow $r) => $r->toArray(), $rows))));
    }

    private function checkName(CoreEntity $entity, string $name): void
    {
        $other = $this->entityManager->getRDBRepositoryByClass(ReportMetricSet::class)
            ->where(['name' => $name, 'id!=' => $entity->getId() ?? ''])
            ->findOne();

        if ($other) {
            throw Conflict::createWithBody('metricSetNameExists',
                Body::create()->withMessageTranslation('metricSetNameExists', 'Report'));
        }
    }

    /**
     * @return array<string, string> row id → source key of the stored rows
     */
    private function sourceKeys(mixed $rows): array
    {
        try {
            $parsed = MetricRowsParser::parse($rows);
        } catch (DefinitionError) {
            return [];
        }

        $result = [];

        foreach ($parsed as $row) {
            $result[$row->id] = $row->sourceKey();
        }

        return $result;
    }
}
