<?php

declare(strict_types=1);

namespace Itvolga\Tests\Reports;

use DateTimeImmutable;
use DateTimeZone;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\DefinitionError;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\FieldForbidden;
use Espo\Modules\Itvolga\Tools\Report\Core\Mailing\DiscoveryFilters;
use Espo\Modules\Itvolga\Tools\Report\Core\Mailing\MailingSettings;
use Espo\Modules\Itvolga\Tools\Report\Core\Mailing\MailingSettingsParser;
use Espo\Modules\Itvolga\Tools\Report\Core\Mailing\Schedule;
use Itvolga\Tests\Finance\TestCase;

/**
 * The mailing part (D-121, D-122): canonical form and refusals of the settings, the «generate for» links through the
 * Schema, and the moments of every frequency in the owner's time zone (today if still ahead, the last day of a short
 * month, the 29th of February, the anchor of every two weeks, no catching up of missed slots).
 */
final class MailingTest extends TestCase
{
    private DateTimeZone $moscow;

    public function setUp(): void
    {
        $this->moscow = new DateTimeZone('Europe/Moscow');
    }

    /**
     * @param array<string, mixed> $extra
     */
    private static function settings(array $extra = []): MailingSettings
    {
        return MailingSettingsParser::parse($extra + ['enabled' => true, 'frequency' => 'daily', 'time' => '09:00',
            'formats' => ['xlsx'], 'users' => ['u1']]);
    }

    private function refused(array $raw, string $key, string $path): void
    {
        $error = $this->assertThrows(DefinitionError::class, fn () => MailingSettingsParser::parse($raw));
        assert($error instanceof DefinitionError);
        $this->assertSame($key, $error->key, 'key');
        $this->assertSame($path, $error->path, 'path');
    }

    private static function utc(string $value): DateTimeImmutable
    {
        return new DateTimeImmutable($value, new DateTimeZone('UTC'));
    }

    private function first(array $extra, string $nowUtc): string
    {
        return Schedule::first(self::settings($extra), $this->moscow, self::utc($nowUtc))->format('Y-m-d H:i');
    }

    public function testCanonicalForm(): void
    {
        $settings = MailingSettingsParser::parse([
            'enabled' => true, 'frequency' => 'weekly', 'time' => '18:45', 'weekday' => 5, 'day' => 3, 'month' => 2,
            'subject' => '  Итоги недели ', 'text' => "Строка 1\nСтрока 2", 'users' => ['u1', 'u1', 'u2'],
            'teams' => ['t1'], 'emails' => 'Boss@Example.com; boss@example.com, second@example.com',
            'formats' => ['pdf', 'csv'], 'noLimit' => true, 'skipEmpty' => true, 'names' => ['u1' => 'X'],
        ]);

        $this->assertSame([
            'enabled' => true, 'frequency' => 'weekly', 'time' => '18:45', 'weekday' => 5, 'day' => null,
            'month' => null, 'subject' => 'Итоги недели', 'text' => "Строка 1\nСтрока 2", 'users' => ['u1', 'u2'],
            'teams' => ['t1'], 'emails' => ['Boss@Example.com', 'second@example.com'], 'formats' => ['csv', 'pdf'],
            'noLimit' => true, 'skipEmpty' => true, 'generateFor' => [],
        ], $settings->toArray());
        $this->assertSame(['enabled' => true, 'frequency' => 'weekly', 'time' => '18:45', 'weekday' => 5,
            'day' => null, 'month' => null], $settings->schedule());

        $this->assertSame(null, MailingSettingsParser::parse(null));
        $this->assertSame(null, MailingSettingsParser::parse((object) []));
        // A switched-off mailing keeps its settings without recipients or formats.
        $this->assertSame(false, MailingSettingsParser::parse(['enabled' => false, 'formats' => []])->enabled);
    }

