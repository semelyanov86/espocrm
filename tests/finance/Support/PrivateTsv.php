<?php

declare(strict_types=1);

namespace Itvolga\Tests\Finance\Support;

use RuntimeException;

/**
 * Reader of a private multi-statement mysql --batch output: every result set starts with a header row whose first
 * column is `k`, data rows start with their kind. Values are returned as strings ('NULL' stays 'NULL').
 */
final class PrivateTsv
{
    /**
     * @return array<string, list<array<string, string>>> kind → rows keyed by column name
     */
    public static function read(string $file): array
    {
        $handle = @fopen($file, 'rb');

        if ($handle === false) {
            throw new RuntimeException('Cannot read ' . basename($file) . '.');
        }

        $columns = null;
        $result = [];

        while (($line = fgets($handle)) !== false) {
            $cells = explode("\t", rtrim($line, "\n"));

            if ($cells[0] === 'k') {
                $columns = $cells;

                continue;
            }

            if ($columns === null || count($cells) !== count($columns)) {
                throw new RuntimeException('Unexpected row shape in ' . basename($file) . " (kind '{$cells[0]}').");
            }

            $result[$cells[0]][] = array_combine($columns, $cells);
        }

        fclose($handle);

        return $result;
    }
}
