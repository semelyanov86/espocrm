<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\SecurityKey\Core;

use Espo\Modules\Itvolga\Tools\SecurityKey\Core\Cbor\ByteString;
use Espo\Modules\Itvolga\Tools\SecurityKey\Core\Cbor\CborMap;

/**
 * A credential public key of one of the supported COSE algorithms, kept as its SubjectPublicKeyInfo (DER) — the form
 * OpenSSL imports and the form stored with the key:
 *
 * - ES256 (-7): EC2, P-256, ECDSA with SHA-256 (YubiKey default), signature DER-encoded;
 * - EdDSA (-8): OKP, Ed25519 (sodium), signature 64 bytes;
 * - RS256 (-257): RSA 2048–4096 bits, PKCS#1 v1.5 with SHA-256 (Windows Hello).
 *
 * Every key is checked when built: the EC point must lie on the curve (OpenSSL refuses the import otherwise), the RSA
 * modulus and exponent must be sane. Verification never falls back to another algorithm.
 */
final class PublicKey
{
    public const ES256 = -7;
    public const EDDSA = -8;
    public const RS256 = -257;

    // SubjectPublicKeyInfo prefixes: id-ecPublicKey + prime256v1, uncompressed point follows; id-Ed25519, key follows.
    private const P256_PREFIX = '3059301306072a8648ce3d020106082a8648ce3d030107034200';
    private const ED25519_PREFIX = '302a300506032b6570032100';
    // AlgorithmIdentifier rsaEncryption with NULL parameters.
    private const RSA_ALGORITHM = '300d06092a864886f70d0101010500';

    private const RSA_MIN_BITS = 2048;
    private const RSA_MAX_BITS = 4096;
    private const MAX_SIGNATURE_BYTES = 1024;

    private function __construct(
        public readonly int $algorithm,
        public readonly string $der,
    ) {}

    /**
     * The algorithms this PHP can verify, in the order of preference offered to the browser.
     *
     * @return list<int>
     */
    public static function supportedAlgorithms(): array
    {
        return function_exists('sodium_crypto_sign_verify_detached') ?
            [self::ES256, self::EDDSA, self::RS256] :
            [self::ES256, self::RS256];
    }

    public static function fromCose(CborMap $key): self
    {
        $algorithm = $key->get(3);

        if (!is_int($algorithm) || !in_array($algorithm, self::supportedAlgorithms(), true)) {
            throw new VerificationFailed(VerificationFailed::ALGORITHM);
        }

        $type = $key->get(1);

        $der = match ($algorithm) {
            self::ES256 => $type === 2 && $key->get(-1) === 1 ?
                self::p256Der(self::bytes($key, -2, 32), self::bytes($key, -3, 32)) :
                throw self::invalid(),
            self::EDDSA => $type === 1 && $key->get(-1) === 6 ?
                hex2bin(self::ED25519_PREFIX) . self::bytes($key, -2, 32) :
                throw self::invalid(),
            default => $type === 3 ?
                self::rsaDer(self::bytes($key, -1, 512), self::bytes($key, -2, 4)) :
                throw self::invalid(),
        };

        return self::fromStored($algorithm, $der);
    }

    /**
     * A key as stored with a credential; checked again, as data read back from the database.
     */
    public static function fromStored(int $algorithm, string $der): self
    {
        if (!in_array($algorithm, self::supportedAlgorithms(), true)) {
            throw new VerificationFailed(VerificationFailed::ALGORITHM);
        }

        if ($algorithm === self::EDDSA) {
            if (strlen($der) !== 44 || !str_starts_with($der, hex2bin(self::ED25519_PREFIX))) {
                throw self::invalid();
            }

            return new self($algorithm, $der);
        }

        $details = self::importDetails($der);
        $expectedType = $algorithm === self::ES256 ? OPENSSL_KEYTYPE_EC : OPENSSL_KEYTYPE_RSA;

        if ($details === null || ($details['type'] ?? null) !== $expectedType) {
            throw self::invalid();
        }

        if ($algorithm === self::ES256 && ($details['ec']['curve_name'] ?? null) !== 'prime256v1') {
            throw self::invalid();
        }

        if (
            $algorithm === self::RS256 &&
            (($details['bits'] ?? 0) < self::RSA_MIN_BITS || ($details['bits'] ?? 0) > self::RSA_MAX_BITS)
        ) {
            throw self::invalid();
        }

        return new self($algorithm, $der);
    }