    public function testRefusals(): void
    {
        $base = ['enabled' => true, 'frequency' => 'daily', 'time' => '09:00', 'formats' => ['csv'], 'users' => ['u1']];

        $this->refused(['frequency' => 'hourly'] + $base, 'badMailingFrequency', 'mailing.frequency');
        $this->refused(['time' => '09:10'] + $base, 'badMailingTime', 'mailing.time');
        $this->refused(['time' => '24:00'] + $base, 'badMailingTime', 'mailing.time');
        $this->refused(['frequency' => 'weekly', 'weekday' => 0] + $base, 'badMailingSchedule', 'mailing.weekday');
        $this->refused(['frequency' => 'monthly', 'day' => 32] + $base, 'badMailingSchedule', 'mailing.day');
        $this->refused(['frequency' => 'yearly', 'month' => 4, 'day' => 31] + $base, 'badMailingSchedule',
            'mailing.day');
        $this->refused(['formats' => ['xml']] + $base, 'badMailingFormats', 'mailing.formats');
        $this->refused(['formats' => []] + $base, 'mailingNoFormats', 'mailing.formats');
        $this->refused(['users' => []] + $base, 'mailingNoRecipients', 'mailing.users');
        $this->refused(['users' => array_map(fn ($i) => "u$i", range(1, 51))] + $base, 'badMailingRecipients',
            'mailing.users');
        $this->refused(['users' => ["x'; DROP"]] + $base, 'badMailingRecipients', 'mailing.users[0]');
        $this->refused(['emails' => ['not-an-address']] + $base, 'badMailingEmails', 'mailing.emails[0]');
        $this->refused(['subject' => "a\r\nBcc: x@example.com"] + $base, 'badMailingSubject', 'mailing.subject');
        $this->refused(['generateFor' => ['assignedUser']] + $base, 'mailingGenerateForExclusive',
            'mailing.generateFor');
        $this->refused(['noLimit' => 'yes'] + $base, 'badMailing', 'mailing.noLimit');

        // Only «generate for» is a source of recipients too.
        $this->assertSame(['assignedUser'], MailingSettingsParser::parse(['users' => [],
            'generateFor' => ['assignedUser']] + $base)->generateFor);
    }

    public function testGenerateForThroughTheSchema(): void
    {
        $schema = new FakeSchema();
        $settings = self::settings(['users' => [], 'generateFor' => ['assignedUser', 'account.assignedUser']]);
        $fields = MailingSettingsParser::generateFor($settings, 'Invoice', $schema);

        $this->assertSame(['assignedUser', 'account.assignedUser'], array_map(fn ($f) => $f->ref->toString(), $fields));

        foreach (['status', 'account', 'items.product', 'nothing'] as $ref) {
            $bad = self::settings(['users' => [], 'generateFor' => [$ref]]);
            $error = $this->assertThrows(DefinitionError::class, fn () =>
                MailingSettingsParser::generateFor($bad, 'Invoice', $schema));
            $this->assertSame('badGenerateFor', $error->key, $ref);
        }

        $closed = self::settings(['users' => [], 'generateFor' => ['secretOwner']]);
        $this->assertThrows(FieldForbidden::class, fn () => MailingSettingsParser::generateFor($closed, 'Invoice',
            $schema));
    }

    public function testDailyAndWeekly(): void
    {
        // 05:00 UTC = 08:00 in Moscow: 09:00 is still ahead today; 06:30 UTC = 09:30 — tomorrow.
        $this->assertSame('2026-10-05 06:00', $this->first([], '2026-10-05 05:00'));
        $this->assertSame('2026-10-06 06:00', $this->first([], '2026-10-05 06:30'));
        $this->assertSame('2026-10-06 06:00', $this->first([], '2026-10-05 06:00'), 'the slot itself has passed');
        // The Moscow day changes before the UTC one: 22:00 UTC is already the next day there.
        $this->assertSame('2026-10-06 20:15', $this->first(['time' => '23:15'], '2026-10-05 21:00'));

        // 2026-10-05 is a Monday.
        $this->assertSame('2026-10-09 06:00', $this->first(['frequency' => 'weekly', 'weekday' => 5],
            '2026-10-05 05:00'));
        $this->assertSame('2026-10-05 06:00', $this->first(['frequency' => 'weekly', 'weekday' => 1],
            '2026-10-05 05:00'), 'today, still ahead');
        $this->assertSame('2026-10-12 06:00', $this->first(['frequency' => 'weekly', 'weekday' => 1],
            '2026-10-05 07:00'), 'today has passed');
    }

    public function testMonthlyAndYearly(): void
    {
        $monthly31 = ['frequency' => 'monthly', 'day' => 31];

        $this->assertSame('2026-10-31 06:00', $this->first($monthly31, '2026-10-05 05:00'));
        $this->assertSame('2026-11-30 06:00', $this->first($monthly31, '2026-10-31 07:00'), '30 days in November');
        $this->assertSame('2027-02-28 06:00', $this->first($monthly31, '2027-01-31 07:00'), 'not the 3rd of March');
        $this->assertSame('2028-02-29 06:00', $this->first($monthly31, '2028-01-31 07:00'), 'leap year');
        $this->assertSame('2027-03-31 06:00', Schedule::after(self::settings($monthly31), $this->moscow,
            self::utc('2027-02-28 06:00'), self::utc('2027-02-28 06:05'))->format('Y-m-d H:i'), 'the day is kept');

        $leap = ['frequency' => 'yearly', 'month' => 2, 'day' => 29];
        $this->assertSame('2027-02-28 06:00', $this->first($leap, '2026-10-05 05:00'));
        $this->assertSame('2028-02-29 06:00', $this->first($leap, '2027-03-01 05:00'));
        $this->assertSame('2026-12-01 06:00', $this->first(['frequency' => 'yearly', 'month' => 12, 'day' => 1],
            '2026-10-05 05:00'));
    }

