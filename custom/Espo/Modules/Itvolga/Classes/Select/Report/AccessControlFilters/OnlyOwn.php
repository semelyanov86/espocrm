<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Classes\Select\Report\AccessControlFilters;

use Espo\Core\Select\AccessControl\Filter;
use Espo\Entities\User;
use Espo\Modules\Itvolga\Classes\Select\Report\SharedReports;
use Espo\ORM\Query\Part\Condition as Cond;
use Espo\ORM\Query\SelectBuilder;

/**
 * Read level `own` (D-87): own reports, public ones and the shared ones listing the user.
 */
class OnlyOwn implements Filter
{
    public function __construct(private User $user) {}

    public function apply(SelectBuilder $queryBuilder): void
    {
        $queryBuilder->where(Cond::or(
            SharedReports::owner($this->user),
            SharedReports::public(),
            SharedReports::sharedWithUser($this->user),
        ));
    }
}
