<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Hooks\Call;

use Espo\Core\Exceptions\Error\Body;
use Espo\Core\Exceptions\Forbidden;
use Espo\Core\Hook\Hook\BeforeSave;
use Espo\Modules\Itvolga\Tools\Telephony\CallFacts;
use Espo\ORM\Entity;
use Espo\ORM\EntityManager;
use Espo\ORM\Query\SelectBuilder;
use Espo\ORM\Repository\Option\SaveOptions;
use Espo\ORM\Util;

/**
 * The facts of a telephony Call change only through the Asterisk integration (D-168). The API, the form and mass
 * update drop them already (logicDefs readOnlySaved, readOnly fields); this guard covers every other write path —
 * the import tool (it saves with SaveOption::IMPORT too, so IMPORT is not trusted), formula, console, hooks, the
 * system user. A Call cannot become or stop being a telephony call either. Order 45, as FinanceNumberGuard.
 *
 * An existing Call saved without its stored key (an entity built by id and marked not new, never fetched) is compared
 * with its stored row: otherwise its empty fetched key would pass it off as a plain call (external review 2026-10-17).
 *
 * @implements BeforeSave<Entity>
 */
class TelephonyFacts implements BeforeSave
{
    public const LABEL = 'telephonyFactsReadOnly';

    public static int $order = 45;

    public function __construct(private EntityManager $entityManager) {}

    public function beforeSave(Entity $entity, SaveOptions $options): void
    {
        if ($options->get(CallFacts::SAVE_OPTION)) {
            return;
        }

        if ($entity->isNew()) {
            if ((string) $entity->get(CallFacts::KEY) !== '') {
                throw self::refused();
            }

            return;
        }

        if (!$entity->hasFetched(CallFacts::KEY)) {
            $this->checkAgainstStored($entity);

            return;
        }

        if ((string) $entity->get(CallFacts::KEY) === '' && (string) $entity->getFetched(CallFacts::KEY) === '') {
            return;
        }

        foreach (CallFacts::ATTRIBUTES as $attribute) {
            if ($entity->has($attribute) && $entity->isAttributeChanged($attribute)) {
                throw self::refused();
            }
        }
    }

    private function checkAgainstStored(Entity $entity): void
    {
        $query = SelectBuilder::create()
            ->from('Call')
            ->select(['id', ...CallFacts::ATTRIBUTES])
            ->where(['id' => $entity->getId()])
            ->withDeleted()
            ->build();
        $stored = $this->entityManager->getRDBRepository('Call')->clone($query)->findOne();

        if ((string) $entity->get(CallFacts::KEY) === '' && (string) $stored?->get(CallFacts::KEY) === '') {
            return;
        }

        foreach (CallFacts::ATTRIBUTES as $attribute) {
            if (!$entity->has($attribute)) {
                continue;
            }

            if ($stored === null || !Util::areValuesEqual((string) $entity->getAttributeType($attribute),
                    $entity->get($attribute), $stored->get($attribute))) {
                throw self::refused();
            }
        }
    }

    private static function refused(): Forbidden
    {
        return Forbidden::createWithBody(self::LABEL, Body::create()->withMessageTranslation(self::LABEL, 'Call'));
    }
}
