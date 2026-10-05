<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Mailing;

use DateTimeImmutable;
use DateTimeZone;
use Espo\Core\Utils\Config;
use Espo\Core\Utils\Language;
use Espo\Entities\Preferences;
use Espo\Modules\Itvolga\Tools\Report\Core\Mailing\MailingSettings;
use Espo\Modules\Itvolga\Tools\Report\Core\Mailing\Schedule;
use Espo\ORM\EntityManager;
use Throwable;

/**
 * The moments of a mailing in the time zone of the report owner (D-121): his Preferences, else the system's, else UTC
 * — as a run resolves relative periods (ReportRunner). Stored values are UTC `Y-m-d H:i:s`.
 */
final class MailingClock
{
    public function __construct(
        private readonly EntityManager $entityManager,
        private readonly Config $config,
    ) {}

    public function zone(?string $userId): DateTimeZone
    {
        $preferences = $userId ? $this->entityManager->getEntityById(Preferences::ENTITY_TYPE, $userId) : null;
        $name = (string) ($preferences?->get('timeZone') ?: ($this->config->get('timeZone') ?: 'UTC'));

        try {
            return new DateTimeZone($name);
        } catch (Throwable) {
            return new DateTimeZone('UTC');
        }
    }

    public static function now(): DateTimeImmutable
    {
        return new DateTimeImmutable('now', new DateTimeZone('UTC'));
    }

    /**
     * The first slot of an enabled mailing after now, or null.
     */
    public function first(?MailingSettings $settings, ?string $ownerId, ?DateTimeImmutable $now = null): ?string
    {
        if ($settings === null || !$settings->enabled) {
            return null;
        }

        return Schedule::first($settings, $this->zone($ownerId), $now ?? self::now())->format('Y-m-d H:i:s');
    }

    /**
     * The slot after the run of a scheduled one, or null for a mailing that is off.
     */
    public function after(?MailingSettings $settings, ?string $ownerId, string $scheduled, DateTimeImmutable $now): ?string
    {
        if ($settings === null || !$settings->enabled) {
            return null;
        }

        return Schedule::after($settings, $this->zone($ownerId), new DateTimeImmutable($scheduled,
            new DateTimeZone('UTC')), $now)->format('Y-m-d H:i:s');
    }

    /**
     * «еженедельно, понедельник, 09:00 (Europe/Moscow)» in a language.
     */
    public function summary(MailingSettings $settings, Language $language, ?string $ownerId): string
    {
        $parts = [(string) $language->translateOption($settings->frequency, 'mailingFrequency', 'Report')];

        if ($settings->weekday !== null) {
            // Global.lists.dayNames start with Sunday; ISO 7 is Sunday.
            $days = $language->get(['Global', 'lists', 'dayNames']) ?? [];
            $parts[] = mb_strtolower((string) ($days[$settings->weekday % 7] ?? $settings->weekday));
        }

        if ($settings->month !== null) {
            $months = $language->get(['Global', 'lists', 'monthNames']) ?? [];
            $parts[] = $settings->day . ' ' . mb_strtolower((string) ($months[$settings->month - 1] ?? $settings->month));
        } elseif ($settings->day !== null) {
            $parts[] = str_replace('{n}', (string) $settings->day,
                $language->translateLabel('mailingDayOfMonth', 'labels', 'Report'));
        }

        $parts[] = $settings->time . ' (' . $this->zone($ownerId)->getName() . ')';

        return implode(', ', $parts);
    }
}
