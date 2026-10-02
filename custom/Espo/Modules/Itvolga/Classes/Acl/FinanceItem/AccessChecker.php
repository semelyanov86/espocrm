<?php

namespace Espo\Modules\Itvolga\Classes\Acl\FinanceItem;

use Espo\Core\Acl\AccessEntityCREDSChecker;
use Espo\Core\Acl\DefaultAccessChecker;
use Espo\Core\Acl\ScopeData;
use Espo\Core\Acl\Table;
use Espo\Core\AclManager;
use Espo\Core\Utils\Metadata;
use Espo\Entities\User;
use Espo\ORM\Entity;
use Espo\ORM\EntityManager;

/**
 * Items of finance documents (QuoteItem, SalesOrderItem, InvoiceItem): an item is read with its document's access —
 * the document's scope level, ownership and checker (AclManager) — so an item level set wider than the document's in
 * a role reveals nothing; the item's own role entry only has to enable reading. Lists follow the document's level as
 * well (Classes/Select/FinanceItem/DocumentLevel with the core ForeignOnlyTeam/ForeignOnlyOwn filters). Nobody —
 * admins included — creates, edits or deletes an item directly: lines change only through the document, which
 * recalculates its totals in the same transaction.
 *
 * @implements AccessEntityCREDSChecker<Entity>
 */
class AccessChecker implements AccessEntityCREDSChecker
{
    public function __construct(
        private string $entityType,
        private AclManager $aclManager,
        private DefaultAccessChecker $defaultAccessChecker,
        private EntityManager $entityManager,
        private Metadata $metadata,
    ) {}

    public function check(User $user, ScopeData $data): bool
    {
        return $this->checkRead($user, $data);
    }

    public function checkRead(User $user, ScopeData $data): bool
    {
        return $this->defaultAccessChecker->checkRead($user, $data) &&
            $this->aclManager->checkScope($user, $this->documentType(), Table::ACTION_READ);
    }

    public function checkEntityRead(User $user, Entity $entity, ScopeData $data): bool
    {
        if (!$this->checkRead($user, $data)) {
            return false;
        }

        $documentId = $entity->get($this->link() . 'Id');
        $document = $documentId ? $this->entityManager->getEntityById($this->documentType(), $documentId) : null;

        return $document !== null && $this->aclManager->checkEntityRead($user, $document);
    }

    public function checkCreate(User $user, ScopeData $data): bool
    {
        return false;
    }

    public function checkEdit(User $user, ScopeData $data): bool
    {
        return false;
    }

    public function checkDelete(User $user, ScopeData $data): bool
    {
        return false;
    }

    public function checkStream(User $user, ScopeData $data): bool
    {
        return false;
    }

    public function checkEntityCreate(User $user, Entity $entity, ScopeData $data): bool
    {
        return false;
    }

    public function checkEntityEdit(User $user, Entity $entity, ScopeData $data): bool
    {
        return false;
    }

    public function checkEntityDelete(User $user, Entity $entity, ScopeData $data): bool
    {
        return false;
    }

    public function checkEntityStream(User $user, Entity $entity, ScopeData $data): bool
    {
        return false;
    }

    private function link(): string
    {
        return $this->metadata->get(['aclDefs', $this->entityType, 'link']);
    }

    private function documentType(): string
    {
        return $this->metadata->get(['entityDefs', $this->entityType, 'links', $this->link(), 'entity']);
    }
}
