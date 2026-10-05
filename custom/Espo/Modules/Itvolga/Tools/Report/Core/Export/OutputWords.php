<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Export;

/**
 * Words of a file or a print view in the language of the user it is made for (Report.labels, aggregateFunction
 * options; the adapter fills them from the language, the tests from literals). Labels of columns, groups and aggregates
 * and the formatted values already come in the result.
 */
final class OutputWords
{
    /**
     * @param array<string, string> $functions SUM|AVG|MIN|MAX → label
     */
    public function __construct(
        public readonly string $total = 'Total',
        public readonly string $currency = 'Currency',
        public readonly string $mixedCurrencies = 'mixed currencies',
        public readonly string $noData = 'No data',
        public readonly string $totalRecords = 'Total records',
        public readonly string $column = 'Column',
        public readonly string $function = 'Function',
        public readonly string $value = 'Value',
        public readonly array $functions = ['SUM' => 'SUM', 'AVG' => 'AVG', 'MIN' => 'MIN', 'MAX' => 'MAX'],
    ) {}

    public function function(string $function): string
    {
        return $this->functions[$function] ?? $function;
    }
}
