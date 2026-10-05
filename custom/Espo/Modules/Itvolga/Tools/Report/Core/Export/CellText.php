<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Export;

/**
 * Texts that leave the CRM in files: a cell a spreadsheet must not run as a formula, and a file name.
 */
final class CellText
{
    private const FORMULA_STARTS = ['=', '+', '-', '@'];
    private const MAX_FILE_NAME = 150;

    /**
     * A text cell with a leading apostrophe when a spreadsheet would read it as a formula: it starts with = + - @ (also
     * after spaces) or with a tab or a carriage return. A plain number stays as it is — the rule of the core export
     * (Tools/Export/Processor/Util), extended to the control characters.
     */
    public static function safe(string $value): string
    {
        if ($value === '' || is_numeric($value)) {
            return $value;
        }

        $trimmed = ltrim($value, " \t\r\n\v\0");

        if (in_array($value[0], ["\t", "\r"], true) ||
            $trimmed !== '' && in_array($trimmed[0], self::FORMULA_STARTS, true)) {
            return "'" . $value;
        }

        return $value;
    }

    /**
     * A file name of a title: characters a file system or a header would choke on are replaced (as the print forms do,
     * FinancePrint\PrintResult), dots and spaces trimmed, at most 150 characters; an empty title gives «report».
     */
    public static function fileName(string $title, string $extension): string
    {
        $name = preg_replace('/[\x00-\x1F\x7F\/\\\\:*?"<>|]+/u', '_', $title) ?? '';
        $name = trim(mb_substr(trim($name, " ."), 0, self::MAX_FILE_NAME), " .");

        return ($name !== '' ? $name : 'report') . '.' . $extension;
    }
}
