<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Telephony\Core;

/**
 * A call the CRM stored as still in progress (Call.cLiveState ringing/talking): the input of the reconciliation after
 * the listener (re)connects.
 */
final class OpenCall
{
    public function __construct(
        public readonly string $linkedId,
        public readonly string $direction,
        public readonly bool $viaCrm,
        public readonly ?string $number,
        public readonly ?string $numberRaw,
        public readonly ?string $line,
        public readonly float $startedAt,
        public readonly ?float $answeredAt,
        /** Last time the listener saw the call alive (Call.dateEnd while live). */
        public readonly float $lastSeenAt,
        /** Call.cExtension: the caller of an outbound call, the assignee of an inbound one. */
        public readonly ?string $extension,
        /** @var list<string> Desk phones that rang for an inbound call, in ring order (its call cards). */
        public readonly array $rungExtensions = [],
        /** The desk phone that answered an inbound call (its card was talking); null: nobody or a forwarded leg. */
        public readonly ?string $answeredExtension = null,
    ) {}
}
