<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Hooks\Call;

use Espo\Core\Exceptions\Error\Body;
use Espo\Core\Exceptions\Forbidden;
use Espo\Core\Hook\Hook\BeforeSave;
use Espo\Modules\Itvolga\Tools\Telephony\CallFacts;
use Espo\ORM\Entity;
use Espo\ORM\Repository\Option\SaveOptions;

/**
 * The facts of a telephony Call change only through the Asterisk integration (D-168). The API, the form and mass
 * update drop them already (logicDefs readOnlySaved, readOnly fields); this guard covers every other write path —
 * the import tool (it saves with SaveOption::IMPORT too, so IMPORT is not trusted), formula, console, hooks, the
 * system user. A Call cannot become or stop being a telephony call either. Order 45, as FinanceNumberGuard.
 *
 * @implements BeforeSave<Entity>
 */
class TelephonyFacts implements BeforeSave
{
    public const LABEL = 'telephonyFactsReadOnly';

    public static int $order = 45;

    public function beforeSave(Entity $entity, SaveOptions $options): void
    {
        if ($options->get(CallFacts::SAVE_OPTION)) {
            return;
        }

        $isTelephony = (string) $entity->get(CallFacts::KEY) !== '' ||
            (!$entity->isNew() && (string) $entity->getFetched(CallFacts::KEY) !== '');

        if (!$isTelephony) {
            return;
        }

        if ($entity->isNew()) {
            throw self::refused();
        }

        foreach (CallFacts::ATTRIBUTES as $attribute) {
            if ($entity->has($attribute) && $entity->isAttributeChanged($attribute)) {
                throw self::refused();
            }
        }
    }

    private static function refused(): Forbidden
    {
        return Forbidden::createWithBody(self::LABEL, Body::create()->withMessageTranslation(self::LABEL, 'Call'));
    }
}
