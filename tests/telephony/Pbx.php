<?php

declare(strict_types=1);

namespace Itvolga\Tests\Telephony;

use Espo\Modules\Itvolga\Tools\Telephony\Core\Ami\Message;
use Espo\Modules\Itvolga\Tools\Telephony\Core\CallSnapshot;
use Espo\Modules\Itvolga\Tools\Telephony\Core\CallTracker;

/**
 * Synthetic AMI events in the shapes Asterisk 22.5.2 sends them (recorded on the isolated PBX on 2026-10-13; numbers
 * are synthetic) and a tracker that collects the snapshots of a scenario.
 */
final class Pbx
{
    /** @var list<CallSnapshot> */
    public array $snapshots = [];
    public float $now = 1_800_000_000.0;

    public function __construct(public readonly CallTracker $tracker) {}

    /**
     * Feeds the message at now + $after seconds.
     *
     * @return list<CallSnapshot>
     */
    public function at(float $after, Message ...$messages): array
    {
        $this->now += $after;
        $out = [];

        foreach ($messages as $message) {
            $out = [...$out, ...$this->tracker->accept($message, $this->now)];
        }

        $this->snapshots = [...$this->snapshots, ...$out];

        return $out;
    }

    public function last(): ?CallSnapshot
    {
        return $this->snapshots === [] ? null : $this->snapshots[count($this->snapshots) - 1];
    }

    public static function channel(string $event, string $uid, string $linked, string $channel, string $state,
        string $context = '', string $exten = '', string $cid = '', array $extra = []): Message
    {
        return Message::of([
            'Event' => $event,
            'Channel' => $channel,
            'ChannelState' => '0',
            'ChannelStateDesc' => $state,
            'CallerIDNum' => $cid,
            'Context' => $context,
            'Exten' => $exten,
            'Uniqueid' => $uid,
            'Linkedid' => $linked,
        ] + $extra);
    }

    public static function newChannel(string $uid, string $linked, string $channel, string $state, string $context = '',
        string $exten = '', string $cid = ''): Message
    {
        return self::channel('Newchannel', $uid, $linked, $channel, $state, $context, $exten, $cid);
    }

    public static function newState(string $uid, string $linked, string $channel, string $state): Message
    {
        return self::channel('Newstate', $uid, $linked, $channel, $state);
    }

    public static function hangup(string $uid, string $linked, string $channel, string $cause = '16'): Message
    {
        return self::channel('Hangup', $uid, $linked, $channel, 'Up', '', '', '', ['Cause' => $cause]);
    }

    public static function recording(string $uid, string $linked, string $channel, string $file): Message
    {
        return self::channel('VarSet', $uid, $linked, $channel, 'Up', 'sub-monitor', 's', '',
            ['Variable' => 'MIXMONITOR_FILENAME', 'Value' => $file]);
    }

    /**
     * DialBegin; a null caller is the Originate leg (no Channel/Uniqueid headers).
     */
    public static function dialBegin(?string $callerUid, ?string $callerChannel, string $linked, string $destUid,
        string $destChannel, string $dialString): Message
    {
        $headers = ['Event' => 'DialBegin'];

        if ($callerUid !== null) {
            $headers += ['Channel' => (string) $callerChannel, 'Uniqueid' => $callerUid, 'Linkedid' => $linked];
        }

        return Message::of($headers + ['DestChannel' => $destChannel, 'DestUniqueid' => $destUid,
            'DestLinkedid' => $linked, 'DialString' => $dialString]);
    }

    public static function dialEnd(?string $callerUid, ?string $callerChannel, string $linked, string $destUid,
        string $destChannel, string $status): Message
    {
        $headers = ['Event' => 'DialEnd'];

        if ($callerUid !== null) {
            $headers += ['Channel' => (string) $callerChannel, 'Uniqueid' => $callerUid, 'Linkedid' => $linked];
        }

        return Message::of($headers + ['DestChannel' => $destChannel, 'DestUniqueid' => $destUid,
            'DestLinkedid' => $linked, 'DialStatus' => $status]);
    }

    public static function showChannel(string $uid, string $linked, string $channel, string $state, string $duration,
        string $cid = '', string $context = '', string $exten = ''): Message
    {
        return Message::of(['Event' => 'CoreShowChannel', 'ActionID' => 'r1', 'Channel' => $channel,
            'Uniqueid' => $uid, 'Linkedid' => $linked, 'ChannelStateDesc' => $state, 'CallerIDNum' => $cid,
            'Context' => $context, 'Exten' => $exten, 'Duration' => $duration]);
    }
}
