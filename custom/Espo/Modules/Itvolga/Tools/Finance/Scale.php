<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Finance;

/**
 * Decimal places of finance values (source column types in comments).
 */
final class Scale
{
    /** Money of new documents and payments: kopecks (D-29). Source totals are DECIMAL(25,8) with ≤ 2 significant. */
    public const MONEY = 2;
    /** Line quantity, vtiger_inventoryproductrel.quantity DECIMAL(25,3). */
    public const QUANTITY = 3;
    /** Unit price, vtiger_inventoryproductrel.listprice DECIMAL(27,8). */
    public const UNIT_PRICE = 8;
    /** Discount and tax percentages, DECIMAL(7,3). */
    public const PERCENT = 3;
}
