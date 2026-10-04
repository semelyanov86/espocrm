<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Classes\Select\Where;

use Espo\Core\Exceptions\BadRequest;
use Espo\Core\Select\Where\Item;
use Espo\Core\Select\Where\ItemConverter;
use Espo\Entities\User;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\DefinitionError;
use Espo\Modules\Itvolga\Tools\Report\ErrorMapper;
use Espo\Modules\Itvolga\Tools\Report\Run\ReportRunner;
use Espo\ORM\Query\Part\Condition as Cond;
use Espo\ORM\Query\Part\Expression as Expr;
use Espo\ORM\Query\Part\WhereItem;
use Espo\ORM\Query\SelectBuilder;
use Espo\ORM\Query\Part\WhereClause;

/**
 * Where item `itvolgaReport` (drill-down, D-98): the records of a report group, for the standard record list of the
 * main entity. The value is a JSON string {"id", "path": [level-1 key, level-2 key …], "filters"?, "quickFilters"?}.
 * The report is read with the user's rights and its records are selected by the same query as the result (ACL of
 * fields and related records, one-off conditions, quick filters), plus the group keys of the path.
 */
class ReportDrillDown implements ItemConverter
{
    public function __construct(
        private string $entityType,
        private User $user,
        private ReportRunner $runner,
    ) {}

    public function convert(SelectBuilder $queryBuilder, Item $item): WhereItem
    {
        $value = $item->getValue();
        $data = is_string($value) ? json_decode($value, true) : null;

        if ($item->getAttribute() !== 'id' || !is_array($data) || !is_string($data['id'] ?? null) ||
            !is_array($data['path'] ?? []) || !array_is_list($data['path'] ?? [])) {
            throw new BadRequest('Bad itvolgaReport where item.');
        }

        $report = $this->runner->loadReadable($data['id'], $this->user);

        if ($report->get('entityType') !== $this->entityType) {
            throw new BadRequest('itvolgaReport: entity type mismatch.');
        }

        try {
            $query = $this->runner->prepare($report, [
                'filters' => $data['filters'] ?? null,
                'quickFilters' => $data['quickFilters'] ?? [],
                'withQuickFilterOptions' => false,
            ], $this->user);
        } catch (DefinitionError $e) {
            throw ErrorMapper::toHttp($e);
        }

        $groups = $query->definition->groups;
        $path = $data['path'] ?? [];

        if (count($path) > count($groups)) {
            throw new BadRequest('itvolgaReport: bad group path.');
        }

        $builder = $query->base();

        foreach ($path as $i => $key) {
            if ($key !== null && !is_string($key) && !is_int($key) && !is_bool($key)) {
                throw new BadRequest('itvolgaReport: bad group key.');
            }

            $expression = $query->groupExpression($groups[$i]);
            $builder->where(WhereClause::fromRaw($key === null || $key === '' ?
                ['OR' => [[$expression => null], [$expression => '']]] : [$expression => $key]));
        }

        return Cond::in(Expr::column('id'), $builder->select(['id'])->build());
    }
}
