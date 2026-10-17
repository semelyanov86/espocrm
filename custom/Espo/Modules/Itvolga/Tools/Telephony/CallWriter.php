<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Telephony;

use Espo\Core\ORM\Repository\Option\SaveOption;
use Espo\Modules\Itvolga\Tools\FinanceDocument\RowLock;
use Espo\Modules\Itvolga\Tools\Telephony\Core\CallSnapshot;
use Espo\Modules\Itvolga\Tools\Telephony\Core\OpenCall;
use Espo\Modules\Itvolga\Tools\Telephony\Core\RecordingPath;
use Espo\ORM\Entity;
use Espo\ORM\EntityManager;
use Espo\ORM\Query\DeleteBuilder;
use Espo\ORM\Query\SelectBuilder;
use Espo\ORM\Query\UpdateBuilder;

/**
 * Writes the snapshots of the listener (D-166…D-168): one Call per Asterisk linkedid (unique cAsteriskLinkedId), the
 * call cards of the users and the state of click-to-call requests, in one short transaction per snapshot.
 *
 * - A Call deleted by an administrator is never created again (the key stays on the deleted row).
 * - Only the facts are written after creation (save option CallFacts::SAVE_OPTION, SILENT): the name, description,
 *   parent, contacts, leads and participants a user changed stay as they are.
 * - Assignee: inbound — the user of the desk phone that answered, else of the first phone that rang that has a user,
 *   else of the fallback extension; outbound — the caller. While the call is live the assignee follows the call
 *   (fallback → the phone that rang → the one that answered), the team with it.
 * - Participants (users): every user whose phone rang or who called, added once; a former automatic assignee who took
 *   no part (the fallback user before a phone rang) leaves them — the phones that rang before a listener restart come
 *   back from the call cards, so they stay.
 */
class CallWriter
{
    private const SAVE_OPTIONS = [
        SaveOption::SILENT => true,
        SaveOption::NO_NOTIFICATIONS => true,
        CallFacts::SAVE_OPTION => true,
    ];

    /** @var array<string, array{matches: list<array{entityType: string, id: string, possible: bool, accountId: ?string}>, complete: bool}> */
    private array $matches = [];

    public function __construct(
        private EntityManager $entityManager,
        private TelephonyConfig $config,
        private ClientLookup $clientLookup,
        private ExtensionDirectory $directory,
        private RowLock $rowLock,
        private CallParties $parties,
        private RecordingFiles $files,
    ) {}

    public function apply(CallSnapshot $snapshot, float $now): void
    {
        $this->entityManager->getTransactionManager()->run(function () use ($snapshot, $now) {
            $intent = $snapshot->intentId !== null
                ? $this->entityManager->getEntityById('TelephonyCallIntent', $snapshot->intentId)
                : null;

            $call = $snapshot->persist ? $this->writeCall($snapshot, $intent, $now) : null;
            $this->writeCards($snapshot, $call, $intent);

            if ($intent) {
                $this->writeIntent($snapshot, $intent, $call);
            }
        });

        if ($snapshot->final) {
            unset($this->matches[$snapshot->linkedId]);
        }
    }

    /**
     * Calls the CRM stored as still in progress (the input of the reconciliation).
     *
     * @return list<OpenCall>
     */
    public function openCalls(): array
    {
        $calls = $this->entityManager->getRDBRepository('Call')
            ->select(['id', 'cAsteriskLinkedId', 'direction', 'cClickToCall', 'cPhoneNumber', 'cIncomingLine',
                'dateStart', 'dateEnd', 'cAnsweredAt', 'cExtension'])
            ->where(['cAsteriskLinkedId!=' => null, 'cLiveState' => [CallSnapshot::RINGING, CallSnapshot::TALKING]])
            ->find();

        $calls = iterator_to_array($calls, false);
        $cards = $this->storedCards(array_map(static fn (Entity $call) => (string) $call->get('cAsteriskLinkedId'), $calls));
        $out = [];

        foreach ($calls as $call) {
            $linkedId = (string) $call->get('cAsteriskLinkedId');
            $number = (string) $call->get('cPhoneNumber');
            $start = self::time($call->get('dateStart')) ?? 0.0;
            $out[] = new OpenCall(
                linkedId: $linkedId,
                direction: $call->get('direction') === CallSnapshot::INBOUND ? CallSnapshot::INBOUND : CallSnapshot::OUTBOUND,
                viaCrm: (bool) $call->get('cClickToCall'),
                number: str_starts_with($number, '+') ? $number : null,
                numberRaw: $number !== '' ? $number : null,
                line: $call->get('cIncomingLine'),
                startedAt: $start,
                answeredAt: self::time($call->get('cAnsweredAt')),
                lastSeenAt: self::time($call->get('dateEnd')) ?? $start,
                extension: $call->get('cExtension'),
                rungExtensions: $cards[$linkedId]['rung'] ?? [],
                answeredExtension: $cards[$linkedId]['answered'] ?? null,
            );
        }

        return $out;
    }

