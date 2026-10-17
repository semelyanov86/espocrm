<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Telephony\Core;

use Espo\Modules\Itvolga\Tools\Telephony\Core\Ami\Message;

/**
 * Follows the AMI channel events of the PBX and turns every call (all channels of one Asterisk linkedid) into
 * CallSnapshot values (stage 07.1, D-166). Deterministic: the time of every event is passed in.
 *
 * Classification is decided by the first channel of the linkedid (Uniqueid = Linkedid), by endpoint name:
 * - an inbound trunk in an inbound context → an external inbound call, stored at once (even a hang-up in the IVR);
 * - a desk phone → pending; it becomes an external outbound call when it dials a trunk, an internal one when it dials
 *   a desk phone first (internal calls, voicemail, the conference never dial a trunk and are never stored);
 * - a desk phone whose Uniqueid carries the CRM prefix → click-to-call (Originate ChannelId): a pending call with a
 *   card for the caller («pick up the phone»), stored once it dials the trunk;
 * - anything else (the German trainer's trunk, Local channels) → ignored.
 * The IVR answers inbound calls itself: only a dialled leg answered (DialEnd ANSWER) is a human answer.
 *
 * Snapshots are emitted only when they change; the last one of a call is final.
 */
final class CallTracker
{
    private const VAR_RECORDING = 'MIXMONITOR_FILENAME';
    private const SWEEP_AFTER = 3600.0;

    /** @var array<string, TrackedCall> */
    private array $calls = [];
    /** @var array<string, string> linkedid => fingerprint of the last emitted snapshot */
    private array $emitted = [];

    public function __construct(private readonly TrackerSettings $settings) {}

    /**
     * @return list<CallSnapshot>
     */
    public function accept(Message $message, float $now): array
    {
        return match ($message->event()) {
            'Newchannel' => $this->onNewChannel($message, $now),
            'Newstate' => $this->onNewState($message, $now),
            'DialBegin' => $this->onDialBegin($message, $now),
            'DialEnd' => $this->onDialEnd($message, $now),
            'VarSet' => $this->onVarSet($message, $now),
            'Hangup' => $this->onHangup($message, $now),
            default => [],
        };
    }

    /**
     * After (re)connecting: compares what the listener knows — calls it tracks and calls the CRM stored as live — with
     * the channels Asterisk has now (CoreShowChannel items). A known call without channels ended while nobody listened:
     * it is closed as lost at the last time it was seen. A live call is adopted with its current legs. A live call
     * nobody knew is classified from its first channel, with times from the channel durations (approximate).
     *
     * The periodic check of a healthy session ($staleAfter > 0, $adoptUnknown false) closes only calls silent for that
     * long — the events of a call ending right now may still be on their way.
     *
     * @param list<Message> $channelList CoreShowChannel items
     * @param list<OpenCall> $open
     * @return list<CallSnapshot>
     */
    public function reconcile(array $channelList, array $open, float $now, float $staleAfter = 0.0,
        bool $adoptUnknown = true): array
    {
        $groups = [];

        foreach ($channelList as $item) {
            $linked = $item->get('Linkedid');
            $uid = $item->get('Uniqueid');

            if ($linked && $uid && $item->get('Channel')) {
                $groups[$linked][$uid] = $item;
            }
        }

        $out = [];

        foreach ($this->calls as $linked => $call) {
            if (!isset($groups[$linked]) && $now - $call->lastEventAt >= $staleAfter) {
                $call->lost = true;
                $out = [...$out, ...$this->finish($call, $call->lastEventAt)];
            }
        }

        foreach ($open as $stored) {
            if (isset($this->calls[$stored->linkedId])) {
                continue;
            }

            $call = $this->fromStored($stored);

            if (!isset($groups[$stored->linkedId])) {
                $call->lost = true;
                $this->calls[$call->linkedId] = $call;
                $out = [...$out, ...$this->finish($call, $stored->lastSeenAt)];

                continue;
            }

            $this->calls[$call->linkedId] = $call;
            $this->adoptChannels($call, $groups[$stored->linkedId], $now);
            $out = [...$out, ...$this->emit($call)];
        }

        foreach ($groups as $linked => $items) {
            if (!$adoptUnknown || isset($this->calls[$linked])) {
                continue;
            }

            $call = $this->fromChannels((string) $linked, $items, $now);
            $this->calls[$call->linkedId] = $call;
            $this->adoptChannels($call, $items, $now);
            $out = [...$out, ...$this->emit($call)];
        }

        return $out;
    }

