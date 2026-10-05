<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Jobs;

use Espo\Core\Job\Job;
use Espo\Core\Job\Job\Data;
use Espo\Core\Utils\Log;
use Espo\Entities\Notification;
use Espo\Entities\User;
use Espo\Modules\Itvolga\Tools\Report\Export\AttachmentStore;
use Espo\Modules\Itvolga\Tools\Report\Export\ExportAccess;
use Espo\Modules\Itvolga\Tools\Report\Export\ExportService;
use Espo\Modules\Itvolga\Tools\Report\Export\ReportFiles;
use Espo\Modules\Itvolga\Tools\Report\Format\FormatContextFactory;
use Espo\Modules\Itvolga\Tools\Report\Mailing\Letters;
use Espo\Modules\Itvolga\Tools\Report\Mailing\LetterSender;
use Espo\Modules\Itvolga\Tools\Report\Mailing\Recipients;
use Espo\Modules\Itvolga\Tools\Report\Run\ReportRunner;
use Espo\ORM\EntityManager;
use Throwable;

/**
 * Background export of a report result (D-125), queued by POST Report/:id/export {background: true}: when it runs,
 * the requester is checked again — active, the export permission, read access to the report — and the report is run
 * with his rights and the conditions of his request. The file comes to him alone: a letter to his address (the file is
 * its attachment, created by him) and a notification with the download link (it works without access to e-mail); no
 * address of his own (none, or shared with another active user) — the link only. A refusal gives a notification without the report's name or data. Never throws (a rerun of
 * the core would send the file twice).
 */
class ReportExport implements Job
{
    public function __construct(
        private EntityManager $entityManager,
        private ReportRunner $runner,
        private ExportAccess $access,
        private ExportService $exportService,
        private ReportFiles $files,
        private AttachmentStore $store,
        private LetterSender $sender,
        private Recipients $recipients,
        private Letters $letters,
        private FormatContextFactory $formatContextFactory,
        private Log $log,
    ) {}

    public function run(Data $data): void
    {
        try {
            $user = $this->entityManager->getRDBRepositoryByClass(User::class)->getById((string) $data->get('userId'));

            if (!$user || !$user->isActive()) {
                return;
            }

            $this->export($user, $data);
        } catch (Throwable $e) {
            $this->log->error('Report background export: ' . $e::class . ' at ' . basename($e->getFile()) . ':' .
                $e->getLine());
        }
    }

    private function export(User $user, Data $data): void
    {
        $format = (string) $data->get('format');
        $runParams = json_decode((string) json_encode($data->get('runParams') ?? []), true);

        try {
            if (!in_array($format, ReportFiles::FORMATS, true) || !is_array($runParams) ||
                !$this->access->canExport($user)) {
                throw new \RuntimeException('Refused.');
            }

            $report = $this->runner->loadReadable((string) $data->get('reportId'), $user);
            [$query, $result] = $this->exportService->run($report, $runParams, $user);
            $file = $this->files->build($result, $user, $format, (string) $report->get('name'));
        } catch (Throwable) {
            $this->notify($user, 'backgroundExportFailed', []);

            return;
        }

        // His own address only: a letter is linked to every user of its address (D-124).
        [, $address] = $this->recipients->personal($user->getId());

        if ($address !== null) {
            $attachment = $this->store->mailFile($file, $user->getId());
            $letter = $this->letters->compose($report, $query, $result, null, 'exportReadyIntro');
            $this->sender->send($address, $letter['subject'], $letter['html'], [$attachment]);
        } else {
            $attachment = $this->store->exportFile($file, $user->getId());
        }

        $this->notify($user, 'backgroundExportReady', ['{url}' => '?entryPoint=download&id=' . $attachment->getId(),
            '{name}' => str_replace(['[', ']'], ['(', ')'], $file->name)]);
    }

    /**
     * @param array<string, string> $values
     */
    private function notify(User $user, string $key, array $values): void
    {
        $language = $this->formatContextFactory->create($user)->language;
        $notification = $this->entityManager->getRDBRepositoryByClass(Notification::class)->getNew();
        $notification
            ->setType(Notification::TYPE_MESSAGE)
            ->setMessage(strtr($language->translateLabel($key, 'messages', 'Report'), $values))
            ->setUserId($user->getId());
        $this->entityManager->saveEntity($notification);
    }
}
