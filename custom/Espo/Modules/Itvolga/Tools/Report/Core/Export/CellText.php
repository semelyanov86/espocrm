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
     * after spaces) or with a tab or a carriage return (D-117). Unlike the core export a numeric text is no exception:
     * numbers are number cells and never come here, and a text like «+00123» would lose its sign and zeros (external
     * review 05.3 W1).
     */
    public static function safe(string $value): string
    {
        if ($value === '') {
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
