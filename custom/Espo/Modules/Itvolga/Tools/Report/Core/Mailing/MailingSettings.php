<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Mailing;

/**
 * The mailing of a report (step 9 of the builder, D-121), checked and canonical: on/off, the schedule (frequency, time
 * on the 15-minute grid of the job, weekday ISO 1–7, day of month, month), the letter (subject, text), the recipients —
 * users, teams and extra addresses, or the user links «generate for» (each found user gets his own slice; the two are
 * exclusive) — the formats of the attachments and the flags «no limit» and «skip an empty report».
 */
final class MailingSettings
{
    public const DAILY = 'daily';
    public const WEEKLY = 'weekly';
    public const BIWEEKLY = 'biweekly';
    public const MONTHLY = 'monthly';
    public const YEARLY = 'yearly';
    public const FREQUENCIES = [self::DAILY, self::WEEKLY, self::BIWEEKLY, self::MONTHLY, self::YEARLY];
    public const FORMATS = ['csv', 'xlsx', 'pdf'];

    /**
     * @param list<string> $users ids
     * @param list<string> $teams ids
     * @param list<string> $emails extra addresses
     * @param list<string> $formats
     * @param list<string> $generateFor references of user links (`assignedUser`, `account.assignedUser`)
     */
    public function __construct(
        public readonly bool $enabled,
        public readonly string $frequency,
        public readonly string $time,
        public readonly ?int $weekday = null,
        public readonly ?int $day = null,
        public readonly ?int $month = null,
        public readonly string $subject = '',
        public readonly string $text = '',
        public readonly array $users = [],
        public readonly array $teams = [],
        public readonly array $emails = [],
        public readonly array $formats = [],
        public readonly bool $noLimit = false,
        public readonly bool $skipEmpty = false,
        public readonly array $generateFor = [],
    ) {}

    public function hour(): int
    {
        return (int) substr($this->time, 0, 2);
    }

    public function minute(): int
    {
        return (int) substr($this->time, 3, 2);
    }

    /**
     * Canonical stored form.
     *
     * @return array<string, mixed>
     */
    public function toArray(): array
    {
        return [
            'enabled' => $this->enabled,
            'frequency' => $this->frequency,
            'time' => $this->time,
            'weekday' => $this->weekday,
            'day' => $this->day,
            'month' => $this->month,
            'subject' => $this->subject,
            'text' => $this->text,
            'users' => $this->users,
            'teams' => $this->teams,
            'emails' => $this->emails,
            'formats' => $this->formats,
            'noLimit' => $this->noLimit,
            'skipEmpty' => $this->skipEmpty,
            'generateFor' => $this->generateFor,
        ];
    }

    /**
     * When the letters go: what readers of the report see of its mailing (no recipients, subject, text, D-124), and
     * what decides whether the next run is computed anew.
     *
     * @return array{enabled: bool, frequency: string, time: string, weekday: ?int, day: ?int, month: ?int}
     */
    public function schedule(): array
    {
        return [
            'enabled' => $this->enabled,
            'frequency' => $this->frequency,
            'time' => $this->time,
            'weekday' => $this->weekday,
            'day' => $this->day,
            'month' => $this->month,
        ];
    }
}
