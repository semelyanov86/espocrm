<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Classes\Select\Report\AccessControlFilters;

use Espo\Core\Select\AccessControl\Filter;
use Espo\Entities\User;
use Espo\Modules\Itvolga\Classes\Select\Report\SharedReports;
use Espo\ORM\Query\Part\Condition as Cond;
use Espo\ORM\Query\SelectBuilder;

/**
 * Read level `team` (D-87): as `own`, plus the shared reports listing a team of the user.
 */
class OnlyTeam implements Filter
{
    public function __construct(private User $user) {}

    public function apply(SelectBuilder $queryBuilder): void
    {
        $items = [
            SharedReports::owner($this->user),
            SharedReports::public(),
            SharedReports::sharedWithUser($this->user),
        ];

        $teams = SharedReports::sharedWithTeams($this->user);

        if ($teams) {
            $items[] = $teams;
        }

        $queryBuilder->where(Cond::or(...$items));
    }
}
