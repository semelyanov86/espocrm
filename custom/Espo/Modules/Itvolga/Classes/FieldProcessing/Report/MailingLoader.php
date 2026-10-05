<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Classes\FieldProcessing\Report;

use Espo\Core\Acl;
use Espo\Core\FieldProcessing\Loader;
use Espo\Core\FieldProcessing\Loader\Params;
use Espo\Entities\Team;
use Espo\Entities\User;
use Espo\Modules\Itvolga\Tools\Report\Core\Mailing\MailingSettingsParser;
use Espo\ORM\Entity;
use Espo\ORM\EntityManager;
use Throwable;

/**
 * `mailingSettings` of a read report (D-124): the stored mailing is `internal` — never in an API answer, never in a
 * filter — and this is what a reader sees of it. Who may edit the report (the owner, an administrator) gets the whole
 * part with the names of the chosen users and teams and the last attempt; any other reader — when the letters go and
 * in which formats, without recipients, addresses, subject or text.
 */
class MailingLoader implements Loader
{
    public function __construct(
        private Acl $acl,
        private EntityManager $entityManager,
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
        $names = [];

        if ($ids !== []) {
            foreach ($this->entityManager->getRDBRepository($entityType)->select(['id', 'name'])
                ->where(['id' => $ids])->find() as $record) {
                $names[$record->getId()] = (string) $record->get('name');
            }
        }

        return (object) $names;
    }
}
