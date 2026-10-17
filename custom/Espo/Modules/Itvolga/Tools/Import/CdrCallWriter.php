<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Import;

use Espo\Core\ORM\Repository\Option\SaveOption;
use Espo\Modules\Itvolga\Tools\FinanceDocument\RowLock;
use Espo\Modules\Itvolga\Tools\Telephony\CallFacts;
use Espo\Modules\Itvolga\Tools\Telephony\CallParties;
use Espo\Modules\Itvolga\Tools\Telephony\ClientLookup;
use Espo\Modules\Itvolga\Tools\Telephony\Core\HistoryCall;
use Espo\Modules\Itvolga\Tools\Telephony\Core\PhoneNumbers;
use Espo\Modules\Itvolga\Tools\Telephony\Core\TrackerSettings;
use Espo\Modules\Itvolga\Tools\Telephony\RecordingFiles;
use Espo\Modules\Itvolga\Tools\Telephony\TelephonyConfig;
use Espo\ORM\Entity;
use Espo\ORM\EntityManager;
use Espo\ORM\Query\SelectBuilder;
use InvalidArgumentException;
use stdClass;

/**
 * Writer of the Asterisk CDR history (stage 07.2, D-176): one Call per Asterisk linkedid, the key the live
 * integration uses too (`cAsteriskLinkedId`, D-164) — the only import path that saves with the integration's option
 * (CallFacts::SAVE_OPTION).
 *
 * - A Call deleted by an administrator is never created again (`deleted_in_target`); a Call the live integration wrote
 *   (no `cCdrSource`) is never touched (`live_call`).
 * - A new Call gets everything the live integration would give it (CallParties): the assignee and the team, the users
 *   whose phones rang, the exact clients of the number and the parent, the name. A Call of an earlier run gets only
 *   the facts of the history (HistoryCall::facts) and its recording: what users changed stays (owner's answer
 *   2026-10-17).
 * - The recording is attached only when the file inside the recordings root has the size and sha256 of the sealed
 *   snapshot inventory and no other Call stores its path (RecordingFiles).
 *
 * Saves: SILENT + NO_NOTIFICATIONS + the integration's option. Answers carry statuses, ids, attribute names and closed
 * codes only.
 */
class CdrCallWriter
{
    private const SAVE_OPTIONS = [
        SaveOption::SILENT => true,
        SaveOption::NO_NOTIFICATIONS => true,
        CallFacts::SAVE_OPTION => true,
    ];

    public function __construct(
        private EntityManager $entityManager,
        private TelephonyConfig $config,
        private RowLock $rowLock,
        private CallParties $parties,
        private ClientLookup $clientLookup,
        private RecordingFiles $files,
    ) {}

    /**
     * The classification rules of the installation (the same configuration as the listener's), whether the
     * integration is on, and the recordings root — no secrets.
     *
     * @return array<string, mixed>
     */
    public function rules(): array
    {
        $settings = $this->settings();

        return [
            'rules' => [
                'extensionPattern' => $settings->extensionPattern,
                'trunks' => (object) $settings->trunks,
                'inboundContexts' => $settings->inboundContexts,
                'originatePrefix' => $settings->originatePrefix,
                'localAreaCode' => $settings->localAreaCode,
            ],
            'enabled' => $this->config->isEnabled(),
            'recordingRoot' => $this->config->recordingRoot(),
        ];
    }

    /**
     * Keys of the target's Asterisk calls by owner: the history import, the live integration, deleted.
     *
     * @return array{history: list<string>, live: list<string>, deleted: list<string>}
     */
    public function inventory(): array
    {
        $query = SelectBuilder::create()
            ->from('Call')
            ->select(['cAsteriskLinkedId', 'cCdrSource', 'deleted'])
            ->where(['cAsteriskLinkedId!=' => null])
            ->withDeleted()
            ->build();
        $out = ['history' => [], 'live' => [], 'deleted' => []];

        foreach ($this->entityManager->getQueryExecutor()->execute($query) as $row) {
            $owner = $row['deleted'] ? 'deleted' : ((string) $row['cCdrSource'] !== '' ? 'history' : 'live');
            $out[$owner][] = (string) $row['cAsteriskLinkedId'];
        }

        return $out;
    }

