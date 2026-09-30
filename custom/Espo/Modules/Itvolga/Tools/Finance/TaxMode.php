<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Finance;

use Espo\Modules\Itvolga\Tools\Finance\Exceptions\InvalidValue;

/**
 * Tax regime of a document (Vtiger `taxtype`, `hdnTaxType`).
 */
enum TaxMode: string
{
    /** Tax rate per line. */
    case Individual = 'individual';
    /** One rate for the document, stored on every line; tax added on top of the pre-tax total. */
    case Group = 'group';
    /** SalesPlatform: prices already include the tax; the tax amount is only shown, never added. */
    case GroupTaxIncluded = 'group_tax_inc';

    public static function fromSource(string $value): self
    {
        return self::tryFrom($value) ?? throw new InvalidValue("Unknown tax mode '$value'.");
    }
}
