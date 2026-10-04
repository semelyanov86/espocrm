<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Classes\Record\ReportFolder;

use Espo\Core\Exceptions\Error\Body;
use Espo\Core\Exceptions\Forbidden;
use Espo\Core\Record\Deleted\Restorer as RestorerInterface;
use Espo\ORM\Entity;

/**
 * Report folders are not restored (external review B9): the core category tree deletes a folder row, and the row a
 * removed standard folder leaves behind only tells the seed not to bring it back (Repositories\ReportFolder). A plain
 * restore would skip the name check and the category paths; a new folder of the same name is made instead.
 *
 * @implements RestorerInterface<Entity>
 */
final class Restorer implements RestorerInterface
{
    public function restore(Entity $entity): void
    {
        throw Forbidden::createWithBody('folderRestoreDisabled',
            Body::create()->withMessageTranslation('folderRestoreDisabled', 'ReportFolder'));
    }
}
