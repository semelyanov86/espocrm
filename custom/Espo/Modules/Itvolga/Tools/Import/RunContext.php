<?php

namespace Espo\Modules\Itvolga\Tools\Import;

use stdClass;

/**
 * What a protocol-3 writer session may do beyond upserts (stage 06.4, docs/migration/import.md «Дельта»): the source key
 * range of the run (real keys or a test block) and the entity types whose every source module is part of it. Only
 * records of those types with a key in the range are removed, and only link items pointing to such records are owned
 * by the source. Protocols 1 and 2 get an empty context: no removal, add-only links.
 */
final class RunContext
{
    /**
     * @param ?array{int, int} $keyRange
     * @param string[] $ownedTypes
     */
    private function __construct(
        public readonly ?string $adoptUserName,
        private readonly ?array $keyRange,
        private readonly array $ownedTypes,
    ) {}

    public static function fromHeader(stdClass $header): self
    {
        $adopt = is_string($header->adoptUserName ?? null) ? $header->adoptUserName : null;

        if (($header->protocol ?? null) !== 3) {
            return new self($adopt, null, []);
        }

        $range = $header->keyRange ?? null;
        $types = $header->ownedTypes ?? null;

        if (!is_array($range) || count($range) !== 2 || !is_int($range[0]) || !is_int($range[1]) || $range[0] < 1 ||
            $range[0] > $range[1] || !is_array($types) || array_filter($types, static fn ($t) => !is_string($t))) {
            throw new ImportError('bad_header');
        }

        return new self($adopt, [$range[0], $range[1]], array_values(array_intersect($types, RecordWriter::ENTITY_TYPES)));
    }

    public function removalsEnabled(): bool
    {
        return $this->keyRange !== null;
    }

    public function ownsType(string $entityType): bool
    {
        return in_array($entityType, $this->ownedTypes, true) && !isset(KeyResolver::NATURAL_KEYS[$entityType]);
    }

    public function inRange(mixed $key): bool
    {
        return $this->keyRange !== null && is_int($key) && $key >= $this->keyRange[0] && $key <= $this->keyRange[1];
    }

    /**
     * @return ?array{int, int}
     */
    public function keyRange(): ?array
    {
        return $this->keyRange;
    }
}
