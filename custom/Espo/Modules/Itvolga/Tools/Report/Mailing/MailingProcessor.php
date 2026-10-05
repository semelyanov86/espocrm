<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Mailing;

use Espo\Core\AclManager;
use Espo\Entities\Attachment;
use Espo\Entities\User;
use Espo\Modules\Itvolga\Entities\Report;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\DefinitionError;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\FieldForbidden;
use Espo\Modules\Itvolga\Tools\Report\Core\Export\ExportRequest;
use Espo\Modules\Itvolga\Tools\Report\Core\Mailing\DiscoveryFilters;
use Espo\Modules\Itvolga\Tools\Report\Core\Mailing\MailingSettings;
use Espo\Modules\Itvolga\Tools\Report\Core\Mailing\MailingSettingsParser;
use Espo\Modules\Itvolga\Tools\Report\Export\AttachmentStore;
use Espo\Modules\Itvolga\Tools\Report\Export\ExportAccess;
use Espo\Modules\Itvolga\Tools\Report\Export\ExportService;
use Espo\Modules\Itvolga\Tools\Report\Export\ReportFiles;
use Espo\Modules\Itvolga\Tools\Report\Query\ReportQuery;
use Espo\Modules\Itvolga\Tools\Report\Run\ReportRunner;
use Espo\Modules\Itvolga\Tools\Report\Schema\SchemaFactory;
use Espo\ORM\EntityManager;

/**
 * One attempt of the mailing of a report (D-122, D-123):
 *
 *  - with the owner's rights: the owner must be active, may export (D-126) and read the report; the report is run once
 *    with his rights, the files are built once in his language and notation, every address gets its own letter (no
 *    other recipient in it) with the same stored files;
 *  - «generate for»: the users in the chosen user links over the records of the conditions — found with the owner's
 *    rights, «current user» conditions taken as true (DiscoveryFilters) — each get the report run with his own rights, in his language, in a letter to him only; a user whose rights
 *    refuse the definition is skipped and counted (the owner decided to send it, so his read access to the report
 *    itself is not required — owner's answer 2026-10-05).
 *
 * «Skip an empty report»: no letter when the run of that user has no records. The outcome holds codes and counts only
 * (no addresses, names or values) and is never an exception.
 */
final class MailingProcessor
{
    public const MAX_GENERATED = 200;

    public function __construct(
        private readonly EntityManager $entityManager,
        private readonly ReportRunner $runner,
        private readonly SchemaFactory $schemaFactory,
        private readonly AclManager $aclManager,
        private readonly ExportAccess $access,
        private readonly ExportService $exportService,
        private readonly ReportFiles $files,
        private readonly AttachmentStore $store,
        private readonly LetterSender $sender,
        private readonly Recipients $recipients,
        private readonly Letters $letters,
    ) {}

    /**
     * @return array<string, mixed>
     */
    public function process(string $reportId): array
    {
        $report = $this->entityManager->getRDBRepositoryByClass(Report::class)->getById($reportId);

        if (!$report) {
            return self::failed('reportMissing');
        }

        try {
            $settings = MailingSettingsParser::parse($report->get('mailing'));
        } catch (DefinitionError) {
            return self::failed('invalidSettings');
        }

        if ($settings === null || !$settings->enabled) {
            return ['status' => 'skipped', 'reason' => 'disabled'];
        }

        $owner = $report->get('assignedUserId') ?
            $this->entityManager->getRDBRepositoryByClass(User::class)->getById((string) $report->get('assignedUserId')) :
            null;

        if (!$owner || !$owner->isActive()) {
            return self::failed('ownerInactive');
        }

        if (!$this->access->canExport($owner)) {
            return self::failed('ownerNoExport');
        }

        if (!$this->aclManager->checkEntityRead($owner, $report)) {
            return self::failed('ownerNoAccess');
        }

        $outcome = ['status' => 'ok', 'letters' => 0, 'sent' => 0, 'noSmtp' => 0, 'failed' => 0, 'skipped' => []];
        $runParams = ExportRequest::runParams([], $settings->noLimit);

        try {
            $settings->generateFor === [] ?
                $this->forRecipients($report, $settings, $owner, $runParams, $outcome) :
                $this->forEachUser($report, $settings, $owner, $runParams, $outcome);
        } catch (FieldForbidden) {
            return self::failed('definitionForbidden');
        } catch (DefinitionError) {
            return self::failed('definitionInvalid');
        }

        if ($outcome['letters'] === 0) {
            $outcome['status'] = $outcome['skipped'] !== [] ? 'skipped' : 'failed';
        } elseif ($outcome['sent'] < $outcome['letters']) {
            $outcome['status'] = $outcome['sent'] === 0 ? 'failed' : 'partial';
        }

        return $outcome;
    }

