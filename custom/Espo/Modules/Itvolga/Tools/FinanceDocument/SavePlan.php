<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\FinanceDocument;

use Espo\Modules\Itvolga\Tools\Finance\Editing\EditPlan;
use Espo\ORM\Entity;

/**
 * What DocumentProcessor::prepare decided before the document row is written; persist() applies it to the items.
 */
final class SavePlan
{
    /**
     * @param array<string, Entity> $items stored items by id
     * @param array<string, string> $productNames names of products of new or changed lines, by id
     */
    public function __construct(
        public readonly EditPlan $edit,
        public readonly array $items,
        public readonly array $productNames,
    ) {}
}
