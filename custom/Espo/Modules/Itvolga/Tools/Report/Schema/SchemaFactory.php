<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Schema;

use Espo\Core\AclManager;
use Espo\Core\Utils\FieldUtil;
use Espo\Core\Utils\Metadata;
use Espo\Entities\User;
use Espo\ORM\EntityManager;

/**
 * The report schema of a given user: the runner, a recipient of a mailing (05.3) or the saver of a definition.
 */
final class SchemaFactory
{
    public function __construct(
        private readonly AclManager $aclManager,
        private readonly Metadata $metadata,
        private readonly EntityManager $entityManager,
        private readonly FieldUtil $fieldUtil,
    ) {}

    public function create(User $user): MetadataSchema
    {
        return new MetadataSchema($user, $this->aclManager->createUserAcl($user), $this->metadata,
            $this->entityManager->getDefs(), $this->fieldUtil);
    }
}
