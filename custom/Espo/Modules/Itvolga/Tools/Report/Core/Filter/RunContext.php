<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Filter;

use DateTimeImmutable;
use DateTimeZone;

/**
 * The moment, time zone and user a report runs for (D-92): relative periods and "current user" resolve against them.
 */
final class RunContext
{
    public function __construct(
        public readonly DateTimeImmutable $now,
        public readonly string $timeZone,
        public readonly string $userId,
        public readonly int $fiscalYearShift = 0,
    ) {}

    public function today(): DateTimeImmutable
    {
        return $this->now->setTimezone(new DateTimeZone($this->timeZone))->setTime(0, 0);
    }

    /**
     * Offset of the time zone at the moment of the run, in hours (for TZ: of date groups of datetime fields).
     */
    public function offsetHours(): string
    {
        $seconds = (new DateTimeZone($this->timeZone))->getOffset($this->now);

        return rtrim(rtrim(number_format($seconds / 3600, 2, '.', ''), '0'), '.');
    }
}
