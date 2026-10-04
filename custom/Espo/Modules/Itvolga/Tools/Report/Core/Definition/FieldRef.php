<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Definition;

/**
 * A field of the main entity ("status") or of an entity one link away ("account.industry") — the stable column id of
 * reports (reports.md §2). Names only: whether the field exists and may be used is the Schema's answer.
 */
final class FieldRef
{
    private const PATTERN = '/^([a-z][a-zA-Z0-9]{0,99})(?:\.([a-z][a-zA-Z0-9]{0,99}))?$/';

    private function __construct(
        public readonly ?string $link,
        public readonly string $field,
    ) {}

    public static function parse(mixed $value): ?self
    {
        if (!is_string($value) || !preg_match(self::PATTERN, $value, $m)) {
            return null;
        }

        return isset($m[2]) ? new self($m[1], $m[2]) : new self(null, $m[1]);
    }

    public static function of(?string $link, string $field): self
    {
        $ref = self::parse($link === null ? $field : "$link.$field");

        if ($ref === null) {
            throw new DefinitionError('badField', '');
        }

        return $ref;
    }

    public function isRelated(): bool
    {
        return $this->link !== null;
    }

    public function toString(): string
    {
        return $this->link === null ? $this->field : "$this->link.$this->field";
    }
}
