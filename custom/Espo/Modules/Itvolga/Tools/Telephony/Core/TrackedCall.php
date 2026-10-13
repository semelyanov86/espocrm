<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Telephony\Core;

/**
 * @internal Mutable state of one linkedid inside CallTracker.
 */
final class TrackedCall
{
    public const PENDING = 'pending';
    public const INBOUND = 'inbound';
    public const OUTBOUND = 'outbound';
    public const INTERNAL = 'internal';
    public const IGNORED = 'ignored';

    public string $kind = self::IGNORED;
    public string $rootUid = '';
    public bool $viaCrm = false;
    public ?string $intentId = null;
    public ?string $callerExtension = null;
    public ?string $number = null;
    public ?string $numberRaw = null;
    public ?string $line = null;
    public ?float $answeredAt = null;
    public ?string $answeredExtension = null;
    /** @var list<string> */
    public array $answeredPair = [];
    public ?float $talkEndedAt = null;
    public ?float $endedAt = null;
    public ?string $lastDialStatus = null;
    public ?string $recordingFile = null;
    public bool $approximate = false;
    public bool $lost = false;
    public ?string $knownAssignee = null;
    /** @var list<string> Desk phones that rang before the listener (re)connected (from the stored call cards). */
    public array $rungBefore = [];
    public float $lastEventAt;

    /** @var array<string, array{name: string, endpoint: ?string, state: string}> uniqueid => channel */
    public array $channels = [];

    /**
     * Dialled destinations: extension legs of an inbound call, trunk legs.
     *
     * @var array<string, array{extension: ?string, trunk: bool, ringingAt: ?float, status: ?string, gone: bool}>
     */
    public array $legs = [];

    public function __construct(public readonly string $linkedId, public float $startedAt)
    {
        $this->lastEventAt = $startedAt;
    }

    public function isPersisted(): bool
    {
        return $this->kind === self::INBOUND || $this->kind === self::OUTBOUND;
    }

    public function hasSnapshot(): bool
    {
        return $this->isPersisted() || ($this->kind === self::PENDING && $this->viaCrm);
    }

    public function isRinging(string $uid): bool
    {
        $leg = $this->legs[$uid] ?? null;

        return $leg !== null && $leg['ringingAt'] !== null && $leg['status'] === null && !$leg['gone'];
    }

    public function firstRung(): ?string
    {
        return $this->rungInOrder()[0] ?? null;
    }

    /**
     * Desk phones that rang, in ring order: those known before a reconnection first, then the ringing legs.
     *
     * @return list<string>
     */
    public function rungInOrder(): array
    {
        $legs = array_filter($this->legs, static fn (array $leg) => $leg['extension'] !== null && $leg['ringingAt'] !== null);
        uasort($legs, static fn (array $a, array $b) => $a['ringingAt'] <=> $b['ringingAt']);

        return array_values(array_unique([
            ...$this->rungBefore,
            ...array_map(static fn (array $leg) => (string) $leg['extension'], $legs),
        ]));
    }
}
