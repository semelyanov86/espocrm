<?php

namespace Espo\Modules\Itvolga\Tools\ContactAccess;

use Espo\Core\Acl;
use Espo\Core\Acl\Table;
use Espo\Core\Exceptions\Forbidden;
use Espo\Core\Exceptions\NotFound;
use Espo\Core\Field\LinkParent;
use Espo\Core\Utils\Crypt;
use Espo\Entities\ActionHistoryRecord;
use Espo\Entities\User;
use Espo\Modules\Itvolga\Entities\ContactAccess;
use Espo\ORM\EntityManager;

/**
 * Returns the plain AnyDesk password of a ContactAccess record to a user who may read that record,
 * and records who revealed it, when and from which address (Administration → Action History, action «reveal»).
 */
class PasswordService
{
    public const ACTION_REVEAL = 'reveal';

    public function __construct(
        private EntityManager $entityManager,
        private Acl $acl,
        private User $user,
        private Crypt $crypt,
    ) {}

    /**
     * @throws Forbidden
     * @throws NotFound
     */
    public function reveal(string $id): ?string
    {
        if (!$this->acl->checkScope(ContactAccess::ENTITY_TYPE, Table::ACTION_READ)) {
            throw new Forbidden("No access to ContactAccess.");
        }

        $entity = $this->entityManager->getRDBRepositoryByClass(ContactAccess::class)->getById($id);

        if (!$entity) {
            throw new NotFound();
        }

        if (!$this->acl->checkEntityRead($entity)) {
            throw new Forbidden("No read access to the record.");
        }

        $this->log($entity);

        $encrypted = $entity->getEncryptedPassword();

        return $encrypted === null ? null : $this->crypt->decrypt($encrypted);
    }

    private function log(ContactAccess $entity): void
    {
        $record = $this->entityManager->getRDBRepositoryByClass(ActionHistoryRecord::class)->getNew();

        $record
            ->setAction(self::ACTION_REVEAL)
            ->setUserId($this->user->getId())
            ->setAuthTokenId($this->user->get('authTokenId'))
            ->setAuthLogRecordId($this->user->get('authLogRecordId'))
            ->setIpAddress($this->user->get('ipAddress'))
            ->setTarget(LinkParent::fromEntity($entity));

        $record->set('data', (object) ['field' => ContactAccess::FIELD_PASSWORD]);

        $this->entityManager->saveEntity($record);
    }
}