    /**
     * Forgets calls that were never stored and saw no event for an hour (a lost Hangup of an internal call).
     */
    public function sweep(float $now): void
    {
        foreach ($this->calls as $linked => $call) {
            if (!$call->isPersisted() && $now - $call->lastEventAt > self::SWEEP_AFTER) {
                unset($this->calls[$linked], $this->emitted[$linked]);
            }
        }
    }

    /**
     * Linkedids of the stored calls in progress.
     *
     * @return list<string>
     */
    public function liveStoredIds(): array
    {
        return array_values(array_map(
            static fn (TrackedCall $call) => $call->linkedId,
            array_filter($this->calls, static fn (TrackedCall $call) => $call->isPersisted()),
        ));
    }

    public function count(): int
    {
        return count($this->calls);
    }

    /**
     * Linkedids of every call in memory, stored or not (a click-to-call before the number is dialled).
     *
     * @return list<string>
     */
    public function trackedIds(): array
    {
        return array_map('strval', array_keys($this->calls));
    }

    // --- events --------------------------------------------------------------------------------------------------

    /**
     * @return list<CallSnapshot>
     */
    private function onNewChannel(Message $m, float $now): array
    {
        $uid = $m->get('Uniqueid');
        $linked = $m->get('Linkedid');
        $name = $m->get('Channel');

        if (!$uid || !$linked || !$name) {
            return [];
        }

        $call = $this->calls[$linked] ?? null;

        if ($call === null) {
            if ($uid !== $linked) {
                return [];
            }

            $call = $this->classify($m, $now);
            $this->calls[$linked] = $call;
        }

        $call->channels[$uid] = ['name' => $name, 'endpoint' => $this->settings->endpointOf($name),
            'state' => (string) $m->get('ChannelStateDesc')];
        $call->lastEventAt = $now;

        return $this->emit($call);
    }

    /**
     * @return list<CallSnapshot>
     */
    private function onNewState(Message $m, float $now): array
    {
        [$call, $uid] = $this->callOf($m);

        if ($call === null || !isset($call->channels[$uid])) {
            return [];
        }

        $state = (string) $m->get('ChannelStateDesc');
        $call->channels[$uid]['state'] = $state;
        $call->lastEventAt = $now;
        $endpoint = $call->channels[$uid]['endpoint'];

        if ($call->kind === TrackedCall::INBOUND && $state === 'Ringing' && $uid !== $call->rootUid
            && $this->settings->isExtension($endpoint)) {
            $call->legs[$uid] ??= self::leg($endpoint, false);

            if ($call->legs[$uid]['ringingAt'] === null) {
                $call->legs[$uid]['ringingAt'] = $now;
            }
        }

        return $this->emit($call);
    }

    /**
     * @return list<CallSnapshot>
     */
    private function onDialBegin(Message $m, float $now): array
    {
        $destUid = $m->get('DestUniqueid');
        $linked = $m->get('DestLinkedid') ?: $m->get('Linkedid');
        $call = $linked ? ($this->calls[$linked] ?? null) : null;

        if ($call === null || !$destUid || in_array($call->kind, [TrackedCall::IGNORED, TrackedCall::INTERNAL], true)) {
            return [];
        }

        $call->lastEventAt = $now;
        $callerUid = $m->get('Uniqueid');

        if (!$callerUid) {
            // Originate rings the user's own desk phone first: not a dial of the call.
            return [];
        }

        $endpoint = $this->settings->endpointOf($m->get('DestChannel'));
        $isTrunk = $this->settings->isCrmTrunk($endpoint);
        $extension = $this->settings->isExtension($endpoint) ? $endpoint : null;

        if ($call->kind === TrackedCall::PENDING) {
            if ($isTrunk && $callerUid === $call->rootUid) {
                $call->kind = TrackedCall::OUTBOUND;
                $dialled = self::externalNumber(strstr((string) $m->get('DialString'), '@', true) ?: null);
                $call->numberRaw = $dialled;
                $call->number = PhoneNumbers::canonical($dialled, $this->settings->localAreaCode);
                $call->legs[$destUid] = self::leg(null, true);

                return $this->emit($call);
            }

            if ($extension !== null && !$call->viaCrm) {
                $call->kind = TrackedCall::INTERNAL;
            }

            return [];
        }

        if ($extension !== null || $isTrunk) {
            $call->legs[$destUid] ??= self::leg($extension, $isTrunk);
        }

        return $this->emit($call);
    }

