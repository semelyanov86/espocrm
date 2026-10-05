<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Classes\FieldProcessing\Report;

use Espo\Core\Acl;
use Espo\Core\FieldProcessing\Loader;
use Espo\Core\FieldProcessing\Loader\Params;
use Espo\Core\Utils\Language;
use Espo\Entities\Team;
use Espo\Entities\User;
use Espo\Modules\Itvolga\Tools\Report\Core\Mailing\MailingSettingsParser;
use Espo\Modules\Itvolga\Tools\Report\Mailing\ReadableNames;
use Espo\ORM\Entity;
use Throwable;

/**
 * `mailingSettings` of a read report (D-124): the stored mailing is `internal` — never in an API answer, never in a
 * filter — and this is what a reader sees of it. Who may edit the report (the owner, an administrator) gets the whole
 * part with the names of the chosen users and teams he may read (others — «(нет доступа)», external review 05.3 B5)
 * and the last attempt; any other reader — when the letters go and in which formats, without recipients, addresses,
 * subject or text.
 */
class MailingLoader implements Loader
{
    public function __construct(
        private Acl $acl,
        private User $user,
        private ReadableNames $readableNames,
        private Language $language,
    ) {}

    public function process(Entity $entity, Params $params): void
    {
        try {
            $settings = MailingSettingsParser::parse($entity->get('mailing'));
        } catch (Throwable) {
            $settings = null;
        }

        if ($settings === null) {
            $entity->set('mailingSettings', null);

            return;
        }

        if (!$this->acl->checkEntityEdit($entity)) {
            $entity->set('mailingSettings', (object) ($settings->schedule() + ['formats' => $settings->formats]));

            return;
        }

        $entity->set('mailingSettings', (object) ($settings->toArray() + [
            'names' => [
                'users' => $this->names(User::ENTITY_TYPE, $settings->users),
                'teams' => $this->names(Team::ENTITY_TYPE, $settings->teams),
            ],
            'lastRunAt' => $entity->get('mailingLastRunAt'),
            'lastResult' => $entity->get('mailingLastResult'),
        ]));
    }

    /**
     * @param list<string> $ids
     * @return object id → name
     */
    private function names(string $entityType, array $ids): object
    {
        $readable = $this->readableNames->of($this->user, $entityType, $ids);
        $noAccess = $this->language->translateLabel('noAccessRecord', 'labels', 'Report');
        $names = [];

        foreach ($ids as $id) {
            $names[$id] = $readable[$id] ?? $noAccess;
        }

        return (object) $names;
    }
}