    /**
     * Who rang and who answered, as the call cards of the users recorded it (oldest card first).
     *
     * @param list<string> $linkedIds
     * @return array<string, array{rung: list<string>, answered: ?string}>
     */
    private function storedCards(array $linkedIds): array
    {
        if ($linkedIds === []) {
            return [];
        }

        $out = [];
        $cards = $this->entityManager->getRDBRepository('TelephonyCard')
            ->select(['linkedId', 'extension', 'state', 'direction'])
            ->where(['linkedId' => $linkedIds, 'direction' => CallSnapshot::INBOUND])
            ->order('createdAt')
            ->find();

        foreach ($cards as $card) {
            $linkedId = (string) $card->get('linkedId');
            $extension = (string) $card->get('extension');
            $out[$linkedId] ??= ['rung' => [], 'answered' => null];

            if ($extension !== '' && !in_array($extension, $out[$linkedId]['rung'], true)) {
                $out[$linkedId]['rung'][] = $extension;
            }

            if (in_array($card->get('state'), [CallSnapshot::CARD_TALKING, CallSnapshot::CARD_ENDED], true)) {
                $out[$linkedId]['answered'] = $extension;
            }
        }

        return $out;
    }

    /**
     * The calls in progress were seen alive now: dateEnd of a live call is its «last seen» time, so a call that ends
     * while the listener is away keeps a nearly right end (a direct update: no hooks, nothing else changes).
     *
     * @param list<string> $linkedIds
     */
    public function touch(array $linkedIds, float $now): void
    {
        if ($linkedIds === []) {
            return;
        }

        $this->entityManager->getQueryExecutor()->execute(
            UpdateBuilder::create()
                ->in('Call')
                ->set(['dateEnd' => self::date($now)])
                ->where([
                    'cAsteriskLinkedId' => $linkedIds,
                    'cLiveState' => [CallSnapshot::RINGING, CallSnapshot::TALKING],
                    'deleted' => false,
                ])
                ->build()
        );
    }

    /**
     * After a reconciliation: the cards still active and the click-to-call requests still queued of calls that are
     * neither on the PBX nor in the tracker's memory — a click-to-call that ended while the listener was away before
     * a Call was stored — are closed (the request: «unanswered»). Only rows untouched since `$before`: an Originate
     * whose channel is just being created keeps its card.
     *
     * @param list<string> $aliveLinkedIds
     */
    public function closeStale(array $aliveLinkedIds, float $before): void
    {
        $this->entityManager->getTransactionManager()->run(function () use ($aliveLinkedIds, $before) {
            $where = [
                'state' => [CallSnapshot::CARD_RINGING, CallSnapshot::CARD_DIALING, CallSnapshot::CARD_TALKING],
                'modifiedAt<' => self::date($before),
            ];

            if ($aliveLinkedIds !== []) {
                $where['linkedId!='] = $aliveLinkedIds;
            }

            foreach ($this->rowLock->query('TelephonyCard')->where($where)->find() as $card) {
                $card->set(['state' => CallSnapshot::CARD_CLOSED, 'endedAt' => $card->get('modifiedAt')]);
                $this->entityManager->saveEntity($card, [SaveOption::SILENT => true]);
            }

            $prefix = $this->config->trackerSettings()->originatePrefix;
            $intents = $this->rowLock->query('TelephonyCallIntent')
                ->where(['status' => 'queued', 'modifiedAt<' => self::date($before)])
                ->find();

            foreach ($intents as $intent) {
                if (!in_array($prefix . $intent->getId(), $aliveLinkedIds, true)) {
                    $intent->set('status', 'unanswered');
                    $this->entityManager->saveEntity($intent, [SaveOption::SILENT => true]);
                }
            }
        });
    }

    /**
     * Removes the call cards and click-to-call requests nobody needs any more.
     */
    public function purge(float $now): void
    {
        $executor = $this->entityManager->getQueryExecutor();

        foreach (['TelephonyCard' => 86400, 'TelephonyCallIntent' => 30 * 86400] as $entityType => $age) {
            $executor->execute(
                DeleteBuilder::create()
                    ->from($entityType)
                    ->where(['modifiedAt<' => self::date($now - $age)])
                    ->build()
            );
        }
    }

    // --- Call ------------------------------------------------------------------------------------------------------