    /**
     * @return list<CallSnapshot>
     */
    private function onDialEnd(Message $m, float $now): array
    {
        $destUid = $m->get('DestUniqueid');
        $linked = $m->get('DestLinkedid') ?: $m->get('Linkedid');
        $call = $linked ? ($this->calls[$linked] ?? null) : null;
        $callerUid = $m->get('Uniqueid');

        if ($call === null || !$destUid || !$callerUid || !isset($call->legs[$destUid])) {
            return [];
        }

        $call->lastEventAt = $now;
        $status = strtoupper((string) $m->get('DialStatus'));
        $leg = &$call->legs[$destUid];

        if ($leg['status'] !== null) {
            return [];
        }

        $leg['status'] = $status;
        $relevant = $call->kind === TrackedCall::INBOUND || $leg['trunk'];

        if ($relevant) {
            $call->lastDialStatus = $status;

            if ($status === 'ANSWER' && $call->answeredAt === null) {
                $call->answeredAt = $now;
                $call->answeredExtension = $call->kind === TrackedCall::INBOUND ? $leg['extension'] : null;
                $call->answeredPair = [$callerUid, $destUid];
            }
        }

        unset($leg);

        return $this->emit($call);
    }

    /**
     * @return list<CallSnapshot>
     */
    private function onVarSet(Message $m, float $now): array
    {
        if ($m->get('Variable') !== self::VAR_RECORDING) {
            return [];
        }

        [$call] = $this->callOf($m);
        $value = $m->get('Value');

        if ($call === null || !$value || in_array($call->kind, [TrackedCall::IGNORED, TrackedCall::INTERNAL], true)) {
            return [];
        }

        $call->lastEventAt = $now;
        $call->recordingFile ??= $value;

        return $this->emit($call);
    }

    /**
     * @return list<CallSnapshot>
     */
    private function onHangup(Message $m, float $now): array
    {
        [$call, $uid] = $this->callOf($m);

        if ($call === null || !isset($call->channels[$uid])) {
            return [];
        }

        unset($call->channels[$uid]);
        $call->lastEventAt = $now;

        if (isset($call->legs[$uid])) {
            $call->legs[$uid]['gone'] = true;
        }

        if ($call->answeredAt !== null && $call->talkEndedAt === null && in_array($uid, $call->answeredPair, true)) {
            $call->talkEndedAt = $now;
        }

        if ($call->channels === []) {
            return $this->finish($call, $now);
        }

        return $this->emit($call);
    }

    // --- state -----------------------------------------------------------------------------------------------------

    private function classify(Message $m, float $now): TrackedCall
    {
        $uid = (string) $m->get('Uniqueid');
        $call = new TrackedCall((string) $m->get('Linkedid'), $now);
        $call->rootUid = $uid;
        $endpoint = $this->settings->endpointOf($m->get('Channel'));

        if ($this->settings->trunkClass($endpoint) === TrackerSettings::INBOUND
            && $this->settings->isInboundContext($m->get('Context'))) {
            $call->kind = TrackedCall::INBOUND;
            $call->numberRaw = self::externalNumber($m->get('CallerIDNum'));
            $call->number = PhoneNumbers::canonical($call->numberRaw, $this->settings->localAreaCode);
            $call->line = self::externalNumber($m->get('Exten'));

            return $call;
        }

        if ($this->settings->isExtension($endpoint)) {
            $call->kind = TrackedCall::PENDING;
            $call->callerExtension = $endpoint;
            $prefix = $this->settings->originatePrefix;

            if (str_starts_with($uid, $prefix) && preg_match('/^[A-Za-z0-9]{1,40}$/', substr($uid, strlen($prefix)))) {
                $call->viaCrm = true;
                $call->intentId = substr($uid, strlen($prefix));
            }
        }

        return $call;
    }