    /**
     * @param array<string, mixed> $runParams
     * @param array<string, mixed> $outcome
     */
    private function forRecipients(Report $report, MailingSettings $settings, User $owner, array $runParams,
        array &$outcome): void
    {
        $addresses = $this->recipients->addresses($settings);

        if ($addresses === []) {
            self::skip($outcome, 'noRecipients');

            return;
        }

        [$query, $result] = $this->exportService->run($report, $runParams, $owner);

        if ($settings->skipEmpty && ($result['recordCount'] ?? 0) === 0) {
            self::skip($outcome, 'empty');

            return;
        }

        $files = $this->build($result, $owner, $settings, (string) $report->get('name'), $outcome);
        $letter = $this->letters->compose($report, $query, $result, $settings, 'mailingDefaultIntro');

        foreach ($addresses as $i => $address) {
            // One stored file, an attachment record per letter (a letter is the parent of its attachments).
            $attachments = array_map(fn (Attachment $a) => $i === 0 ? $a : $this->store->copy($a, $owner->getId()),
                $files);
            $this->count($outcome, $this->sender->send($address, $letter['subject'], $letter['html'], $attachments));
        }
    }

    /**
     * @param array<string, mixed> $runParams
     * @param array<string, mixed> $outcome
     */
    private function forEachUser(Report $report, MailingSettings $settings, User $owner, array $runParams,
        array &$outcome): void
    {
        $fields = MailingSettingsParser::generateFor($settings, (string) $report->get('entityType'),
            $this->schemaFactory->create($owner));
        // The search with the owner's rights; «current user» conditions apply to each recipient's own run only.
        $filters = ReportRunner::attributes($report)['filters'] ?? null;
        $search = is_array($filters) ? ['filters' => DiscoveryFilters::withoutCurrentUser($filters)] + $runParams :
            $runParams;
        $ids = $this->entityManager->getTransactionManager()->run(fn () => $this->runner->distinctUserIds(
            $this->runner->prepare($report, $search, $owner, false, $fields), $fields, self::MAX_GENERATED));

        if (count($ids) > self::MAX_GENERATED) {
            $ids = array_slice($ids, 0, self::MAX_GENERATED);
            $outcome['capped'] = true;
        }

        if ($ids === []) {
            self::skip($outcome, 'noRecipients');
        }

        foreach ($ids as $id) {
            [$user, $address, $reason] = $this->recipients->personal($id);

            if ($reason !== null || !$user || $address === null) {
                self::skip($outcome, $reason ?? 'inactive');

                continue;
            }

            try {
                /** @var ReportQuery $query */
                [$query, $result] = $this->exportService->run($report, $runParams, $user);
            } catch (DefinitionError) {
                // A field or an entity of the report is closed to him: no slice weaker than the report.
                self::skip($outcome, 'noRights');

                continue;
            }

            if ($settings->skipEmpty && ($result['recordCount'] ?? 0) === 0) {
                self::skip($outcome, 'empty');

                continue;
            }

            $files = $this->build($result, $user, $settings, (string) $report->get('name'), $outcome);
            $letter = $this->letters->compose($report, $query, $result, $settings, 'mailingDefaultIntro');
            $this->count($outcome, $this->sender->send($address, $letter['subject'], $letter['html'], $files));
        }
    }

    /**
     * Files of the chosen formats for the user of the run, stored as letter attachments created by him; a PDF over
     * its budget is left out and noted.
     *
     * @param array<string, mixed> $result
     * @param array<string, mixed> $outcome
     * @return list<Attachment>
     */
    private function build(array $result, User $user, MailingSettings $settings, string $title, array &$outcome): array
    {
        $attachments = [];

        foreach ($settings->formats as $format) {
            if ($format === 'pdf' && !ReportFiles::pdfFits($result)) {
                $outcome['pdfTooLarge'] = true;

                continue;
            }

            $attachments[] = $this->store->mailFile($this->files->build($result, $user, $format, $title),
                $user->getId());
        }

        return $attachments;
    }

    /**
     * @param array<string, mixed> $outcome
     */
    private function count(array &$outcome, string $sent): void
    {
        $outcome['letters']++;
        $outcome[$sent === LetterSender::SENT ? 'sent' : ($sent === LetterSender::NO_SMTP ? 'noSmtp' : 'failed')]++;
    }

    /**
     * @param array<string, mixed> $outcome
     */
    private static function skip(array &$outcome, string $reason): void
    {
        $outcome['skipped'][$reason] = ($outcome['skipped'][$reason] ?? 0) + 1;
    }

    /**
     * @return array<string, mixed>
     */
    private static function failed(string $error): array
    {
        return ['status' => 'failed', 'error' => $error];
    }
}