    private function writeCall(CallSnapshot $s, ?Entity $intent, float $now): ?Entity
    {
        $key = ['cAsteriskLinkedId' => $s->linkedId];
        $this->rowLock->lockWithDeleted('Call', $key);

        $row = $this->entityManager->getQueryExecutor()->execute(
            SelectBuilder::create()->from('Call')->select(['id', 'deleted'])->where($key)->withDeleted()->build()
        )->fetch();

        if ($row && $row['deleted']) {
            return null;
        }

        $call = $row ? $this->rowLock->one('Call', (string) $row['id']) : $this->entityManager->getNewEntity('Call');

        if (!$call) {
            return null;
        }

        $isNew = !$row;
        $assigneeExtension = $this->parties->assigneeExtension($s->direction, $s->assigneeExtension,
            $s->answeredExtension, $s->rungExtensions);
        $assigneeId = $this->directory->userId($assigneeExtension);
        $previousAssigneeId = $isNew ? null : $call->get('assignedUserId');

        if ($isNew) {
            $this->initCall($call, $s, $intent);
        }

        $recording = $s->recordingFile !== null
            ? RecordingPath::relative($this->config->asteriskMonitorDir(), $s->recordingFile)
            : null;

        $facts = [
            'status' => $s->status(),
            'direction' => $s->direction,
            'dateStart' => self::date($s->startedAt),
            'dateEnd' => self::date($s->final ? (float) $s->endedAt : max($now, $s->startedAt)),
            'cPhoneNumber' => $s->number ?? $s->numberRaw,
            'cIncomingLine' => $s->line,
            'cCallStatusRaw' => $s->rawStatus,
            'cBillDuration' => $s->talkSeconds($now),
            'cAnsweredAt' => $s->answeredAt !== null ? self::date($s->answeredAt) : null,
            'cExtension' => $assigneeExtension,
            'cLiveState' => $s->liveState,
            'cClickToCall' => $s->viaCrm,
            'cCdrSource' => null, // the live integration owns the call (a CDR history import never touches it again)
        ];

        if ($recording !== null) {
            $facts['cRecordingPath'] = $recording;
        }

        $facts['cRecording'] = $s->final && $this->files->path($recording ?? $call->get('cRecordingPath')) !== null;

        $call->setMultiple($facts);
        $live = !$isNew && in_array($call->getFetched('cLiveState'), [CallSnapshot::RINGING, CallSnapshot::TALKING], true);

        if ($assigneeId !== null && ($isNew || ($live && $assigneeId !== $previousAssigneeId))) {
            $call->set('assignedUserId', $assigneeId);
            $team = $this->parties->defaultTeam($assigneeId);
            $call->set('teamsIds', $team !== null ? [$team] : []);
        }

        if ($isNew || $this->changed($call)) {
            $this->entityManager->saveEntity($call, self::SAVE_OPTIONS);
        }

        $this->parties->relateParticipants($call, $s->participantExtensions, $previousAssigneeId, $assigneeId);

        return $call;
    }

    private function initCall(Entity $call, CallSnapshot $s, ?Entity $intent): void
    {
        ['contacts' => $contacts, 'leads' => $leads, 'parent' => $parent] = $this->parties->clients($this->lookupOf($s));
        $intentParent = $this->intentParent($intent);

        if ($intentParent !== null) {
            $parent = $intentParent;

            if ($parent[0] === 'Contact') {
                $contacts[$parent[1]] ??= null;
            } elseif ($parent[0] === 'Lead' && !in_array($parent[1], $leads, true)) {
                $leads[] = $parent[1];
            }
        }

        $call->setMultiple([
            'name' => $this->parties->name($s->direction, $s->number ?? $s->numberRaw),
            'cAsteriskLinkedId' => $s->linkedId,
            'contactsIds' => array_keys($contacts),
            'leadsIds' => $leads,
            'parentType' => $parent[0] ?? null,
            'parentId' => $parent[1] ?? null,
        ]);
    }

    /**
     * @return ?array{string, string}
     */
    private function intentParent(?Entity $intent): ?array
    {
        $type = $intent?->get('parentType');
        $id = $intent?->get('parentId');

        if (!$type || !$id || !in_array($type, ['Account', 'Contact', 'Lead', 'Opportunity', 'Case', 'Invoice'], true)) {
            return null;
        }

        return $this->entityManager->getEntityById($type, $id) ? [$type, $id] : null;
    }

    private function changed(Entity $call): bool
    {
        foreach ([...CallFacts::ATTRIBUTES, 'assignedUserId', 'teamsIds'] as $attribute) {
            if ($call->has($attribute) && $call->isAttributeChanged($attribute)) {
                return true;
            }
        }

        return false;
    }

    // --- cards and intents -----------------------------------------------------------------------------------------