    private function fromStored(OpenCall $stored): TrackedCall
    {
        $call = new TrackedCall($stored->linkedId, $stored->startedAt);
        $call->kind = $stored->direction === CallSnapshot::INBOUND ? TrackedCall::INBOUND : TrackedCall::OUTBOUND;
        $call->rootUid = $stored->linkedId;
        $call->viaCrm = $stored->viaCrm;
        $call->number = $stored->number;
        $call->numberRaw = $stored->numberRaw;
        $call->line = $stored->line;
        $call->answeredAt = $stored->answeredAt;
        $call->lastEventAt = $stored->lastSeenAt;

        if ($call->kind === TrackedCall::OUTBOUND) {
            $call->callerExtension = $stored->extension;
        } else {
            // The stored assignee may be the fallback user: only the call cards tell who rang and who answered.
            $call->knownAssignee = $stored->extension;
            $call->rungBefore = $stored->rungExtensions;
            $call->answeredExtension = $stored->answeredAt !== null ? $stored->answeredExtension : null;
        }

        return $call;
    }

    /**
     * @param array<string, Message> $items
     */
    private function fromChannels(string $linked, array $items, float $now): TrackedCall
    {
        $root = $items[$linked] ?? reset($items);
        $endpoint = $this->settings->endpointOf($root->get('Channel'));
        $call = new TrackedCall($linked, $now - self::seconds($root->get('Duration')));
        $call->rootUid = (string) $root->get('Uniqueid');
        $call->approximate = true;
        $call->lastEventAt = $now;
        $hasTrunk = false;

        foreach ($items as $uid => $item) {
            if ($uid !== $call->rootUid && $this->settings->isCrmTrunk($this->settings->endpointOf($item->get('Channel')))) {
                $hasTrunk = true;
            }
        }

        if ($this->settings->trunkClass($endpoint) === TrackerSettings::INBOUND) {
            $call->kind = TrackedCall::INBOUND;
            $call->numberRaw = self::externalNumber($root->get('CallerIDNum'));
            $call->number = PhoneNumbers::canonical($call->numberRaw, $this->settings->localAreaCode);
        } elseif ($this->settings->isExtension($endpoint)) {
            // As on the event path: a desk phone that dialled a desk phone (phones-local, even with a failover to a
            // mobile through a trunk) makes an internal call; an external one dials a trunk from phones-out, and its
            // Dial data names the number.
            $exten = (string) $root->get('Exten');
            $dialled = $this->dialledNumber($root);
            $call->callerExtension = $endpoint;
            $call->kind = match (true) {
                $this->settings->isExtension($exten) => TrackedCall::INTERNAL,
                $hasTrunk => TrackedCall::OUTBOUND,
                default => TrackedCall::PENDING,
            };

            if ($call->kind === TrackedCall::OUTBOUND) {
                $call->numberRaw = $dialled ?? self::externalNumber($exten);
                $call->number = PhoneNumbers::canonical($call->numberRaw, $this->settings->localAreaCode);
            }

            $prefix = $this->settings->originatePrefix;

            if (str_starts_with($call->rootUid, $prefix)) {
                $call->viaCrm = true;
                $call->intentId = substr($call->rootUid, strlen($prefix));
            }
        }

        return $call;
    }

