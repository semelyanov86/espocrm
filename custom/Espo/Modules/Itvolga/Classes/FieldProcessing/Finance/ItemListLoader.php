<?php

namespace Espo\Modules\Itvolga\Classes\FieldProcessing\Finance;

use Espo\Core\FieldProcessing\Loader;
use Espo\Core\FieldProcessing\Loader\Params;
use Espo\Modules\Itvolga\Tools\FinanceDocument\DocumentProcessor;
use Espo\Modules\Itvolga\Tools\FinanceDocument\DocumentTypes;
use Espo\ORM\Entity;

/**
 * Fills the non-stored `itemList` of a finance document on read (and before an update, so that an unchanged table
 * is not taken for an edit: the loaded value is also the fetched one).
 *
 * @implements Loader<Entity>
 */
class ItemListLoader implements Loader
{
    public function __construct(
        private DocumentTypes $types,
        private DocumentProcessor $processor,
    ) {}

    public function process(Entity $entity, Params $params): void
    {
        $type = $this->types->find($entity->getEntityType());

        if (!$type || ($params->hasSelect() && !$params->hasInSelect(DocumentProcessor::ITEM_LIST))) {
            return;
        }

        $itemList = $this->processor->loadItemList($entity, $type);

        $entity->set(DocumentProcessor::ITEM_LIST, $itemList);
        $entity->setFetched(DocumentProcessor::ITEM_LIST, $itemList);
    }
}
