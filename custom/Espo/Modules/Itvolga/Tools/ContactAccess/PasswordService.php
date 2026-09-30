<?php

namespace Espo\Modules\Itvolga\Tools\ContactAccess;

use Espo\Core\Acl;
use Espo\Core\Acl\Table;
use Espo\Core\Exceptions\Forbidden;
use Espo\Core\Exceptions\NotFound;
use Espo\Core\Field\LinkParent;
use Espo\Core\Utils\Config;
use Espo\Entities\ActionHistoryRecord;
use Espo\Entities\User;
use Espo\Modules\Itvolga\Entities\ContactAccess;
use Espo\ORM\EntityManager;
use RuntimeException;

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
        private Config $config,
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

        return $encrypted === null ? null : $this->decrypt($encrypted);
    }

    /**
     * Inverse of Espo\Core\Utils\Crypt::encrypt() (AES-256-CBC, key = sha256(cryptKey), IV appended). Unlike
     * Crypt::decrypt() it does not trim the result: leading and trailing spaces of a password are preserved.
     */
    private function decrypt(string $encrypted): string
    {
        $decoded = base64_decode($encrypted, true);

        if ($decoded === false || strlen($decoded) <= 16) {
            throw new RuntimeException("Malformed ciphertext.");
        }

        $key = hash('sha256', (string) $this->config->get('cryptKey', ''), true);
        $value = openssl_decrypt(substr($decoded, 0, -16), 'aes-256-cbc', $key, OPENSSL_RAW_DATA, substr($decoded, -16));

        if ($value === false) {
            throw new RuntimeException("OpenSSL decrypt failure.");
        }

        return $value;
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
