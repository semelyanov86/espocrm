<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Format;

use Espo\Modules\Itvolga\Tools\Finance\Decimal;

/**
 * Display of report numbers in the user's notation without floats (D-91): thousand groups and decimal mark of the
 * user's preferences; money shows exactly two decimals (rounded half away from zero, the value itself is kept raw).
 */
final class NumberText
{
    public function __construct(
        private readonly string $decimalMark = ',',
        private readonly string $thousandSeparator = ' ',
    ) {}

    /**
     * @param Decimal|string|int|null $value
     * @param ?int $scale exact number of decimals (rounded), null = as significant
     */
    public function format(Decimal|string|int|null $value, ?int $scale = null): string
    {
        if ($value === null || $value === '') {
            return '';
        }

        $decimal = Decimal::of($value);
        $text = $scale === null ? $decimal->toString() : $decimal->round($scale)->toFixed($scale);
        $sign = '';

        if (str_starts_with($text, '-')) {
            $sign = '-';
            $text = substr($text, 1);
        }

        [$integer, $fraction] = array_pad(explode('.', $text, 2), 2, '');
        $grouped = $this->thousandSeparator === '' ? $integer :
            ltrim(strrev(chunk_split(strrev($integer), 3, strrev($this->thousandSeparator))), $this->thousandSeparator);

        if ($sign !== '' && trim($grouped . $fraction, '0') === '') {
            $sign = '';
        }

        return $sign . $grouped . ($fraction !== '' ? $this->decimalMark . $fraction : '');
    }
}