    /**
     * Channels of a call found by CoreShowChannels: ringing desk phones of an inbound call become ringing legs, a
     * talking desk phone (Up) or an answered trunk the human answer, timed by the channel's duration.
     *
     * @param array<string, Message> $items
     */
    private function adoptChannels(TrackedCall $call, array $items, float $now): void
    {
        foreach ($items as $uid => $item) {
            $uid = (string) $uid;
            $endpoint = $this->settings->endpointOf($item->get('Channel'));
            $state = (string) $item->get('ChannelStateDesc');
            $call->channels[$uid] = ['name' => (string) $item->get('Channel'), 'endpoint' => $endpoint, 'state' => $state];

            if ($uid === $call->rootUid) {
                continue;
            }

            $extension = $this->settings->isExtension($endpoint) ? $endpoint : null;
            $isTrunk = $this->settings->isCrmTrunk($endpoint);
            $started = $now - self::seconds($item->get('Duration'));

            if ($call->kind === TrackedCall::INBOUND && $extension !== null) {
                $call->legs[$uid] = self::leg($extension, false);
                $call->legs[$uid]['ringingAt'] = $started;

                if ($state === 'Up' && ($call->answeredExtension === null || $call->answeredExtension === $extension)) {
                    $call->legs[$uid]['status'] = 'ANSWER';
                    $this->adoptAnswer($call, $uid, $started, $extension);
                }
            } elseif ($isTrunk && $call->kind === TrackedCall::INBOUND) {
                // A forwarded leg (the mobile failover): answered when Up, by nobody's desk phone.
                $call->legs[$uid] = self::leg(null, true);

                if ($state === 'Up' && $call->answeredExtension === null) {
                    $call->legs[$uid]['status'] = 'ANSWER';
                    $this->adoptAnswer($call, $uid, $started, null);
                }
            } elseif ($isTrunk && $call->kind === TrackedCall::OUTBOUND) {
                $call->legs[$uid] = self::leg(null, true);

                if ($state === 'Up') {
                    $call->legs[$uid]['status'] = 'ANSWER';
                    $this->adoptAnswer($call, $uid, $started, null);
                }
            }
        }
    }

    /**
     * The answer seen in a channel list: the talking pair is set again (so the first hang-up ends the conversation)
     * while a stored answer time is kept.
     */
    private function adoptAnswer(TrackedCall $call, string $uid, float $started, ?string $extension): void
    {
        if ($call->answeredAt === null) {
            $call->answeredAt = $started;
            $call->approximate = true;
        }

        $call->answeredExtension ??= $extension;
        $call->answeredPair = [$call->rootUid, $uid];
    }

    /**
     * The external number a desk phone's channel is dialling (Dial application data «PJSIP/<number>@<CRM trunk>»).
     */
    private function dialledNumber(Message $channel): ?string
    {
        if (strcasecmp((string) $channel->get('Application'), 'Dial') !== 0
            || !preg_match('~^PJSIP/([^@,&]+)@([^,&]+)~', (string) $channel->get('ApplicationData'), $m)
            || !$this->settings->isCrmTrunk($m[2])) {
            return null;
        }

        return self::externalNumber($m[1]);
    }

    /**
     * @return list<CallSnapshot>
     */
    private function finish(TrackedCall $call, float $at): array
    {
        $call->endedAt = $at;

        if ($call->answeredAt !== null) {
            $call->talkEndedAt ??= $at;
        }

        $out = $call->hasSnapshot() ? [$this->snapshot($call, true)] : [];
        unset($this->calls[$call->linkedId], $this->emitted[$call->linkedId]);

        return $out;
    }

    /**
     * @return list<CallSnapshot>
     */
    private function emit(TrackedCall $call): array
    {
        if (!$call->hasSnapshot()) {
            return [];
        }

        $snapshot = $this->snapshot($call, false);
        $fingerprint = $snapshot->fingerprint();

        if (($this->emitted[$call->linkedId] ?? null) === $fingerprint) {
            return [];
        }

        $this->emitted[$call->linkedId] = $fingerprint;

        return [$snapshot];
    }

