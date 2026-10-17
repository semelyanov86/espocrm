<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Telephony\Core;

use DateTimeImmutable;
use DateTimeZone;
use InvalidArgumentException;
use stdClass;

/**
 * One Asterisk call of the CDR history (stage 07.2, D-175): the operation the importer planned from the grouped CDR
 * legs (scripts/import/cdr.py), validated value by value before anything is written. Error codes name the field,
 * never its value. Pure: no EspoCRM dependency (tests/telephony).
 */
final class HistoryCall
{
    public const SOURCES = ['mysql', 'csv'];
    /** The attributes facts() owns: compared and written on every run (with the assignee extension, D-176). */
    public const FACTS = ['status', 'direction', 'dateStart', 'dateEnd', 'cPhoneNumber', 'cIncomingLine',
        'cCallStatusRaw', 'cBillDuration', 'cAnsweredAt', 'cLiveState', 'cClickToCall', 'cCdrSource', 'cRecording',
        'cRecordingPath', 'cExtension'];
    private const KEY = '/^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$/';
    private const STATUS = '/^[A-Z]{2,20}$/';
    private const NUMBER = '/^\+?[0-9]{1,30}$/';
    private const LINE = '/^[0-9A-Za-z+*#_.-]{1,40}$/';
    private const SHA256 = '/^[0-9a-f]{64}$/';
    private const DATETIME = 'Y-m-d H:i:s';

    /**
     * @param list<string> $rungExtensions
     * @param ?array{path: string, size: int, sha256: string} $recording
     */
    private function __construct(
        public readonly string $linkedId,
        public readonly string $source,
        public readonly string $direction,
        public readonly string $dateStart,
        public readonly string $dateEnd,
        public readonly ?string $answeredAt,
        public readonly int $billSeconds,
        public readonly string $rawStatus,
        public readonly ?string $numberRaw,
        public readonly ?string $line,
        public readonly bool $clickToCall,
        public readonly ?string $callerExtension,
        public readonly ?string $answeredExtension,
        public readonly array $rungExtensions,
        public readonly ?array $recording,
    ) {}

    /**
     * @throws InvalidArgumentException code = the field
     */
    public static function fromOperation(stdClass $op, TrackerSettings $settings): self
    {
        $linkedId = self::string($op, 'linkedId', self::KEY, false);
        $source = $op->source ?? null;
        $direction = $op->direction ?? null;

        if (!in_array($source, self::SOURCES, true)) {
            throw new InvalidArgumentException('source');
        }

        if (!in_array($direction, [CallSnapshot::INBOUND, CallSnapshot::OUTBOUND], true)) {
            throw new InvalidArgumentException('direction');
        }

        $start = self::datetime($op, 'dateStart', false);
        $end = self::datetime($op, 'dateEnd', false);
        $answered = self::datetime($op, 'answeredAt', true);

        if ($end < $start || ($answered !== null && ($answered < $start || $answered > $end))) {
            throw new InvalidArgumentException('dates');
        }

        $bill = $op->billSeconds ?? null;

        if (!is_int($bill) || $bill < 0 || $bill > strtotime($end . ' UTC') - strtotime($start . ' UTC')) {
            throw new InvalidArgumentException('billSeconds');
        }

        $rawStatus = self::string($op, 'rawStatus', self::STATUS, false);

        if (($rawStatus === 'ANSWER') !== ($answered !== null)) {
            throw new InvalidArgumentException('rawStatus');
        }

        $rung = $op->rungExtensions ?? null;

        if (!is_array($rung) || !array_is_list($rung) || count($rung) > 50) {
            throw new InvalidArgumentException('rungExtensions');
        }

        foreach ($rung as $extension) {
            if (!is_string($extension) || !$settings->isExtension($extension)) {
                throw new InvalidArgumentException('rungExtensions');
            }
        }

        foreach (['callerExtension', 'answeredExtension'] as $field) {
            $value = $op->$field ?? null;

            if ($value !== null && (!is_string($value) || !$settings->isExtension($value))) {
                throw new InvalidArgumentException($field);
            }
        }

        if (!is_bool($op->clickToCall ?? null)) {
            throw new InvalidArgumentException('clickToCall');
        }

        return new self(
            linkedId: $linkedId,
            source: $source,
            direction: $direction,
            dateStart: $start,
            dateEnd: $end,
            answeredAt: $answered,
            billSeconds: $bill,
            rawStatus: $rawStatus,
            numberRaw: self::string($op, 'numberRaw', self::NUMBER, true),
            line: self::string($op, 'line', self::LINE, true),
            clickToCall: $op->clickToCall,
            callerExtension: $op->callerExtension ?? null,
            answeredExtension: $op->answeredExtension ?? null,
            rungExtensions: array_values(array_unique($rung)),
            recording: self::recording($op->recording ?? null),
        );
    }

