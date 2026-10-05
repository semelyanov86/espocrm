<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Mailing;

use Espo\Modules\Itvolga\Tools\Report\Core\Definition\DefinitionError;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\FieldInfo;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\FieldRef;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\Schema;

/**
 * Checks the stored mailing part of a report (D-121). parse() — the structure, without the model (the job, the preview
 * of the next run and the change check use it); generateFor() — the user links «generate for» through the Schema of a
 * user (the one who saves, then the owner at every run): a user link of the main entity or of a to-one link, not closed
 * to him (403 otherwise). Errors name the rule and the place (`mailing.time`), never a value.
 */
final class MailingSettingsParser
{
    public const MAX_SUBJECT = 255;
    public const MAX_TEXT = 5000;
    public const MAX_USERS = 50;
    public const MAX_TEAMS = 20;
    public const MAX_EMAILS = 20;
    public const MAX_GENERATE_FOR = 3;
    private const ID = '/^[A-Za-z0-9_-]{1,36}$/';
    private const TIME = '/^([01]\d|2[0-3]):(00|15|30|45)$/';
    /** Days of the months in a leap year: the 29th of February is a valid yearly date (D-121). */
    private const MONTH_DAYS = [1 => 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];

    /**
     * Null or an empty object: no mailing.
     */
    public static function parse(mixed $raw): ?MailingSettings
    {
        if (is_object($raw)) {
            $raw = json_decode((string) json_encode($raw), true);
        }

        if ($raw === null || $raw === []) {
            return null;
        }

        if (!is_array($raw)) {
            throw new DefinitionError('badMailing', 'mailing');
        }

        $enabled = $raw['enabled'] ?? false;
        $frequency = $raw['frequency'] ?? MailingSettings::DAILY;
        $time = $raw['time'] ?? '09:00';

        if (!is_bool($enabled)) {
            throw new DefinitionError('badMailing', 'mailing.enabled');
        }

        if (!in_array($frequency, MailingSettings::FREQUENCIES, true)) {
            throw new DefinitionError('badMailingFrequency', 'mailing.frequency');
        }

        if (!is_string($time) || !preg_match(self::TIME, $time)) {
            throw new DefinitionError('badMailingTime', 'mailing.time');
        }

        $weekly = in_array($frequency, [MailingSettings::WEEKLY, MailingSettings::BIWEEKLY], true);
        $yearly = $frequency === MailingSettings::YEARLY;
        $weekday = $weekly ? self::number($raw['weekday'] ?? null, 1, 7, 'weekday') : null;
        $month = $yearly ? self::number($raw['month'] ?? null, 1, 12, 'month') : null;
        $day = in_array($frequency, [MailingSettings::MONTHLY, MailingSettings::YEARLY], true) ?
            self::number($raw['day'] ?? null, 1, $month !== null ? self::MONTH_DAYS[$month] : 31, 'day') : null;

        $subject = self::text($raw['subject'] ?? '', self::MAX_SUBJECT, 'subject');

        if (preg_match('/[\x00-\x1F\x7F]/', $subject)) {
            throw new DefinitionError('badMailingSubject', 'mailing.subject');
        }

        $users = self::ids($raw['users'] ?? [], self::MAX_USERS, 'users');
        $teams = self::ids($raw['teams'] ?? [], self::MAX_TEAMS, 'teams');
        $emails = self::emails($raw['emails'] ?? []);
        $formats = self::formats($raw['formats'] ?? []);
        $generateFor = self::refs($raw['generateFor'] ?? []);

        foreach (['noLimit', 'skipEmpty'] as $flag) {
            if (!is_bool($raw[$flag] ?? false)) {
                throw new DefinitionError('badMailing', "mailing.$flag");
            }
        }

        if ($generateFor !== [] && ($users !== [] || $teams !== [] || $emails !== [])) {
            throw new DefinitionError('mailingGenerateForExclusive', 'mailing.generateFor');
        }

        if ($enabled && $formats === []) {
            throw new DefinitionError('mailingNoFormats', 'mailing.formats');
        }

        if ($enabled && $generateFor === [] && $users === [] && $teams === [] && $emails === []) {
            throw new DefinitionError('mailingNoRecipients', 'mailing.users');
        }

        return new MailingSettings(
            enabled: $enabled,
            frequency: $frequency,
            time: $time,
            weekday: $weekday,
            day: $day,
            month: $month,
            subject: $subject,
            text: self::text($raw['text'] ?? '', self::MAX_TEXT, 'text'),
            users: $users,
            teams: $teams,
            emails: $emails,
            formats: $formats,
            noLimit: $raw['noLimit'] ?? false,
            skipEmpty: $raw['skipEmpty'] ?? false,
            generateFor: $generateFor,
        );
    }

