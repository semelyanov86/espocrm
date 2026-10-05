<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Export;

/**
 * The boundary of a spreadsheet number (D-118): XLSX keeps numbers as IEEE doubles and the writer (OpenSpout) puts a
 * float into the file by the string conversion of PHP (its `precision`), so a decimal string becomes a native number
 * only when that conversion gives back exactly the same number — at most 15 significant digits, and then the digits
 * PHP prints; otherwise it stays text in the file and never changes silently. This is the only place of the module
 * where a money value becomes a float.
 */
final class SheetNumber
{
    private const MAX_DIGITS = 15;

    public static function native(string $decimal): int|float|null
    {
        if (!preg_match('/^(-?)(\d+)(?:\.(\d+))?$/', $decimal, $m)) {
            return null;
        }

        $integer = ltrim($m[2], '0');
        $fraction = rtrim($m[3] ?? '', '0');
        $digits = ltrim($integer . $fraction, '0');

        if (strlen($digits) > self::MAX_DIGITS || strlen($integer) > self::MAX_DIGITS) {
            return null;
        }

        if ($fraction === '') {
            return (int) ($m[1] . ($integer !== '' ? $integer : '0'));
        }

        $normalized = $m[1] . ($integer !== '' ? $integer : '0') . '.' . $fraction;
        $number = (float) $normalized;

        // The text the file gets (internal review: with precision 14 a 15-digit amount lost its last digit).
        return (string) $number === $normalized ? $number : null;
    }
}
