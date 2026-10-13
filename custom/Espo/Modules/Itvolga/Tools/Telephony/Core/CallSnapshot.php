<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Telephony\Core;

/**
 * The externally visible state of one call (one Asterisk linkedid) after an event: what the Call record and the call
 * cards of the users must show. Times are Unix seconds of the listener's clock (AMI events carry no time). Extensions
 * stand for users; the writer maps them.
 */
final class CallSnapshot
{
    public const RINGING = 'ringing';
    public const TALKING = 'talking';
    public const ENDED = 'ended';
    public const LOST = 'lost';

    public const CARD_RINGING = 'ringing';
    public const CARD_DIALING = 'dialing';
    public const CARD_TALKING = 'talking';
    public const CARD_ENDED = 'ended';
    public const CARD_CLOSED = 'closed';

    public const INBOUND = 'Inbound';
    public const OUTBOUND = 'Outbound';

    /**
     * @param list<string> $participantExtensions
     * @param array<string, string> $cards extension => CARD_*
     * @param list<string> $rungExtensions
     */
    public function __construct(
        public readonly string $linkedId,
        /** A Call is stored for this call (an external inbound or outbound call). */
        public readonly bool $persist,
        public readonly string $direction,
        /** Started by click-to-call (Originate with the CRM ChannelId prefix). */
        public readonly bool $viaCrm,
        public readonly ?string $intentId,
        /** Canonical external number (PhoneNumbers::canonical), null when unknown or not a phone number. */
        public readonly ?string $number,
        /** The external number as Asterisk reported it (digits, «+», «*», «#» only). */
        public readonly ?string $numberRaw,
        /** The dialled line (DID) of an inbound call. */
        public readonly ?string $line,
        public readonly float $startedAt,
        public readonly ?float $answeredAt,
        public readonly ?float $endedAt,
        public readonly ?float $talkEndedAt,
        public readonly string $liveState,
        public readonly bool $final,
        /** Final DialStatus (ANSWER, NOANSWER, BUSY, CANCEL, CONGESTION, CHANUNAVAIL), NODIAL, LOST; null while live. */
        public readonly ?string $rawStatus,
        /** Null: nobody's phone rang, the writer takes the fallback extension. */
        public readonly ?string $assigneeExtension,
        public readonly array $participantExtensions,
        public readonly array $cards,
        /** Absolute file name reported by MixMonitor. */
        public readonly ?string $recordingFile,
        /** Times rebuilt from a channel snapshot after the listener was away. */
        public readonly bool $approximate,
        /** The desk phone that answered an inbound call (null: nobody, or a forwarded leg such as the mobile). */
        public readonly ?string $answeredExtension = null,
        /** Desk phones that rang for an inbound call, in ring order: the writer assigns the first one with a user. */
        public readonly array $rungExtensions = [],
    ) {}

    public function isAnswered(): bool
    {
        return $this->answeredAt !== null;
    }

    public function status(): string
    {
        return $this->isAnswered() ? 'Held' : 'Not Held';
    }

    /**
     * Seconds of conversation: from the human answer to the first hang-up of the two talking channels.
     */
    public function talkSeconds(float $now): int
    {
        if ($this->answeredAt === null) {
            return 0;
        }

        $end = $this->talkEndedAt ?? $this->endedAt ?? $now;

        return max(0, (int) round($end - $this->answeredAt));
    }

    public function fingerprint(): string
    {
        return md5(serialize(get_object_vars($this)));
    }
}