    public function testBiweeklyKeepsItsAnchorAndMissedSlotsAreNotCaughtUp(): void
    {
        $settings = self::settings(['frequency' => 'biweekly', 'weekday' => 1]);
        $after = fn (string $scheduled, string $now) =>
            Schedule::after($settings, $this->moscow, self::utc($scheduled), self::utc($now))->format('Y-m-d H:i');

        $this->assertSame('2026-10-19 06:00', $after('2026-10-05 06:00', '2026-10-05 06:10'));
        // A run that came late (the job is every 15 minutes) keeps the anchor.
        $this->assertSame('2026-10-19 06:00', $after('2026-10-05 06:00', '2026-10-07 12:00'));
        // A stand-still of 20 days: one attempt now, then the next slot of the same rhythm.
        $this->assertSame('2026-11-02 06:00', $after('2026-10-05 06:00', '2026-10-25 12:00'));

        $daily = self::settings();
        $this->assertSame('2026-10-26 06:00', Schedule::after($daily, $this->moscow, self::utc('2026-10-05 06:00'),
            self::utc('2026-10-25 12:00'))->format('Y-m-d H:i'), 'no catching up');
    }

    public function testTheSearchOfGenerateForUsersIgnoresTheCurrentUser(): void
    {
        $me = ['field' => 'assignedUser', 'where' => ['type' => 'isCurrentUser', 'attribute' => 'assignedUserId']];
        $status = ['field' => 'status', 'where' => ['type' => 'in', 'attribute' => 'status', 'value' => ['Sent']]];
        $tree = fn (array ...$items) => ['type' => 'and', 'items' => $items];

        // AND: the condition leaves, the others stay.
        $this->assertSame($tree($status), DiscoveryFilters::withoutCurrentUser($tree($me, $status)));
        // OR with it is true as a whole (dropping a branch would narrow the search).
        $this->assertSame($tree($status), DiscoveryFilters::withoutCurrentUser($tree(
            ['type' => 'or', 'items' => [$me, $status]], $status)));
        $this->assertSame($tree(), DiscoveryFilters::withoutCurrentUser(['type' => 'or', 'items' => [$status, $me]]));
        // Inside a where of one field (the core search views make and/or of a field).
        $nested = ['field' => 'assignedUser', 'where' => ['type' => 'or', 'value' => [
            ['type' => 'isCurrentUser', 'attribute' => 'assignedUserId'],
            ['type' => 'isNull', 'attribute' => 'assignedUserId']]]];
        $this->assertSame($tree(), DiscoveryFilters::withoutCurrentUser($tree($nested)));
        $this->assertSame($tree($status), DiscoveryFilters::withoutCurrentUser($tree($status)));
    }

    public function testBiweeklyKeepsItsWeekdayAfterTheOwnerZoneChanges(): void
    {
        // Monday 00:00 in Moscow is stored as Sunday 21:00 UTC; the owner then moves to UTC.
        $settings = self::settings(['frequency' => 'biweekly', 'weekday' => 1, 'time' => '00:00']);
        $next = Schedule::after($settings, new DateTimeZone('UTC'), self::utc('2026-10-04 21:00'),
            self::utc('2026-10-05 10:00'));

        $this->assertSame('2026-10-19 00:00 1', $next->format('Y-m-d H:i N'));
    }

    public function testOtherTimeZones(): void
    {
        $settings = self::settings(['time' => '09:00']);

        $this->assertSame('2026-10-05 23:00', Schedule::first($settings, new DateTimeZone('Asia/Vladivostok'),
            self::utc('2026-10-05 05:00'))->format('Y-m-d H:i'));
        // A day of a clock change (Berlin, 2026-03-29): 02:30 does not exist, the slot moves forward.
        $night = self::settings(['time' => '02:30']);
        $this->assertSame('2026-03-29 01:30', Schedule::first($night, new DateTimeZone('Europe/Berlin'),
            self::utc('2026-03-28 23:00'))->format('Y-m-d H:i'));
    }
}
