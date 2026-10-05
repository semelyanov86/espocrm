<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Export;

/**
 * One cell of a flat file (CSV, XLSX — D-117, D-118): a kind and its value as a string. Numbers stay decimal strings
 * (no float here), dates are ISO `Y-m-d`, date-times `Y-m-d H:i` in the time zone of the user the file is made for.
 */
final class SheetCell
{
    public const TEXT = 'text';
    public const NUMBER = 'number';
    public const DATE = 'date';
    public const DATETIME = 'datetime';
    public const EMPTY = 'empty';

    private function __construct(
        public readonly string $kind,
        public readonly string $value,
    ) {}

    public static function text(string $value): self
    {
        return $value === '' ? self::empty() : new self(self::TEXT, $value);
    }

    public static function number(string $decimal): self
    {
        return new self(self::NUMBER, $decimal);
    }

    public static function date(string $isoDate): self
    {
        return new self(self::DATE, $isoDate);
    }

    public static function dateTime(string $value): self
    {
        return new self(self::DATETIME, $value);
    }

    public static function empty(): self
    {
        return new self(self::EMPTY, '');
    }
}
