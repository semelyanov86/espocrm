<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\SecurityKey\Core;

/**
 * A registered security key as stored in the user's list: the credential id (bytes), the verified public key, the last
 * seen signature counter (unsigned 32-bit), the name the user gave it and the transports the browser reported (hints
 * for the next sign-in, never trusted). The stored array form uses base64url for bytes.
 */
final class Credential
{
    public const MAX_NAME_LENGTH = 100;
    public const TRANSPORTS = ['usb', 'nfc', 'ble', 'hybrid', 'internal', 'smart-card'];

    /**
     * @param list<string> $transports
     */
    public function __construct(
        public readonly string $id,
        public readonly PublicKey $publicKey,
        public readonly int $signCount,
        public readonly ?string $name,
        public readonly array $transports,
        public readonly string $createdAt,
        public readonly ?string $lastUsedAt,
    ) {}

    /**
     * A user-given name: trimmed, control and format characters removed, at most MAX_NAME_LENGTH characters; empty
     * means no name. Anything but a string or null is refused.
     */
    public static function normalizeName(mixed $name): ?string
    {
        if ($name === null) {
            return null;
        }

        if (!is_string($name) || !mb_check_encoding($name, 'UTF-8')) {
            throw new VerificationFailed(VerificationFailed::MALFORMED);
        }

        $name = trim((string) preg_replace('/[\p{Cc}\p{Cf}]+/u', '', $name));

        if (mb_strlen($name) > self::MAX_NAME_LENGTH) {
            throw new VerificationFailed(VerificationFailed::MALFORMED);
        }

        return $name === '' ? null : $name;
    }

    /**
     * Known transport names only, without repeats; anything else is dropped (they are hints).
     *
     * @return list<string>
     */
    public static function normalizeTransports(mixed $transports): array
    {
        if (!is_array($transports)) {
            return [];
        }

        return array_values(array_intersect(self::TRANSPORTS, array_filter($transports, 'is_string')));
    }

    /**
     * @param array<string, mixed> $row
     */
    public static function fromArray(array $row): self
    {
        $algorithm = $row['algorithm'] ?? null;
        $signCount = $row['signCount'] ?? null;
        $createdAt = $row['createdAt'] ?? null;
        $lastUsedAt = $row['lastUsedAt'] ?? null;

        if (
            !is_int($algorithm) ||
            !is_int($signCount) || $signCount < 0 || $signCount > 0xFFFFFFFF ||
            !is_string($createdAt) ||
            ($lastUsedAt !== null && !is_string($lastUsedAt))
        ) {
            throw new VerificationFailed(VerificationFailed::MALFORMED);
        }

        return new self(
            id: Base64Url::decode($row['id'] ?? null, AuthenticatorData::MAX_CREDENTIAL_ID_BYTES),
            publicKey: PublicKey::fromStored($algorithm, Base64Url::decode($row['publicKey'] ?? null, 1024)),
            signCount: $signCount,
            name: self::normalizeName($row['name'] ?? null),
            transports: self::normalizeTransports($row['transports'] ?? []),
            createdAt: $createdAt,
            lastUsedAt: $lastUsedAt,
        );
    }

    /**
     * @return array<string, mixed>
     */
    public function toArray(): array
    {
        return [
            'id' => Base64Url::encode($this->id),
            'algorithm' => $this->publicKey->algorithm,
            'publicKey' => Base64Url::encode($this->publicKey->der),
            'signCount' => $this->signCount,
            'name' => $this->name,
            'transports' => $this->transports,
            'createdAt' => $this->createdAt,
            'lastUsedAt' => $this->lastUsedAt,
        ];
    }

    public function withUse(int $signCount, string $at): self
    {
        return new self($this->id, $this->publicKey, $signCount, $this->name, $this->transports, $this->createdAt, $at);
    }
}
