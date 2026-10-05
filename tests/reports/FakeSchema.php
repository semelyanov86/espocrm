<?php

declare(strict_types=1);

namespace Itvolga\Tests\Reports;

use Espo\Modules\Itvolga\Tools\Report\Core\Definition\FieldForbidden;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\FieldInfo;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\FieldRef;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\Schema;

/**
 * A small synthetic model for the definition tests: Invoice with a to-one link `account` and a to-many link `items`.
 * Fields named `secret*` and the entity `Secret` stand for ACL-closed ones; `vtigerData` for a technical one.
 * Every field() call is recorded, which lets the tests prove each section is checked.
 */
final class FakeSchema implements Schema
{
    /** @var list<string> */
    public array $calls = [];

    private const ENTITIES = [
        'Invoice' => [
            'name' => 'varchar', 'status' => 'enum', 'grandTotal' => 'currency', 'dateInvoiced' => 'date',
            'dateDue' => 'date', 'createdAt' => 'datetime', 'account' => 'link:Account',
            'assignedUser' => 'link:User', 'teams' => 'linkMultiple:Team', 'description' => 'text',
            'secretNote' => 'varchar', 'number' => 'varchar', 'paid' => 'bool', 'cTags' => 'multiEnum',
        ],
        'Account' => ['name' => 'varchar', 'industry' => 'enum', 'cEmployees' => 'int', 'secretInn' => 'varchar',
            'createdAt' => 'datetime', 'assignedUser' => 'link:User'],
        'InvoiceItem' => ['quantity' => 'decimal', 'amount' => 'currency', 'product' => 'link:Product',
            'name' => 'varchar'],
        'Contact' => ['name' => 'personName', 'lastName' => 'varchar'],
    ];
    private const LINKS = ['Invoice' => ['account' => ['Account', FieldInfo::LINK_ONE],
        'items' => ['InvoiceItem', FieldInfo::LINK_MANY], 'contacts' => ['Contact', FieldInfo::LINK_MANY]]];

    public function assertEntity(string $entityType): void
    {
        if ($entityType === 'Secret') {
            throw new FieldForbidden('entityForbidden', 'entityType');
        }
    }

    public function field(string $entityType, FieldRef $ref): ?FieldInfo
    {
        $this->calls[] = $ref->toString();
        $owner = $entityType;
        $kind = FieldInfo::LINK_NONE;

        if ($ref->link !== null) {
            [$owner, $kind] = self::LINKS[$entityType][$ref->link] ?? [null, null];

            if ($owner === null) {
                return null;
            }
        }

        if (str_starts_with($ref->field, 'secret')) {
            throw new FieldForbidden('fieldForbidden', '', ['field' => $ref->toString()]);
        }

        $type = self::ENTITIES[$owner][$ref->field] ?? null;

        if ($type === null) {
            return null;
        }

        [$type, $foreign] = array_pad(explode(':', $type), 2, null);
        $attributes = match ($type) {
            'link' => [$ref->field . 'Id'],
            'linkMultiple' => [$ref->field],
            'currency' => [$ref->field, $ref->field . 'Currency'],
            default => [$ref->field],
        };

        return new FieldInfo($ref, $type, $owner, $kind, $foreign, $attributes,
            $type === 'enum' ? ['Draft', 'Sent', 'Paid'] : []);
    }
}
