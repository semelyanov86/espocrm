<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Format;

use Espo\Modules\Itvolga\Tools\Report\Core\Granularity;

/**
 * Labels of date group keys produced by the query (D-89): day 'YYYY-MM-DD' (formatted by the caller's date
 * formatter), week 'YYYY/W' (ISO, Monday first), month 'YYYY-MM', quarter 'YYYY_Q', half-year 'YYYY_H', year 'YYYY'.
 */
final class PeriodLabel
{
    /**
     * @param list<string> $monthNames 12 names in the user's language
     * @param array{week: string, quarter: string, halfYear: string} $patterns with {n} and {year}
     * @param callable(string): string $dateFormatter 'YYYY-MM-DD' → user notation
     */
    public function __construct(
        private readonly array $monthNames,
        private readonly array $patterns,
        private $dateFormatter,
    ) {}

    public function label(Granularity $granularity, string $key): string
    {
        $parts = preg_split('/[-_\/]/', $key) ?: [$key];

        return match ($granularity) {
            Granularity::DAY => ($this->dateFormatter)($key),
            Granularity::WEEK => $this->pattern('week', $parts),
            Granularity::MONTH => ($this->monthNames[(int) ($parts[1] ?? 0) - 1] ?? $key) . ' ' . $parts[0],
            Granularity::QUARTER => $this->pattern('quarter', $parts),
            Granularity::HALF_YEAR => $this->pattern('halfYear', $parts),
            Granularity::YEAR => $key,
        };
    }

    /**
     * @param list<string> $parts
     */
    private function pattern(string $name, array $parts): string
    {
        return strtr($this->patterns[$name], ['{year}' => $parts[0], '{n}' => (string) (int) ($parts[1] ?? '')]);
    }
}
