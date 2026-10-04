<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Access;

/**
 * Who reads a report (D-87). The access type of the report and the read level of the role on the scope `Report`
 * combine as follows (an administrator reads everything):
 *
 *   private — the owner only, whatever the level (a private report is never shown to a level `all` role);
 *   public  — any level but `no`;
 *   shared  — level own: the users of the list; level team: also the members of the teams of the list; level all: any.
 *
 * The owner always reads his report when the level is not `no`. Users and teams of the lists count only while the
 * report is shared. Editing and deleting are for the owner and administrators. The select filters of the scope
 * (Classes/Select/Report) implement the same rule in SQL; tests/reports/SharingPolicyTest checks the table.
 */
final class SharingPolicy
{
    public const LEVEL_ALL = 'all';
    public const LEVEL_TEAM = 'team';
    public const LEVEL_OWN = 'own';
    public const LEVEL_NO = 'no';

    public static function canRead(
        string $level,
        string $accessType,
        bool $isOwner,
        bool $isListedUser,
        bool $isListedTeamMember,
    ): bool {
        if ($level === self::LEVEL_NO || !in_array($level, [self::LEVEL_ALL, self::LEVEL_TEAM, self::LEVEL_OWN], true)) {
            return false;
        }

        if ($isOwner) {
            return true;
        }

        return match ($accessType) {
            'public' => true,
            'shared' => $level === self::LEVEL_ALL || $isListedUser ||
                ($level === self::LEVEL_TEAM && $isListedTeamMember),
            default => false,
        };
    }

    public static function canEdit(string $level, bool $isOwner): bool
    {
        return $isOwner && in_array($level, [self::LEVEL_ALL, self::LEVEL_TEAM, self::LEVEL_OWN], true);
    }
}
