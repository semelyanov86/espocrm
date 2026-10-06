<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\SecurityKey\Core\Cbor;

/**
 * A CBOR map with integer and text keys (the only ones WebAuthn uses). The integer 1 and the text "1" are different
 * keys, which a PHP array would merge; the decoder refuses a repeated key.
 */
final class CborMap
{
    /** @var array<string, mixed> */
    private array $items = [];

    public static function slot(int|string $key): string
    {
        return is_int($key) ? 'i:' . $key : 't:' . $key;
    }

    /**
     * @return bool False when the key is already present.
     */
    public function add(int|string $key, mixed $value): bool
    {
        $slot = self::slot($key);

        if (array_key_exists($slot, $this->items)) {
            return false;
        }

        $this->items[$slot] = $value;

        return true;
    }

    public function has(int|string $key): bool
    {
        return array_key_exists(self::slot($key), $this->items);
    }

    public function get(int|string $key): mixed
    {
        return $this->items[self::slot($key)] ?? null;
    }

    public function count(): int
    {
        return count($this->items);
    }
}