    private function writeCards(CallSnapshot $s, ?Entity $call, ?Entity $intent): void
    {
        $existing = [];

        foreach ($this->rowLock->query('TelephonyCard')->where(['linkedId' => $s->linkedId])->find() as $card) {
            $existing[(string) $card->get('userId')] = $card;
        }

        $matches = null;
        $seen = [];

        foreach ($s->cards as $extension => $state) {
            $userId = $this->directory->userId((string) $extension);

            if ($userId === null || isset($seen[$userId])) {
                continue;
            }

            $seen[$userId] = true;
            $card = $existing[$userId] ?? null;

            if (!$card) {
                $matches ??= $this->cardMatches($s, $intent);
                $card = $this->entityManager->getNewEntity('TelephonyCard');
                $card->setMultiple(['linkedId' => $s->linkedId, 'userId' => $userId, 'matches' => $matches,
                    'dismissed' => false]);
            } elseif ($call !== null && !$card->get('callId')) {
                // A click-to-call card made before the number was dialled: now the clients of the number are known.
                $matches ??= $this->cardMatches($s, $intent);
                $card->set('matches', $matches);
            }

            $this->fillCard($card, $s, (string) $extension, $state, $call, $intent);
        }

        foreach ($existing as $userId => $card) {
            if (!isset($seen[$userId]) && $card->get('state') !== CallSnapshot::CARD_CLOSED) {
                $state = $s->final && $card->get('state') === CallSnapshot::CARD_TALKING
                    ? CallSnapshot::CARD_ENDED : CallSnapshot::CARD_CLOSED;
                $this->fillCard($card, $s, (string) $card->get('extension'), $state, $call, $intent);
            }
        }
    }

    private function fillCard(Entity $card, CallSnapshot $s, string $extension, string $state, ?Entity $call,
        ?Entity $intent): void
    {
        $previous = $card->isNew() ? null : $card->get('state');

        $card->setMultiple([
            'extension' => $extension,
            'direction' => $s->direction,
            'state' => $state,
            'number' => $s->number ?? $s->numberRaw ?? $intent?->get('number'),
            'viaCrm' => $s->viaCrm,
            'callId' => $call?->getId() ?? $card->get('callId'),
            'startedAt' => self::date($s->startedAt),
            'answeredAt' => $s->answeredAt !== null ? self::date($s->answeredAt) : null,
            'endedAt' => $s->endedAt !== null ? self::date($s->endedAt) : null,
        ]);

        $active = [CallSnapshot::CARD_RINGING, CallSnapshot::CARD_DIALING, CallSnapshot::CARD_TALKING];

        if ($previous !== null && $previous !== $state && in_array($state, $active, true)) {
            $card->set('dismissed', false);
        }

        if ($card->isNew() || $card->isAttributeChanged('state') || $card->isAttributeChanged('callId')
            || $card->isAttributeChanged('matches')
            || $card->isAttributeChanged('number') || $card->isAttributeChanged('answeredAt')
            || $card->isAttributeChanged('endedAt') || $card->isAttributeChanged('dismissed')) {
            $this->entityManager->saveEntity($card, [SaveOption::SILENT => true]);
        }
    }

    /**
     * Clients shown on the cards: the record a click-to-call started from, then the matches of the number.
     *
     * @return list<array{entityType: string, id: string, possible: bool}>
     */
    private function cardMatches(CallSnapshot $s, ?Entity $intent): array
    {
        $out = [];
        $parent = $this->intentParent($intent);

        if ($parent !== null && in_array($parent[0], ClientLookup::TYPES, true)) {
            $out[$parent[0] . ':' . $parent[1]] = ['entityType' => $parent[0], 'id' => $parent[1], 'possible' => false];
        }

        foreach ($this->lookupOf($s)['matches'] as $m) {
            $out[$m['entityType'] . ':' . $m['id']] ??= ['entityType' => $m['entityType'], 'id' => $m['id'],
                'possible' => $m['possible']];
        }

        return array_values($out);
    }

    /**
     * @return array{matches: list<array{entityType: string, id: string, possible: bool, accountId: ?string}>, complete: bool}
     */
    private function lookupOf(CallSnapshot $s): array
    {
        if ($s->number === null) {
            return ['matches' => [], 'complete' => true];
        }

        return $this->matches[$s->linkedId] ??= $this->clientLookup->find(
            $s->number,
            $this->config->trackerSettings()->localAreaCode,
        );
    }

    private function writeIntent(CallSnapshot $s, Entity $intent, ?Entity $call): void
    {
        $status = match (true) {
            $call !== null => 'observed',
            $s->final => 'unanswered',
            default => null,
        };

        if ($status !== null && $intent->get('status') !== $status && $intent->get('status') !== 'observed') {
            $intent->set('status', $status);
            $this->entityManager->saveEntity($intent, [SaveOption::SILENT => true]);
        }
    }

    // --- time ------------------------------------------------------------------------------------------------------

    public static function date(float $time): string
    {
        return gmdate('Y-m-d H:i:s', (int) floor($time));
    }

    private static function time(mixed $value): ?float
    {
        if (!is_string($value) || $value === '') {
            return null;
        }

        $time = strtotime($value . ' UTC');

        return $time === false ? null : (float) $time;
    }
}
