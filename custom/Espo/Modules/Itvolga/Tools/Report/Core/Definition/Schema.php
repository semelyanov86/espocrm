<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Definition;

/**
 * What the definition parser needs to know about the model, for one user (implemented over metadata and ACL by
 * Tools/Report/Schema/MetadataSchema; by a fake in the unit tests). Every field the definition mentions — in any
 * section — goes through field(), which is how the ACL check covers all usages (D-99).
 */
interface Schema
{
    /**
     * @throws FieldForbidden the entity is not readable by the user (or admin-only)
     */
    public function assertEntity(string $entityType): void;

    /**
     * Null: no such field or a technical one (not usable in reports).
     *
     * @throws FieldForbidden the field, its link or the foreign entity is closed to the user
     */
    public function field(string $entityType, FieldRef $ref): ?FieldInfo;
}
