<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Finance\Source;

/**
 * How the stored totals of a source document were formed (finance-contract.md §4, §12). Only combinations seen in the
 * live data have a class; anything else is Unverified and is never recalculated.
 */
enum FormulaClass: string
{
    /** No tax on the lines: subtotal = Σ net, pre-tax total = total = subtotal − document discount. */
    case NoLineTax = 'noLineTax';
    /** individual, region_id NULL (before the 2018-07 upgrade): tax1 on the lines, the totals do not include it. */
    case LineTaxNotApplied = 'lineTaxNotApplied';
    /** group_tax_inc, region_id NULL: the rate is on the lines, the tax is inside the prices and never added. */
    case TaxIncludedInPrice = 'taxIncludedInPrice';
    /** group, region_id NULL, one rate on every line, no document discount: total = pre-tax + tax rounded to kopecks. */
    case GroupTaxAdded = 'groupTaxAdded';
    /** A combination absent from the source data: no expected totals are produced. */
    case Unverified = 'unverified';
}
