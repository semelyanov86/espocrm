<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Classes\Select\Report\AccessControlFilters;

use Espo\Core\Select\AccessControl\Filter;
use Espo\Entities\User;
use Espo\Modules\Itvolga\Classes\Select\Report\SharedReports;
use Espo\ORM\Query\Part\Condition as Cond;
use Espo\ORM\Query\SelectBuilder;

/**
 * Applied at every read level, `all` included (D-87): a private report is listed to its owner and administrators only.
 */
class Mandatory implements Filter
{
    public function __construct(private User $user) {}

    public function apply(SelectBuilder $queryBuilder): void
    {
        if ($this->user->isAdmin()) {
            return;
        }

        $queryBuilder->where(Cond::or(SharedReports::notPrivate(), SharedReports::owner($this->user)));
    }
}