    /**
     * @return array<string, mixed>
     * @throws ImportError
     */
    public function write(stdClass $op): array
    {
        $call = $this->call($op);
        $key = [CallFacts::KEY => $call->linkedId];
        $this->rowLock->lockWithDeleted('Call', $key);
        $row = $this->stored($call->linkedId);

        if ($row !== null && ($skip = $this->skip($row))) {
            return $skip;
        }

        $entity = $row !== null ? $this->rowLock->one('Call', (string) $row['id']) : $this->entityManager->getNewEntity('Call');

        if (!$entity) {
            throw new ImportError('call_missing');
        }

        $isNew = $row === null;
        [$path, $playable, $recording] = $this->recording($call, $isNew ? null : $entity->getId(),
            $isNew ? null : $entity->get('cRecordingPath'));
        $assignee = $this->assigneeExtension($call);

        if ($isNew) {
            $this->initialize($entity, $call, $assignee);
        }

        $entity->setMultiple($call->facts($this->settings()->localAreaCode, $path, $playable, $assignee));
        $changed = $isNew ? [] : $this->changed($entity);

        if ($isNew || $changed) {
            $this->entityManager->saveEntity($entity, self::SAVE_OPTIONS);
        }

        if ($isNew) {
            $this->parties->relateParticipants($entity, $call->participantExtensions(), null,
                $this->parties->userId($assignee));
        }

        return ['status' => $isNew ? 'created' : ($changed ? 'updated' : 'unchanged'), 'id' => $entity->getId(),
            'changed' => $changed, 'recording' => $recording] + ($isNew ? ['assignee' => $this->assigneeKind($call,
            $assignee)] : []);
    }

    /**
     * The check pass: the same decision, nothing written.
     *
     * @return array<string, mixed>
     * @throws ImportError
     */
    public function check(stdClass $op): array
    {
        $call = $this->call($op);
        $row = $this->stored($call->linkedId);

        if ($row === null) {
            return ['status' => 'missing'];
        }

        if ($skip = $this->skip($row)) {
            return $skip;
        }

        $entity = $this->entityManager->getEntityById('Call', (string) $row['id']) ?? throw new ImportError('call_missing');
        [$path, $playable, $recording] = $this->recording($call, $entity->getId(), $entity->get('cRecordingPath'));
        $entity->setMultiple($call->facts($this->settings()->localAreaCode, $path, $playable,
            $this->assigneeExtension($call)));
        $differs = $this->changed($entity);

        return ['status' => $differs ? 'differs' : 'equal', 'id' => $entity->getId(), 'differs' => $differs,
            'recording' => $recording];
    }

    /**
     * The extension the call belongs to (CallParties, D-165) — a fact of every run (cExtension); the user it maps to
     * becomes the assignee only when the Call is created.
     */
    private function assigneeExtension(HistoryCall $call): string
    {
        return $this->parties->assigneeExtension($call->direction, $call->callerExtension, $call->answeredExtension,
            $call->rungExtensions);
    }

    /**
     * Set once, when the Call is created (owner's answer 2026-10-17: a re-run writes only the facts).
     */
    private function initialize(Entity $entity, HistoryCall $call, string $assignee): void
    {
        $assigneeId = $this->parties->userId($assignee);
        $area = $this->settings()->localAreaCode;
        $number = PhoneNumbers::canonical($call->numberRaw, $area);
        ['contacts' => $contacts, 'leads' => $leads, 'parent' => $parent] =
            $this->parties->clients($this->clientLookup->find($number, $area));

        $entity->setMultiple([
            'name' => $this->parties->name($call->direction, $number ?? $call->numberRaw),
            CallFacts::KEY => $call->linkedId,
            'contactsIds' => array_keys($contacts),
            'leadsIds' => $leads,
            'parentType' => $parent[0] ?? null,
            'parentId' => $parent[1] ?? null,
        ]);

        if ($assigneeId !== null) {
            $team = $this->parties->defaultTeam($assigneeId);
            $entity->set(['assignedUserId' => $assigneeId, 'teamsIds' => $team !== null ? [$team] : []]);
        }
    }

