<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Hooks\Report;

use Espo\Core\Exceptions\BadRequest;
use Espo\Core\Exceptions\Error\Body;
use Espo\Core\Exceptions\Forbidden;
use Espo\Core\Hook\Hook\BeforeSave;
use Espo\Core\ORM\Entity as CoreEntity;
use Espo\Entities\Team;
use Espo\Entities\User;
use Espo\Modules\Itvolga\Entities\Report;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\DefinitionError;
use Espo\Modules\Itvolga\Tools\Report\Core\Mailing\MailingSettings;
use Espo\Modules\Itvolga\Tools\Report\Core\Mailing\MailingSettingsParser;
use Espo\Modules\Itvolga\Tools\Report\ErrorMapper;
use Espo\Modules\Itvolga\Tools\Report\Export\ExportAccess;
use Espo\Modules\Itvolga\Tools\Report\Mailing\MailingClock;
use Espo\Modules\Itvolga\Tools\Report\Schema\SchemaFactory;
use Espo\ORM\Entity;
use Espo\ORM\EntityManager;
use Espo\ORM\Repository\Option\SaveOptions;
use Throwable;

/**
 * The mailing part of a save (D-121), after the definition hook rebased the save on the committed row: when the mailing
 * or the owner changes, the part is checked — its structure, the «generate for» links with the ACL of the acting user,
 * the recipients exist, the owner of an enabled mailing may export (D-126) — and stored canonical; a new owner given
 * with the mailing left as it was switches it off (his rights are not lent without a decision); the next slot is
 * computed anew only when the schedule, its switch or the owner changes (a new subject or recipients keep the rhythm
 * of every two weeks). Who may save a report — its owner or an administrator — is the edit access of the report.
 *
 * @implements BeforeSave<Report>
 */
class Mailing implements BeforeSave
{
    public static int $order = 20;

    public function __construct(
        private SchemaFactory $schemaFactory,
        private User $user,
        private EntityManager $entityManager,
        private ExportAccess $exportAccess,
        private MailingClock $clock,
    ) {}

    public function beforeSave(Entity $entity, SaveOptions $options): void
    {
        assert($entity instanceof CoreEntity);

        $ownerChanged = !$entity->isNew() && $entity->isAttributeChanged('assignedUserId');

        if (!$entity->isNew() && !$entity->isAttributeChanged('mailing') && !$ownerChanged) {
            return;
        }

        try {
            $settings = MailingSettingsParser::parse($entity->get('mailing'));

            if ($settings !== null) {
                MailingSettingsParser::generateFor($settings, (string) $entity->get('entityType'),
                    $this->schemaFactory->create($this->user));
            }
        } catch (DefinitionError $e) {
            throw ErrorMapper::toHttp($e);
        }

        if ($settings === null) {
            $entity->set('mailing', null);
            $entity->set('mailingNextRunAt', null);

            return;
        }

        if ($ownerChanged && $settings->enabled && !$entity->isAttributeChanged('mailing')) {
            // The mailing runs with the owner's rights: a new owner (only an administrator gives a report away) lends
            // them to recipients chosen by the previous one only by an explicit decision — the mailing is switched off.
            $settings = MailingSettingsParser::parse(['enabled' => false] + $settings->toArray());
            assert($settings !== null);
        }

        $this->checkRecipients($settings);
        $ownerId = $entity->get('assignedUserId') ? (string) $entity->get('assignedUserId') : null;

        if ($settings->enabled) {
            $owner = $ownerId ? $this->entityManager->getRDBRepositoryByClass(User::class)->getById($ownerId) : null;

            if (!$owner || !$this->exportAccess->canExport($owner)) {
                throw Forbidden::createWithBody('mailingNeedsExport',
                    Body::create()->withMessageTranslation('mailingNeedsExport', 'Report'));
            }
        }

        $entity->set('mailing', (object) $settings->toArray());

        try {
            $before = MailingSettingsParser::parse($entity->getFetched('mailing'));
        } catch (Throwable) {
            $before = null;
        }

        if ($entity->isNew() || $ownerChanged || $before?->schedule() !== $settings->schedule() ||
            $settings->enabled && !$entity->get('mailingNextRunAt')) {
            $entity->set('mailingNextRunAt', $this->clock->first($settings, $ownerId));
        }
    }

    /**
     * @throws BadRequest
     */
    private function checkRecipients(MailingSettings $settings): void
    {
        foreach ([User::ENTITY_TYPE => $settings->users, Team::ENTITY_TYPE => $settings->teams] as $type => $ids) {
            if ($ids !== [] && $this->entityManager->getRDBRepository($type)->where(['id' => $ids])->count() !==
                count($ids)) {
                throw BadRequest::createWithBody('mailingUnknownRecipient',
                    Body::create()->withMessageTranslation('mailingUnknownRecipient', 'Report'));
            }
        }
    }
}
