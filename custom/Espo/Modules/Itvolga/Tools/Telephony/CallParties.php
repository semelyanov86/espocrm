<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Telephony;

use Espo\Core\Utils\Language;
use Espo\Entities\User;
use Espo\Modules\Itvolga\Tools\Telephony\Core\CallSnapshot;
use Espo\Modules\Itvolga\Tools\Telephony\Core\ParentChooser;
use Espo\ORM\Entity;
use Espo\ORM\EntityManager;

/**
 * Who a telephony Call belongs to and whom it concerns (D-165, D-167) — one rule for the live listener and the CDR
 * history of stage 07.2: the assignee extension, the user participants, the clients of the number with the parent,
 * the team, the name.
 */
class CallParties
{
    public function __construct(
        private EntityManager $entityManager,
        private TelephonyConfig $config,
        private ExtensionDirectory $directory,
        private Language $language,
    ) {}

    /**
     * Inbound: the desk phone that answered, else the first one that rang — the first of them that has a user —, else
     * the fallback extension. Outbound: the caller.
     *
     * @param list<string> $rung
     */
    public function assigneeExtension(string $direction, ?string $caller, ?string $answered, array $rung): string
    {
        if ($direction !== CallSnapshot::INBOUND) {
            return $caller ?? $this->config->fallbackExtension();
        }

        foreach (array_unique(array_filter([$answered, ...$rung])) as $extension) {
            if ($this->directory->userId((string) $extension) !== null) {
                return (string) $extension;
            }
        }

        return $this->config->fallbackExtension();
    }

    public function userId(?string $extension): ?string
    {
        return $this->directory->userId($extension);
    }

    /**
     * The exact matches of a ClientLookup result (a «possible» match is never linked): contacts with their accounts,
     * leads, and the parent — none when the lookup list was cut by its limits (it could look unambiguous).
     *
     * @param array{matches: list<array{entityType: string, id: string, possible: bool, accountId: ?string}>, complete: bool} $lookup
     * @return array{contacts: array<string, ?string>, leads: list<string>, parent: ?array{string, string}}
     */
    public function clients(array $lookup): array
    {
        $contacts = [];
        $accounts = [];
        $leads = [];

        foreach ($lookup['matches'] as $match) {
            if ($match['possible']) {
                continue;
            }

            match ($match['entityType']) {
                'Contact' => $contacts[$match['id']] = $match['accountId'],
                'Account' => $accounts[] = $match['id'],
                'Lead' => $leads[] = $match['id'],
                default => null,
            };
        }

        return [
            'contacts' => $contacts,
            'leads' => $leads,
            'parent' => $lookup['complete'] ? ParentChooser::choose($accounts, $contacts, $leads) : null,
        ];
    }

    public function name(string $direction, ?string $number): string
    {
        $label = $direction === CallSnapshot::INBOUND ? 'Incoming call' : 'Outgoing call';
        $number ??= $this->language->translateLabel('Hidden number', 'labels', 'Call');

        return mb_substr($this->language->translateLabel($label, 'labels', 'Call') . ' ' . $number, 0, 255);
    }

    public function defaultTeam(string $userId): ?string
    {
        $user = $this->entityManager->getRDBRepositoryByClass(User::class)->getById($userId);

        return $user?->getDefaultTeam()?->getId();
    }

    /**
     * Relates the users of the extensions once; a former automatic assignee who took no part leaves the participants.
     *
     * @param list<string> $extensions
     */
    public function relateParticipants(Entity $call, array $extensions, ?string $previousAssigneeId,
        ?string $assigneeId): void
    {
        $relation = $this->entityManager->getRDBRepository('Call')->getRelation($call, 'users');
        $participants = [];

        foreach ($extensions as $extension) {
            $userId = $this->directory->userId($extension);

            if ($userId !== null) {
                $participants[$userId] = true;
            }
        }

        foreach (array_keys($participants) as $userId) {
            if (!$relation->isRelatedById($userId)) {
                $relation->relateById($userId);
            }
        }

        if ($previousAssigneeId !== null && $previousAssigneeId !== $assigneeId
            && !isset($participants[$previousAssigneeId]) && $relation->isRelatedById($previousAssigneeId)) {
            $relation->unrelateById($previousAssigneeId);
        }
    }
}