    private function snapshot(TrackedCall $call, bool $final): CallSnapshot
    {
        $inbound = $call->kind === TrackedCall::INBOUND;
        $answered = $call->answeredAt !== null;
        $cards = [];
        $participants = [];

        if ($inbound) {
            foreach ($call->legs as $uid => $leg) {
                $extension = $leg['extension'];

                if ($extension === null || $leg['ringingAt'] === null) {
                    continue;
                }

                $participants[$extension] = true;

                $state = match (true) {
                    $extension === $call->answeredExtension && $leg['status'] === 'ANSWER' =>
                        $final ? CallSnapshot::CARD_ENDED : CallSnapshot::CARD_TALKING,
                    !$final && $call->isRinging((string) $uid) => CallSnapshot::CARD_RINGING,
                    default => CallSnapshot::CARD_CLOSED,
                };

                $cards[$extension] = self::strongerCard($cards[$extension] ?? null, $state);
            }

            foreach ($call->rungBefore as $extension) {
                $participants[$extension] = true;
                $cards[$extension] ??= CallSnapshot::CARD_CLOSED;
            }

            if ($call->answeredExtension !== null) {
                $participants[$call->answeredExtension] = true;
                $state = $final ? CallSnapshot::CARD_ENDED : CallSnapshot::CARD_TALKING;
                $cards[$call->answeredExtension] = self::strongerCard($cards[$call->answeredExtension] ?? null, $state);
            }

            $assignee = $call->answeredExtension ?? $call->firstRung() ?? $call->knownAssignee;
            $participants = array_fill_keys(array_unique([...$call->rungInOrder(), ...array_keys($participants)]), true);
        } else {
            $assignee = $call->callerExtension;

            if ($assignee !== null) {
                $participants[$assignee] = true;
                $cards[$assignee] = match (true) {
                    $final => $call->isPersisted() ? CallSnapshot::CARD_ENDED : CallSnapshot::CARD_CLOSED,
                    $answered => CallSnapshot::CARD_TALKING,
                    default => CallSnapshot::CARD_DIALING,
                };
            }
        }

        $raw = null;

        if ($final) {
            $raw = match (true) {
                $answered => 'ANSWER',
                $call->lost => 'LOST',
                default => $call->lastDialStatus ?? 'NODIAL',
            };
        }

        return new CallSnapshot(
            linkedId: $call->linkedId,
            persist: $call->isPersisted(),
            direction: $inbound ? CallSnapshot::INBOUND : CallSnapshot::OUTBOUND,
            viaCrm: $call->viaCrm,
            intentId: $call->intentId,
            number: $call->number,
            numberRaw: $call->numberRaw,
            line: $call->line,
            startedAt: $call->startedAt,
            answeredAt: $call->answeredAt,
            endedAt: $final ? $call->endedAt : null,
            talkEndedAt: $call->talkEndedAt,
            liveState: match (true) {
                $final => $call->lost ? CallSnapshot::LOST : CallSnapshot::ENDED,
                $answered => CallSnapshot::TALKING,
                default => CallSnapshot::RINGING,
            },
            final: $final,
            rawStatus: $raw,
            assigneeExtension: $assignee,
            participantExtensions: array_map('strval', array_keys($participants)),
            cards: $cards,
            recordingFile: $call->recordingFile,
            approximate: $call->approximate,
            answeredExtension: $inbound ? $call->answeredExtension : null,
            rungExtensions: $inbound ? $call->rungInOrder() : [],
        );
    }

    // --- helpers ---------------------------------------------------------------------------------------------------

    /**
     * @return array{?TrackedCall, string}
     */
    private function callOf(Message $m): array
    {
        $linked = $m->get('Linkedid');
        $uid = (string) $m->get('Uniqueid');

        return [$linked ? ($this->calls[$linked] ?? null) : null, $uid];
    }

    /**
     * @return array{extension: ?string, trunk: bool, ringingAt: ?float, status: ?string, gone: bool}
     */
    private static function leg(?string $extension, bool $trunk): array
    {
        return ['extension' => $extension, 'trunk' => $trunk, 'ringingAt' => null, 'status' => null, 'gone' => false];
    }

    private static function strongerCard(?string $current, string $new): string
    {
        $rank = [
            CallSnapshot::CARD_CLOSED => 1,
            CallSnapshot::CARD_RINGING => 2,
            CallSnapshot::CARD_DIALING => 2,
            CallSnapshot::CARD_ENDED => 3,
            CallSnapshot::CARD_TALKING => 3,
        ];

        return $current !== null && $rank[$current] >= $rank[$new] ? $current : $new;
    }

    /**
     * A number as Asterisk reported it, kept only when it looks like one (digits, «+», «*», «#»).
     */
    private static function externalNumber(?string $value): ?string
    {
        $value = trim((string) $value);

        return preg_match('/^\+?[0-9*#]{1,40}$/', $value) ? $value : null;
    }

    /**
     * CoreShowChannel Duration «HH:MM:SS» → seconds.
     */
    private static function seconds(?string $duration): float
    {
        if ($duration === null || !preg_match('/^(\d+):(\d{2}):(\d{2})$/', $duration, $m)) {
            return 0.0;
        }

        return (float) ((int) $m[1] * 3600 + (int) $m[2] * 60 + (int) $m[3]);
    }
}
