<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Classes\FieldProcessing\ReportMetricSet;

use Espo\Core\FieldProcessing\Loader;
use Espo\Core\FieldProcessing\Loader\Params;
use Espo\Entities\User;
use Espo\Modules\Itvolga\Tools\Report\Core\Metric\MetricRow;
use Espo\Modules\Itvolga\Tools\Report\Metric\MetricSources;
use Espo\ORM\Entity;

/**
 * Rows of a key-metrics set as the reader sees them (D-111): the author and administrators get them whole (they edit
 * them); other readers get filter rows without the conditions copied from the author's saved filter, and without its
 * name for an entity they cannot read. Nothing is stored.
 *
 * @implements Loader<Entity>
 */
class RowsLoader implements Loader
{
    public function __construct(
        private User $user,
        private MetricSources $sources,
    ) {}

    public function process(Entity $entity, Params $params): void
    {
        if ($this->user->isAdmin() || $entity->get('createdById') === $this->user->getId() ||
            ($params->hasSelect() && !$params->hasInSelect('rows'))) {
            return;
        }

        $rows = json_decode((string) json_encode($entity->get('rows')), true);

        if (!is_array($rows)) {
            return;
        }

        foreach ($rows as $i => $row) {
            if (is_array($row) && ($row['source'] ?? null) === MetricRow::SOURCE_FILTER) {
                $rows[$i] = $this->sources->withoutConditions($row, $this->user);
            }
        }

        $entity->set('rows', json_decode((string) json_encode($rows)));
    }
}
