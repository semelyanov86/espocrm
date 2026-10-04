<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Hooks\ReportMetricSet;

use Espo\Core\Hook\Hook\AfterRemove;
use Espo\Core\Utils\Log;
use Espo\Modules\Itvolga\Entities\ReportMetricSet;
use Espo\Modules\Itvolga\Tools\Report\Dashboard\DashletRemover;
use Espo\ORM\Entity;
use Espo\ORM\Repository\Option\RemoveOptions;
use Throwable;

/**
 * A deleted key-metrics set leaves no dashlets behind (D-113): they are removed from the users' dashboards, the
 * dashboard templates and the default dashboard. A failure is logged (ids only) and does not undo the deletion; a
 * dashlet left over shows that its set is deleted.
 *
 * @implements AfterRemove<ReportMetricSet>
 */
class RemoveDashlets implements AfterRemove
{
    public function __construct(
        private DashletRemover $remover,
        private Log $log,
    ) {}

    public function afterRemove(Entity $entity, RemoveOptions $options): void
    {
        try {
            $this->remover->remove($entity->getId());
        } catch (Throwable $e) {
            $this->log->error("Key metrics set {$entity->getId()}: dashlets not removed: " . $e->getMessage());
        }
    }
}
