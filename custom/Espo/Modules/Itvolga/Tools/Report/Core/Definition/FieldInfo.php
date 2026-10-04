<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Definition;

/**
 * A usable field resolved by the Schema: its type, the entity that owns it, how it is reached from the main entity
 * and what a report may do with it (reports.md §3).
 */
final class FieldInfo
{
    public const LINK_NONE = 'none';
    public const LINK_ONE = 'one';
    public const LINK_MANY = 'many';

    public const FAMILY_TEXT = 'text';
    public const FAMILY_LONG_TEXT = 'longText';
    public const FAMILY_ENUM = 'enum';
    public const FAMILY_MULTI_ENUM = 'multiEnum';
    public const FAMILY_NUMBER = 'number';
    public const FAMILY_BOOL = 'bool';
    public const FAMILY_DATE = 'date';
    public const FAMILY_DATETIME = 'datetime';
    public const FAMILY_LINK = 'link';
    public const FAMILY_LINK_MULTIPLE = 'linkMultiple';
    public const FAMILY_LINK_PARENT = 'linkParent';

    private const FAMILIES = [
        'varchar' => self::FAMILY_TEXT, 'email' => self::FAMILY_TEXT, 'phone' => self::FAMILY_TEXT,
        'url' => self::FAMILY_TEXT, 'personName' => self::FAMILY_TEXT, 'number' => self::FAMILY_TEXT,
        'autoincrement' => self::FAMILY_NUMBER, 'barcode' => self::FAMILY_TEXT,
        'text' => self::FAMILY_LONG_TEXT, 'wysiwyg' => self::FAMILY_LONG_TEXT,
        'enum' => self::FAMILY_ENUM, 'colorpicker' => self::FAMILY_TEXT,
        'multiEnum' => self::FAMILY_MULTI_ENUM, 'array' => self::FAMILY_MULTI_ENUM, 'checklist' => self::FAMILY_MULTI_ENUM,
        'int' => self::FAMILY_NUMBER, 'float' => self::FAMILY_NUMBER, 'decimal' => self::FAMILY_NUMBER,
        'currency' => self::FAMILY_NUMBER,
        'bool' => self::FAMILY_BOOL,
        'date' => self::FAMILY_DATE, 'datetime' => self::FAMILY_DATETIME, 'datetimeOptional' => self::FAMILY_DATETIME,
        'link' => self::FAMILY_LINK, 'linkOne' => self::FAMILY_LINK, 'file' => self::FAMILY_LINK,
        'image' => self::FAMILY_LINK,
        'linkMultiple' => self::FAMILY_LINK_MULTIPLE,
        'linkParent' => self::FAMILY_LINK_PARENT,
    ];

    /**
     * @param string $type EspoCRM field type
     * @param string $entityType the entity owning the field (the main one or the foreign one of the link)
     * @param string $linkKind LINK_NONE (field of the main entity), LINK_ONE or LINK_MANY (reached by ref->link)
     * @param ?string $foreignEntityType target of a link-type field
     * @param list<string> $whereAttributes attributes a filter of this field may use
     * @param list<string> $options options of an enum field
     */
    public function __construct(
        public readonly FieldRef $ref,
        public readonly string $type,
        public readonly string $entityType,
        public readonly string $linkKind,
        public readonly ?string $foreignEntityType = null,
        public readonly array $whereAttributes = [],
        public readonly array $options = [],
    ) {}

    public function family(): ?string
    {
        return self::FAMILIES[$this->type] ?? null;
    }

    public function isNumeric(): bool
    {
        return $this->family() === self::FAMILY_NUMBER && $this->type !== 'autoincrement';
    }

    public function isDate(): bool
    {
        return in_array($this->family(), [self::FAMILY_DATE, self::FAMILY_DATETIME], true);
    }

    public function isCurrency(): bool
    {
        return $this->type === 'currency';
    }

    public function isUserLink(): bool
    {
        return $this->family() === self::FAMILY_LINK && $this->foreignEntityType === 'User';
    }

    public function canColumn(): bool
    {
        return $this->family() !== null && $this->family() !== self::FAMILY_LINK_MULTIPLE &&
            !($this->linkKind !== self::LINK_NONE && $this->family() === self::FAMILY_LINK_PARENT);
    }

    public function canGroup(): bool
    {
        return in_array($this->family(), [self::FAMILY_TEXT, self::FAMILY_ENUM, self::FAMILY_NUMBER, self::FAMILY_BOOL,
            self::FAMILY_DATE, self::FAMILY_DATETIME, self::FAMILY_LINK], true) && $this->type !== 'personName';
    }

    /**
     * A related link is not sortable: its name is not joined, only its id.
     */
    public function canSort(): bool
    {
        if ($this->family() === self::FAMILY_LINK && $this->linkKind !== self::LINK_NONE) {
            return false;
        }

        return $this->canGroup() || $this->type === 'personName';
    }

    /**
     * Quick filters list the actual values of the field: main or to-one fields of short value sets only.
     */
    public function canQuickFilter(): bool
    {
        if ($this->linkKind === self::LINK_MANY || $this->type === 'personName') {
            return false;
        }

        return in_array($this->family(), [self::FAMILY_TEXT, self::FAMILY_ENUM, self::FAMILY_BOOL, self::FAMILY_LINK],
            true) || $this->type === 'int';
    }

    public function canFilter(): bool
    {
        if ($this->family() === null) {
            return false;
        }

        // linkMultiple and parent links only on the main entity: their where types work on relations of the main one.
        if ($this->linkKind !== self::LINK_NONE &&
            in_array($this->family(), [self::FAMILY_LINK_MULTIPLE, self::FAMILY_LINK_PARENT], true)) {
            return false;
        }

        return true;
    }
}
