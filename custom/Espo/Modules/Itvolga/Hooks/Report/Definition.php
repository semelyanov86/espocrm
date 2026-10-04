<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Hooks\Report;

use Espo\Core\Exceptions\BadRequest;
use Espo\Core\Exceptions\Error\Body;
use Espo\Core\Exceptions\Forbidden;
use Espo\Core\Hook\Hook\BeforeSave;
use Espo\Core\ORM\Entity as CoreEntity;
use Espo\Entities\User;
use Espo\Modules\Itvolga\Entities\Report;
use Espo\Modules\Itvolga\Entities\ReportFolder;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\DefinitionError;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\DefinitionParser;
use Espo\Modules\Itvolga\Tools\Report\ErrorMapper;
use Espo\Modules\Itvolga\Tools\Report\Run\ReportRunner;
use Espo\Modules\Itvolga\Tools\Report\Schema\SchemaFactory;
use Espo\ORM\Entity;
use Espo\Modules\Itvolga\Tools\FinanceDocument\RowLock;
use Espo\ORM\EntityManager;
use Espo\ORM\Repository\Option\SaveOptions;

/**
 * Every save of a report — API, console, seed, mass update (D-101), also one that changes no definition part: the
 * definition is checked by the rules of reports.md and with the ACL of the acting user (a field closed to him is
 * refused: 403) and stored in its canonical form; the type and the main entity never change after creation; a shared
 * report lists at least one user or team, the lists of other access types are cleared; only an administrator gives a
 * report to another owner; a report without folder goes to «Общие».
 *
 * The folder of a new or moved report is read with a lock that the save transaction holds until the report is stored
 * (Repositories\Report), so a folder being removed meanwhile is never left with this report (D-88).
 *
 * @implements BeforeSave<Report>
 */
class Definition implements BeforeSave
{
    public static int $order = 10;

    public function __construct(
        private SchemaFactory $schemaFactory,
        private User $user,
        private EntityManager $entityManager,
        private RowLock $rowLock,
    ) {}

    public function beforeSave(Entity $entity, SaveOptions $options): void
    {
        assert($entity instanceof CoreEntity);

        if (!$entity->isNew()) {
            foreach (['type', 'entityType'] as $attribute) {
                if ($entity->isAttributeChanged($attribute)) {
                    throw self::badRequest('readOnlyAfterCreate', ['field' => $attribute]);
                }
            }
        }

        $this->checkOwner($entity);
        $this->checkAccess($entity);

        if (!$entity->get('folderId')) {
            $general = $this->entityManager->getRDBRepositoryByClass(ReportFolder::class)
                ->where(['isSystem' => true])
                ->findOne();
            $entity->set('folderId', $general?->getId());
        } elseif ($entity->isAttributeChanged('folderId') &&
            !$this->rowLock->one(ReportFolder::ENTITY_TYPE, (string) $entity->get('folderId'))) {
            // A locking read waits for a folder being removed (D-88) and then finds it gone.
            throw self::badRequest('folderNotFound', []);
        }

        try {
            $definition = (new DefinitionParser($this->schemaFactory->create($this->user)))
                ->parse(ReportRunner::attributes($entity));
        } catch (DefinitionError $e) {
            throw ErrorMapper::toHttp($e);
        }

        foreach ($definition->toAttributes() as $attribute => $value) {
            $entity->set($attribute, is_array($value) && !array_is_list($value) ?
                json_decode((string) json_encode($value)) : $value);
        }
    }

    private function checkOwner(CoreEntity $entity): void
    {
        if ($this->user->isAdmin()) {
            return;
        }

        $owner = $entity->get('assignedUserId');

        if ($entity->isNew() ? $owner !== $this->user->getId() : $entity->isAttributeChanged('assignedUserId')) {
            throw new Forbidden('Only an administrator gives a report to another owner.');
        }
    }

    private function checkAccess(CoreEntity $entity): void
    {
        $accessType = $entity->get('accessType') ?: Report::ACCESS_PRIVATE;
        $entity->set('accessType', $accessType);

        if ($accessType !== Report::ACCESS_SHARED) {
            foreach (['sharedUsers', 'sharedTeams'] as $field) {
                if ($entity->isNew() ? ($entity->get($field . 'Ids') ?? []) !== [] :
                    $entity->getLinkMultipleIdList($field) !== []) {
                    $entity->setLinkMultipleIdList($field, []);
                }
            }

            return;
        }

        $users = $entity->has('sharedUsersIds') || $entity->isNew() ? ($entity->get('sharedUsersIds') ?? []) :
            $entity->getLinkMultipleIdList('sharedUsers');
        $teams = $entity->has('sharedTeamsIds') || $entity->isNew() ? ($entity->get('sharedTeamsIds') ?? []) :
            $entity->getLinkMultipleIdList('sharedTeams');

        if ($users === [] && $teams === []) {
            throw self::badRequest('sharedNeedsList', []);
        }
    }

    /**
     * @param array<string, string> $data
     */
    private static function badRequest(string $label, array $data): BadRequest
    {
        return BadRequest::createWithBody($label, Body::create()->withMessageTranslation($label, 'Report', $data));
    }
}