    /**
     * The path the call claims, whether it is played, the closed code. A path the call already stores that another
     * call stores too is never given up (re-review 2026-10-17): whatever the run brings — no recording, a failed check,
     * another path — clearing it would leave the other call its sole claimant and its playback open.
     *
     * @return array{?string, bool, string}
     */
    private function recording(HistoryCall $call, ?string $callId, ?string $stored): array
    {
        [$path, $playable, $code] = $this->candidate($call, $callId);

        if ($callId !== null && (string) $stored !== '' && $stored !== $path && $this->files->isShared($stored, $callId)) {
            return [$stored, false, 'claim_kept'];
        }

        return [$path, $playable, $code];
    }

    /**
     * @return array{?string, bool, string}
     */
    private function candidate(HistoryCall $call, ?string $callId): array
    {
        if ($call->recording === null) {
            return [null, false, 'none'];
        }

        ['path' => $path, 'size' => $size, 'sha256' => $sha256] = $call->recording;
        $code = $this->files->verify($path, $size, $sha256);

        if ($code !== RecordingFiles::OK) {
            return [null, false, $code];
        }

        if ($this->files->isShared($path, $callId)) {
            // another call stores the path: the claim stays (it keeps blocking the other call's playback too), never
            // played — clearing it would hand the file to the other call (review 2026-10-17)
            return [$path, false, 'claimed_in_target'];
        }

        return [$path, true, 'attached'];
    }

    /**
     * @param array<string, mixed> $row
     * @return ?array<string, mixed>
     */
    private function skip(array $row): ?array
    {
        if ($row['deleted']) {
            return ['status' => 'deleted_in_target', 'id' => (string) $row['id']];
        }

        if ((string) $row['cCdrSource'] === '') {
            return ['status' => 'live_call', 'id' => (string) $row['id']];
        }

        return null;
    }

    /**
     * @return ?array<string, mixed>
     */
    private function stored(string $linkedId): ?array
    {
        $row = $this->entityManager->getQueryExecutor()->execute(
            SelectBuilder::create()
                ->from('Call')
                ->select(['id', 'deleted', 'cCdrSource'])
                ->where([CallFacts::KEY => $linkedId])
                ->withDeleted()
                ->build()
        )->fetch();

        return $row ?: null;
    }

    /**
     * @return list<string> names of the facts that differ from the stored ones
     */
    private function changed(Entity $entity): array
    {
        return array_values(array_filter(HistoryCall::FACTS,
            static fn (string $attribute) => $entity->isAttributeChanged($attribute)));
    }

    private function assigneeKind(HistoryCall $call, string $assignee): string
    {
        return match (true) {
            $this->parties->userId($assignee) === null => 'none',
            $assignee === $call->answeredExtension => 'answered',
            $assignee === $call->callerExtension => 'caller',
            in_array($assignee, $call->rungExtensions, true) => 'rung',
            default => 'fallback',
        };
    }

    /**
     * @throws ImportError
     */
    private function call(stdClass $op): HistoryCall
    {
        try {
            return HistoryCall::fromOperation($op, $this->settings());
        } catch (InvalidArgumentException $e) {
            throw new ImportError('invalid', [$e->getMessage()]);
        }
    }

    /**
     * @throws ImportError
     */
    private function settings(): TrackerSettings
    {
        try {
            return $this->config->trackerSettings();
        } catch (InvalidArgumentException) {
            throw new ImportError('telephony_rules');
        }
    }
}