    /**
     * The «generate for» links as fields of the user's model: user links of the main entity or of a to-one link.
     *
     * @return list<FieldInfo>
     * @throws DefinitionError badGenerateFor; FieldForbidden — closed to the user
     */
    public static function generateFor(MailingSettings $settings, string $entityType, Schema $schema): array
    {
        $fields = [];

        foreach ($settings->generateFor as $i => $ref) {
            $field = $schema->field($entityType, FieldRef::parse($ref) ?? throw new DefinitionError('badGenerateFor',
                "mailing.generateFor[$i]"));

            if ($field === null || !$field->isUserLink() || $field->linkKind === FieldInfo::LINK_MANY) {
                throw new DefinitionError('badGenerateFor', "mailing.generateFor[$i]");
            }

            $fields[] = $field;
        }

        return $fields;
    }

    private static function number(mixed $value, int $min, int $max, string $key): int
    {
        if (!is_int($value) || $value < $min || $value > $max) {
            throw new DefinitionError('badMailingSchedule', "mailing.$key");
        }

        return $value;
    }

    private static function text(mixed $value, int $max, string $key): string
    {
        if (!is_string($value) || mb_strlen($value) > $max || !mb_check_encoding($value, 'UTF-8')) {
            throw new DefinitionError('badMailingText', "mailing.$key", ['max' => $max]);
        }

        return trim($value);
    }

    /**
     * @return list<string>
     */
    private static function ids(mixed $value, int $max, string $key): array
    {
        if (!is_array($value) || !array_is_list($value) || count($value) > $max) {
            throw new DefinitionError('badMailingRecipients', "mailing.$key", ['max' => $max]);
        }

        foreach ($value as $i => $id) {
            if (!is_string($id) || !preg_match(self::ID, $id)) {
                throw new DefinitionError('badMailingRecipients', "mailing.{$key}[$i]", ['max' => $max]);
            }
        }

        return array_values(array_unique($value));
    }

    /**
     * Extra addresses: a list or a text separated by «;» (also «,» and line breaks); repeats are dropped regardless of
     * the case.
     *
     * @return list<string>
     */
    private static function emails(mixed $value): array
    {
        if (is_string($value)) {
            $value = preg_split('/[;,\s]+/u', $value, -1, PREG_SPLIT_NO_EMPTY) ?: [];
        }

        if (!is_array($value) || !array_is_list($value)) {
            throw new DefinitionError('badMailingEmails', 'mailing.emails', ['max' => self::MAX_EMAILS]);
        }

        $result = [];

        foreach ($value as $i => $email) {
            $email = is_string($email) ? trim($email) : null;

            if ($email === null || strlen($email) > 254 || !filter_var($email, FILTER_VALIDATE_EMAIL)) {
                throw new DefinitionError('badMailingEmails', "mailing.emails[$i]", ['max' => self::MAX_EMAILS]);
            }

            $result[mb_strtolower($email)] ??= $email;
        }

        if (count($result) > self::MAX_EMAILS) {
            throw new DefinitionError('badMailingEmails', 'mailing.emails', ['max' => self::MAX_EMAILS]);
        }

        return array_values($result);
    }

    /**
     * @return list<string>
     */
    private static function formats(mixed $value): array
    {
        if (!is_array($value) || !array_is_list($value) ||
            array_filter($value, fn ($f) => !in_array($f, MailingSettings::FORMATS, true)) !== []) {
            throw new DefinitionError('badMailingFormats', 'mailing.formats');
        }

        return array_values(array_intersect(MailingSettings::FORMATS, $value));
    }

    /**
     * @return list<string>
     */
    private static function refs(mixed $value): array
    {
        if (!is_array($value) || !array_is_list($value) || count($value) > self::MAX_GENERATE_FOR) {
            throw new DefinitionError('badGenerateFor', 'mailing.generateFor');
        }

        $refs = [];

        foreach ($value as $i => $ref) {
            $parsed = FieldRef::parse($ref);

            if ($parsed === null) {
                throw new DefinitionError('badGenerateFor', "mailing.generateFor[$i]");
            }

            $refs[] = $parsed->toString();
        }

        return array_values(array_unique($refs));
    }
}
