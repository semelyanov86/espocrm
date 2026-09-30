<?php

namespace Espo\Modules\Itvolga\Entities;

use Espo\Core\Templates\Entities\Base;

/**
 * Remote-access credentials of a contact (Vtiger Contacts.cf_1322–cf_1328, decision D-06).
 *
 * `anydeskPassword` holds ciphertext only (see Hooks\ContactAccess\ProtectPassword); the plain value is
 * returned solely by Tools\ContactAccess\PasswordService::reveal(), which logs every call.
 */
class ContactAccess extends Base
{
    public const ENTITY_TYPE = 'ContactAccess';

    public const FIELD_PASSWORD = 'anydeskPassword';
    public const FIELD_HAS_PASSWORD = 'hasAnydeskPassword';

    /** Plain-text limit in characters; the column (varchar 1024) keeps the base64 ciphertext: ≤ 576 chars for 100 4-byte chars. */
    public const PASSWORD_MAX_LENGTH = 100;

    public function getContactId(): ?string
    {
        return $this->get('contactId');
    }

    public function getEncryptedPassword(): ?string
    {
        $value = $this->get(self::FIELD_PASSWORD);

        return is_string($value) && $value !== '' ? $value : null;
    }
}
