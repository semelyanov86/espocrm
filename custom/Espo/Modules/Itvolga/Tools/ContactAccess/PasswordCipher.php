<?php

namespace Espo\Modules\Itvolga\Tools\ContactAccess;

use Espo\Core\Utils\Config;
use RuntimeException;

/**
 * Inverse of Espo\Core\Utils\Crypt::encrypt() (AES-256-CBC, key = sha256(cryptKey), IV appended). Unlike
 * Crypt::decrypt() it does not trim the result: leading and trailing spaces of a password are preserved.
 */
class PasswordCipher
{
    public function __construct(private Config $config) {}

    public function decrypt(string $encrypted): string
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
}
