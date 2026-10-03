<?php

namespace Espo\Modules\Itvolga\Classes\Select\FinanceItem;

use Espo\Core\Acl;
use Espo\Core\Select\AccessControl\DefaultFilterResolver;
use Espo\Core\Select\AccessControl\FilterResolver;
use Espo\Core\Utils\Metadata;

/**
 * Access filter of item lists (QuoteItem, SalesOrderItem, InvoiceItem, ActItem): the read level of the document decides
 * (all, team → core ForeignOnlyTeam, own → core ForeignOnlyOwn, no), not the item's own level, which only has to enable
 * reading.
 */
class DocumentLevel implements FilterResolver
{
    public function __construct(
        private string $entityType,
        private Acl $acl,
        private Metadata $metadata,
    ) {}

    public function resolve(): ?string
    {
        if ($this->acl->checkReadNo($this->entityType)) {
            return 'no';
        }

        $link = $this->metadata->get(['aclDefs', $this->entityType, 'link']);
        $documentType = $this->metadata->get(['entityDefs', $this->entityType, 'links', $link, 'entity']);

        return (new DefaultFilterResolver($documentType, $this->acl))->resolve();
    }
}
