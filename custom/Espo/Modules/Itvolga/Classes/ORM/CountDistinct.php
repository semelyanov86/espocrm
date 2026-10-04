<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Classes\ORM;

use Espo\ORM\QueryComposer\Part\FunctionConverter;
use RuntimeException;

/**
 * ORM function ITVOLGA_COUNT_DISTINCT:(expression) → COUNT(DISTINCT expression) (reports, stage 05.1, D-86).
 *
 * The core expression language has no COUNT DISTINCT and drops DISTINCT from grouped queries, while a report counts
 * records of the main entity even when a joined to-many link repeats them. The argument arrives already compiled by
 * the query composer (a quoted column), never as user input.
 */
final class CountDistinct implements FunctionConverter
{
    public function convert(string ...$argumentList): string
    {
        if (count($argumentList) !== 1) {
            throw new RuntimeException('ITVOLGA_COUNT_DISTINCT takes exactly one argument.');
        }

        return 'COUNT(DISTINCT ' . $argumentList[0] . ')';
    }
}
