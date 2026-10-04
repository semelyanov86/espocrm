<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Definition;

/**
 * The field (or its link, or its entity) is closed to the user by ACL (D-99): the run or the save is refused (403)
 * instead of dropping the field silently.
 */
final class FieldForbidden extends DefinitionError
{
}
