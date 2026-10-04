<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Metric;

use Espo\Core\AclManager;
use Espo\Core\Exceptions\BadRequest;
use Espo\Core\Exceptions\Error\Body;
use Espo\Core\Exceptions\Forbidden;
use Espo\Core\Exceptions\NotFound;
use Espo\Core\Utils\Metadata;
use Espo\Entities\User;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\DefinitionError;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\FieldForbidden;
use Espo\Modules\Itvolga\Tools\Report\Core\Format\NumberText;
use Espo\Modules\Itvolga\Tools\Report\Core\Metric\MetricRow;
use Espo\Modules\Itvolga\Tools\Report\Core\Metric\MetricRules;
use Espo\Modules\Itvolga\Tools\Report\ErrorMapper;
use Espo\Modules\Itvolga\Tools\Report\Format\FormatContextFactory;
use Espo\Modules\Itvolga\Tools\Report\Run\ReportRunner;
use Espo\Modules\Itvolga\Tools\Report\Schema\SchemaFactory;

/**
 * Sources of key-metric rows (D-111, D-112), always for a given user: check() refuses a row the saving user may not
 * build (HTTP errors with `Report.messages.*`, the place is `rows[i]…`); evaluate() gives the value of each row for the
 * viewer — a report row through ReportRunner (the report's conditions, the viewer's ACL), a filter row through the
 * standard list query — and a status per row, so one closed or removed source does not hide the others. The name of a
 * report is never returned: it would leak for a report the viewer cannot read.
 */
final class MetricSources
{
    public const STATUS_OK = 'ok';
    public const STATUS_FORBIDDEN = 'forbidden';
    public const STATUS_NOT_FOUND = 'notFound';
    public const STATUS_INVALID = 'invalid';

    public function __construct(
        private readonly ReportRunner $runner,
        private readonly FilterQuery $filterQuery,
        private readonly SchemaFactory $schemaFactory,
        private readonly AclManager $aclManager,
        private readonly Metadata $metadata,
        private readonly FormatContextFactory $formatContextFactory,
    ) {}

    /**
     * @throws BadRequest
     * @throws Forbidden
     */
    public function check(MetricRow $row, string $path, User $user): void
    {
        try {
            if ($row->source === MetricRow::SOURCE_REPORT) {
                $this->reportValue($row, $user, false);

                return;
            }

            $this->filterCount($row, $user);
        } catch (NotFound) {
            throw self::error('metricReportNotFound', "$path.reportId");
        } catch (DefinitionError $e) {
            $class = $e instanceof FieldForbidden ? FieldForbidden::class : DefinitionError::class;

            throw ErrorMapper::toHttp(new $class($e->key, $path . ($e->path !== '' ? '.' . $e->path : ''), $e->params));
        } catch (Forbidden $e) {
            throw $e->getBody() !== null ? $e : Forbidden::createWithBody('metric source',
                Body::create()->withMessageTranslation($row->source === MetricRow::SOURCE_REPORT ?
                    'metricReportForbidden' : 'metricFilterForbidden', 'Report', ['path' => $path]));
        } catch (BadRequest) {
            throw self::error('badMetricFilter', "$path.where");
        }
    }

    /**
     * @param list<MetricRow> $rows
     * @return list<array<string, mixed>> each row with `status` and `value` (a result cell or null)
     */
    public function evaluate(array $rows, User $viewer): array
    {
        $numbers = $this->formatContextFactory->create($viewer)->numbers;

        return array_map(function (MetricRow $row) use ($viewer, $numbers): array {
            $status = self::STATUS_OK;
            $value = null;

            try {
                $value = $row->source === MetricRow::SOURCE_REPORT ? $this->reportValue($row, $viewer, true) :
                    self::countCell($this->filterCount($row, $viewer), $numbers);
            } catch (NotFound) {
                $status = self::STATUS_NOT_FOUND;
            } catch (FieldForbidden|Forbidden) {
                $status = self::STATUS_FORBIDDEN;
            } catch (DefinitionError|BadRequest) {
                $status = self::STATUS_INVALID;
            }

            $data = $row->toArray();

            if ($row->source === MetricRow::SOURCE_FILTER) {
                $data['where'] = $this->filterQuery->forUser($row->where, $viewer);
            }

            return $data + ['status' => $status, 'value' => $value];
        }, $rows);
    }

    /**
     * @return ?array<string, mixed>
     * @throws NotFound
     * @throws Forbidden
     */
    private function reportValue(MetricRow $row, User $user, bool $compute): ?array
    {
        $report = $this->runner->loadReadable((string) $row->reportId, $user);

        if ($compute) {
            return $this->runner->metric($report, $row->function, $row->column, $user);
        }

        MetricRules::aggregate($this->runner->prepare($report, ['withQuickFilterOptions' => false], $user)->definition,
            $row->function, $row->column);

        return null;
    }

    /**
     * @throws BadRequest
     * @throws Forbidden
     */
    private function filterCount(MetricRow $row, User $user): int
    {
        $entityType = (string) $row->entityType;
        $this->schemaFactory->create($user)->assertEntity($entityType);

        if (!$this->aclManager->checkScope($user, $entityType, 'read')) {
            throw new FieldForbidden('metricEntityForbidden', 'entityType');
        }

        if ($row->filter['kind'] === MetricRow::KIND_SYSTEM && !$this->hasPrimaryFilter($entityType,
            $row->filter['name'])) {
            throw new DefinitionError('badMetricFilter', 'filter');
        }

        return $this->filterQuery->count($entityType, $row->where, $user);
    }

    /**
     * A system filter of the entity's list (clientDefs filterList: names or {name}).
     */
    private function hasPrimaryFilter(string $entityType, string $name): bool
    {
        foreach ($this->metadata->get(['clientDefs', $entityType, 'filterList']) ?? [] as $item) {
            if ((is_array($item) ? ($item['name'] ?? null) : $item) === $name) {
                return true;
            }
        }

        return false;
    }

    /**
     * @return array{v: int, f: string}
     */
    private static function countCell(int $count, NumberText $numbers): array
    {
        return ['v' => $count, 'f' => $numbers->format($count)];
    }

    private static function error(string $key, string $path): BadRequest
    {
        return BadRequest::createWithBody($key, Body::create()->withMessageTranslation($key, 'Report',
            ['path' => $path]));
    }
}