    public function verify(string $data, string $signature): bool
    {
        if ($signature === '' || strlen($signature) > self::MAX_SIGNATURE_BYTES) {
            return false;
        }

        if ($this->algorithm === self::EDDSA) {
            return strlen($signature) === SODIUM_CRYPTO_SIGN_BYTES &&
                sodium_crypto_sign_verify_detached($signature, $data, substr($this->der, -32));
        }

        $key = openssl_pkey_get_public(self::pem($this->der));

        if ($key === false) {
            self::clearOpensslErrors();

            return false;
        }

        $result = openssl_verify($data, $signature, $key, OPENSSL_ALGO_SHA256);
        self::clearOpensslErrors();

        return $result === 1;
    }

    private static function bytes(CborMap $key, int $label, int $maxLength): string
    {
        $value = $key->get($label);

        if (!$value instanceof ByteString || $value->bytes === '' || strlen($value->bytes) > $maxLength) {
            throw self::invalid();
        }

        return $value->bytes;
    }

    private static function p256Der(string $x, string $y): string
    {
        if (strlen($x) !== 32 || strlen($y) !== 32) {
            throw self::invalid();
        }

        return hex2bin(self::P256_PREFIX) . "\x04" . $x . $y;
    }

    private static function rsaDer(string $modulus, string $exponent): string
    {
        $modulus = ltrim($modulus, "\x00");
        $exponent = ltrim($exponent, "\x00");
        $bits = strlen($modulus) * 8 - (8 - strlen(decbin(ord($modulus[0] ?? "\x00"))));

        if ($bits < self::RSA_MIN_BITS || $bits > self::RSA_MAX_BITS || (ord($modulus[-1]) & 1) === 0) {
            throw self::invalid();
        }

        $e = $exponent === '' ? 0 : (int) hexdec(bin2hex($exponent));

        if ($e < 3 || ($e & 1) === 0) {
            throw self::invalid();
        }

        $rsaPublicKey = self::der(0x30, self::derInteger($modulus) . self::derInteger($exponent));

        return self::der(0x30, hex2bin(self::RSA_ALGORITHM) . self::der(0x03, "\x00" . $rsaPublicKey));
    }

    private static function derInteger(string $unsigned): string
    {
        return self::der(0x02, (ord($unsigned[0]) & 0x80) !== 0 ? "\x00" . $unsigned : $unsigned);
    }

    private static function der(int $tag, string $content): string
    {
        $length = strlen($content);

        if ($length < 0x80) {
            return chr($tag) . chr($length) . $content;
        }

        $lengthBytes = ltrim(pack('N', $length), "\x00");

        return chr($tag) . chr(0x80 | strlen($lengthBytes)) . $lengthBytes . $content;
    }

    /**
     * @return ?array<string, mixed>
     */
    private static function importDetails(string $der): ?array
    {
        $key = openssl_pkey_get_public(self::pem($der));

        if ($key === false) {
            self::clearOpensslErrors();

            return null;
        }

        $details = openssl_pkey_get_details($key);
        self::clearOpensslErrors();

        return $details === false ? null : $details;
    }

    private static function pem(string $der): string
    {
        return "-----BEGIN PUBLIC KEY-----\n" . chunk_split(base64_encode($der), 64, "\n") . "-----END PUBLIC KEY-----\n";
    }

    private static function clearOpensslErrors(): void
    {
        while (openssl_error_string() !== false) {
            // OpenSSL keeps a per-thread error queue; drain it so a refused key does not leak into later calls.
        }
    }

    private static function invalid(): VerificationFailed
    {
        return new VerificationFailed(VerificationFailed::KEY);
    }
}