    public function status(): string
    {
        return $this->answeredAt !== null ? 'Held' : 'Not Held';
    }

    /**
     * Users that took part: everyone whose phone rang, and the caller.
     *
     * @return list<string>
     */
    public function participantExtensions(): array
    {
        return array_values(array_unique(array_filter([...$this->rungExtensions, $this->callerExtension])));
    }

    /**
     * The facts of the history import (CallFacts::ATTRIBUTES without the key) — the only attributes a re-run compares
     * and writes. `$recordingPath` is the path the call claims: playable only when `$playable` (a path another call
     * stores too stays claimed but is not played — the claim keeps blocking the other call, review 2026-10-17).
     *
     * @return array<string, mixed>
     */
    public function facts(string $localAreaCode, ?string $recordingPath, bool $playable, string $extension): array
    {
        return [
            'status' => $this->status(),
            'direction' => $this->direction,
            'dateStart' => $this->dateStart,
            'dateEnd' => $this->dateEnd,
            'cPhoneNumber' => PhoneNumbers::canonical($this->numberRaw, $localAreaCode) ?? $this->numberRaw,
            'cIncomingLine' => $this->line,
            'cCallStatusRaw' => $this->rawStatus,
            'cBillDuration' => $this->billSeconds,
            'cAnsweredAt' => $this->answeredAt,
            'cLiveState' => CallSnapshot::ENDED,
            'cClickToCall' => $this->clickToCall,
            'cCdrSource' => $this->source,
            'cRecording' => $recordingPath !== null && $playable,
            'cRecordingPath' => $recordingPath,
            'cExtension' => $extension,
        ];
    }

    private static function string(stdClass $op, string $field, string $pattern, bool $nullable): ?string
    {
        $value = $op->$field ?? null;

        if ($value === null && $nullable) {
            return null;
        }

        if (!is_string($value) || !preg_match($pattern, $value)) {
            throw new InvalidArgumentException($field);
        }

        return $value;
    }

    private static function datetime(stdClass $op, string $field, bool $nullable): ?string
    {
        $value = $op->$field ?? null;

        if ($value === null && $nullable) {
            return null;
        }

        $parsed = is_string($value)
            ? DateTimeImmutable::createFromFormat('!' . self::DATETIME, $value, new DateTimeZone('UTC'))
            : false;

        if ($parsed === false || $parsed->format(self::DATETIME) !== $value) {
            throw new InvalidArgumentException($field);
        }

        return $value;
    }

    /**
     * @return ?array{path: string, size: int, sha256: string}
     */
    private static function recording(mixed $value): ?array
    {
        if ($value === null) {
            return null;
        }

        if (!$value instanceof stdClass || !is_string($value->path ?? null) || !RecordingPath::isSafe($value->path)
            || !is_int($value->size ?? null) || $value->size < 0
            || !is_string($value->sha256 ?? null) || !preg_match(self::SHA256, $value->sha256)) {
            throw new InvalidArgumentException('recording');
        }

        return ['path' => $value->path, 'size' => $value->size, 'sha256' => $value->sha256];
    }
}
