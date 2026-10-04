<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Classes\Select\Report;

use Espo\Entities\User;
use Espo\Modules\Itvolga\Entities\Report;
use Espo\ORM\Query\Part\Condition as Cond;
use Espo\ORM\Query\Part\Expression as Expr;
use Espo\ORM\Query\Part\WhereItem;
use Espo\ORM\Query\SelectBuilder;

/**
 * SQL form of the report reading rule (Tools/Report/Core/Access/SharingPolicy, D-87): the conditions the access
 * filters of the scope combine. The lists of users and teams are read through their middle tables by sub-queries,
 * so a filter never multiplies rows.
 */
final class SharedReports
{
    public static function owner(User $user): WhereItem
    {
        return Cond::equal(Expr::column('assignedUserId'), $user->getId());
    }

    public static function notPrivate(): WhereItem
    {
        return Cond::notEqual(Expr::column('accessType'), Report::ACCESS_PRIVATE);
    }

    public static function public(): WhereItem
    {
        return Cond::equal(Expr::column('accessType'), Report::ACCESS_PUBLIC);
    }

    public static function sharedWithUser(User $user): WhereItem
    {
        return Cond::and(
            Cond::equal(Expr::column('accessType'), Report::ACCESS_SHARED),
            Cond::in(
                Expr::column('id'),
                SelectBuilder::create()
                    ->from('ReportSharedUser', 'sharedUser')
                    ->select('sharedUser.reportId')
                    ->where(['sharedUser.userId' => $user->getId(), 'sharedUser.deleted' => false])
                    ->build()
            ),
        );
    }

    public static function sharedWithTeams(User $user): ?WhereItem
    {
        $teamIds = $user->getTeamIdList();

        if ($teamIds === []) {
            return null;
        }

        return Cond::and(
            Cond::equal(Expr::column('accessType'), Report::ACCESS_SHARED),
            Cond::in(
                Expr::column('id'),
                SelectBuilder::create()
                    ->from('ReportSharedTeam', 'sharedTeam')
                    ->select('sharedTeam.reportId')
                    ->where(['sharedTeam.teamId' => $teamIds, 'sharedTeam.deleted' => false])
                    ->build()
            ),
        );
    }
}
