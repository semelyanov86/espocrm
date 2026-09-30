<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Finance\Source;

use Espo\Modules\Itvolga\Tools\Finance\Decimal;
use Espo\Modules\Itvolga\Tools\Finance\Document;

/**
 * A live Vtiger document with its stored totals (the reference, D-05).
 */
final class SourceDocument
{
    public function __construct(
        public readonly Document $document,
        /** vtiger_*.region_id: NULL for documents saved before the 2018-07 upgrade, 0 afterwards. */
        public readonly ?int $regionId,
        public readonly Decimal $subtotal,
        public readonly Decimal $preTaxTotal,
        public readonly Decimal $grandTotal,
    ) {}

    public static function of(Document $document, ?int $regionId, mixed $subtotal, mixed $preTaxTotal, mixed $grandTotal): self
    {
        return new self($document, $regionId, Decimal::of($subtotal), Decimal::of($preTaxTotal), Decimal::of($grandTotal));
    }
}
