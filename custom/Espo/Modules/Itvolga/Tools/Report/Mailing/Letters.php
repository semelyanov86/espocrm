<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Mailing;

use DateTimeImmutable;
use DateTimeZone;
use Espo\Core\AclManager;
use Espo\Core\Utils\Config;
use Espo\Modules\Itvolga\Entities\Report;
use Espo\Modules\Itvolga\Tools\Report\Core\Mailing\LetterBody;
use Espo\Modules\Itvolga\Tools\Report\Core\Mailing\MailingSettings;
use Espo\Modules\Itvolga\Tools\Report\Export\ReportFiles;
use Espo\Modules\Itvolga\Tools\Report\Format\FormatContextFactory;
use Espo\Modules\Itvolga\Tools\Report\Query\ReportQuery;

/**
 * Subject and body of a report letter for the user the report was run for (D-123, D-124): his language, notation and
 * time zone; the owner's subject and text or the defaults; the report info of his run; the link to the report only
 * when he may open it.
 */
final class Letters
{
    public function __construct(
        private readonly FormatContextFactory $formatContextFactory,
        private readonly ReportInfo $reportInfo,
        private readonly AclManager $aclManager,
        private readonly Config $config,
    ) {}

    /**
     * @param array<string, mixed> $result
     * @param string $introLabel Report.labels key of the default intro («{name}», «{date}»)
     * @return array{subject: string, html: string}
     */
    public function compose(Report $report, ReportQuery $query, array $result, ?MailingSettings $settings,
        string $introLabel): array
    {
        $user = $query->user;
        $context = $this->formatContextFactory->create($user);
        $language = $context->language;
        $name = (string) $report->get('name');
        $when = $context->dateTime->convertSystemDateTime(
            (new DateTimeImmutable('now', new DateTimeZone('UTC')))->format('Y-m-d H:i:s'),
            $context->timeZone, $context->dateFormat . ' ' . $context->timeFormat, $context->languageCode);
        $intro = $settings !== null && $settings->text !== '' ? $settings->text :
            str_replace(['{name}', '{date}'], [$name, $when], $language->translateLabel($introLabel, 'labels', 'Report'));
        $siteUrl = rtrim((string) $this->config->get('siteUrl'), '/');
        $url = $this->aclManager->checkEntityRead($user, $report) && $siteUrl !== '' ?
            $siteUrl . '/#Report/view/' . rawurlencode($report->getId()) : null;

        return [
            'subject' => LetterBody::subject($settings?->subject ?? '', $name, $when),
            'html' => LetterBody::html($intro, $this->reportInfo->lines($report, $query, $result, $context, $settings),
                ReportFiles::notes($result, $context), $language->translateLabel('Open report', 'labels', 'Report'),
                $url),
        ];
    }
}
