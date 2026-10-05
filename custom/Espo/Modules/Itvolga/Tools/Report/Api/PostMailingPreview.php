<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Api;

use Espo\Core\Acl;
use Espo\Core\Api\Action;
use Espo\Core\Api\Request;
use Espo\Core\Api\Response;
use Espo\Core\Api\ResponseComposer;
use Espo\Core\Exceptions\BadRequest;
use Espo\Core\Exceptions\Forbidden;
use Espo\Core\Utils\Json;
use Espo\Entities\User;
use Espo\Modules\Itvolga\Entities\Report;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\DefinitionError;
use Espo\Modules\Itvolga\Tools\Report\Core\Mailing\MailingSettings;
use Espo\Modules\Itvolga\Tools\Report\Core\Mailing\MailingSettingsParser;
use Espo\Modules\Itvolga\Tools\Report\Format\FormatContextFactory;
use Espo\Modules\Itvolga\Tools\Report\Mailing\MailingClock;
use Espo\ORM\EntityManager;
use Throwable;

/**
 * POST /Report/mailingPreview {mailing, assignedUserId?, id?} — the next run of a mailing being edited (step 9 of the
 * builder, D-121), by the rule of the save: the stored slot of a report the user may edit when its schedule and owner
 * stay (an anchor of every two weeks — external review 05.3 W3), else the first slot by the wall clock of the owner
 * (only an administrator names another owner). Answer: {nextRunAt: UTC|null, text: in the user's notation with the
 * owner's time zone} or {error: translated} for settings the save would refuse. Nothing is written.
 */
class PostMailingPreview implements Action
{
    public function __construct(
        private User $user,
        private Acl $acl,
        private MailingClock $clock,
        private FormatContextFactory $formatContextFactory,
        private EntityManager $entityManager,
    ) {}

    public function process(Request $request): Response
    {
        $raw = json_decode(Json::encode($request->getParsedBody()), true);

        if (!is_array($raw)) {
            throw new BadRequest();
        }

        if (!$this->acl->checkScope('Report', Acl\Table::ACTION_CREATE) &&
            !$this->acl->checkScope('Report', Acl\Table::ACTION_EDIT)) {
            throw new Forbidden();
        }

        $ownerId = is_string($raw['assignedUserId'] ?? null) && $raw['assignedUserId'] !== '' ?
            $raw['assignedUserId'] : $this->user->getId();

        if ($ownerId !== $this->user->getId() && !$this->user->isAdmin()) {
            throw new Forbidden();
        }

        $context = $this->formatContextFactory->create($this->user);

        try {
            $settings = MailingSettingsParser::parse($raw['mailing'] ?? null);
        } catch (DefinitionError $e) {
            return ResponseComposer::json(['nextRunAt' => null, 'text' => null,
                'error' => $context->language->translateLabel($e->key, 'messages', 'Report')]);
        }

        $next = $this->stored($raw['id'] ?? null, $settings, $ownerId) ?? $this->clock->first($settings, $ownerId);
        $text = $next === null ? null : $context->dateTime->convertSystemDateTime($next,
            $this->clock->zone($ownerId)->getName(), $context->dateFormat . ' ' . $context->timeFormat,
            $context->languageCode) . ' (' . $this->clock->zone($ownerId)->getName() . ')';

        return ResponseComposer::json(['nextRunAt' => $next, 'text' => $text, 'error' => null]);
    }

    /**
     * The slot a save would keep (Hooks/Report/Mailing): same owner, same enabled schedule, a stored next run.
     */
    private function stored(mixed $id, ?MailingSettings $settings, string $ownerId): ?string
    {
        if (!is_string($id) || $id === '' || !$settings?->enabled) {
            return null;
        }

        $report = $this->entityManager->getRDBRepositoryByClass(Report::class)->getById($id);

        if (!$report || !$this->acl->checkEntityEdit($report) || $report->get('assignedUserId') !== $ownerId) {
            return null;
        }

        try {
            $before = MailingSettingsParser::parse($report->get('mailing'));
        } catch (Throwable) {
            return null;
        }

        $next = $report->get('mailingNextRunAt');

        return $before?->schedule() === $settings->schedule() && is_string($next) ? $next : null;
    }
}
