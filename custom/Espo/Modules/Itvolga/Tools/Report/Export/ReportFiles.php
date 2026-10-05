<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Export;

use DateTimeImmutable;
use DateTimeZone;
use Espo\Core\Utils\Config;
use Espo\Entities\Preferences;
use Espo\Entities\User;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\DefinitionError;
use Espo\Modules\Itvolga\Tools\Report\Core\Export\CellText;
use Espo\Modules\Itvolga\Tools\Report\Core\Export\CsvWriter;
use Espo\Modules\Itvolga\Tools\Report\Core\Export\FlatSheet;
use Espo\Modules\Itvolga\Tools\Report\Core\Export\LimitNotes;
use Espo\Modules\Itvolga\Tools\Report\Core\Export\OutputWords;
use Espo\Modules\Itvolga\Tools\Report\Core\Export\ScreenHtml;
use Espo\Modules\Itvolga\Tools\Report\Format\FormatContext;
use Espo\Modules\Itvolga\Tools\Report\Format\FormatContextFactory;
use Espo\ORM\EntityManager;
use Espo\Tools\Pdf\Dompdf\DompdfInitializer;
use Espo\Tools\Pdf\Params;

/**
 * Files and the print view of a report result (D-116…D-120) for the user it was run for: his language, time zone,
 * number notation and CSV delimiter. CSV and XLSX — the flat sheet; PDF and print — the table as on the screen. Nothing
 * is stored here (AttachmentStore does it).
 */
final class ReportFiles
{
    public const FORMATS = ['csv', 'xlsx', 'pdf'];
    /** Budget of one PDF in table cells (Dompdf time and memory grow with them; calibrated on the stand, D-119). */
    public const MAX_PDF_CELLS = 60000;
    private const MIME = [
        'csv' => 'text/csv',
        'xlsx' => 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'pdf' => 'application/pdf',
    ];
    private const NOTES = ['limitedRows', 'limitedGroups', 'limitedCap', 'limitedColumns', 'calculationsCapped'];

    public function __construct(
        private readonly FormatContextFactory $formatContextFactory,
        private readonly EntityManager $entityManager,
        private readonly Config $config,
        private readonly DompdfInitializer $dompdfInitializer,
    ) {}

    public static function mimeType(string $format): string
    {
        return self::MIME[$format];
    }

    /**
     * @param array<string, mixed> $result a result of all rows (ReportRunner prepare(allRows) + execute) for $user
     * @throws DefinitionError pdfTooLarge — a PDF over the budget
     */
    public function build(array $result, User $user, string $format, string $title): ExportFile
    {
        $context = $this->formatContextFactory->create($user);
        $words = self::words($context);
        $notes = self::notes($result, $context);
        $name = CellText::fileName($title, $format);

        if ($format === 'pdf') {
            if (!self::pdfFits($result)) {
                throw new DefinitionError('pdfTooLarge', 'format', ['n' => self::MAX_PDF_CELLS]);
            }

            // Dompdf of the core (its fonts, paper and orientation of the template) renders the same document as the
            // print view: no template engine and no record take part.
            $view = $this->document($result, $context, $title);
            $pdf = $this->dompdfInitializer->initialize(new ReportPdfTemplate($title, $view['orientation']),
                Params::create());
            $pdf->loadHtml($view['html']);
            $pdf->render();
            $contents = (string) $pdf->output();

            return new ExportFile($name, self::MIME['pdf'], $contents);
        }

        $sheet = FlatSheet::build($result, $words, new DateTimeZone($context->timeZone), $notes);
        $contents = $format === 'csv' ? CsvWriter::write($sheet, $this->delimiter($user)) : XlsxWriter::write($sheet);

        return new ExportFile($name, self::MIME[$format], $contents);
    }

    /**
     * @param array<string, mixed> $result
     */
    public static function pdfFits(array $result): bool
    {
        return ScreenHtml::cellCount($result) <= self::MAX_PDF_CELLS;
    }

    /**
     * The print view: a complete HTML document of the screen table (no scripts) for the browser print.
     *
     * @param array<string, mixed> $result
     * @return array{title: string, orientation: string, html: string}
     */
    public function printView(array $result, User $user, string $title): array
    {
        return $this->document($result, $this->formatContextFactory->create($user), $title);
    }

    /**
     * @param array<string, mixed> $result
     * @return array{title: string, orientation: string, html: string}
     */
    private function document(array $result, FormatContext $context, string $title): array
    {
        $orientation = ScreenHtml::orientation($result);
        $body = ScreenHtml::body($title, $this->meta($result, $context), self::notes($result, $context), $result,
            self::words($context));

        return [
            'title' => $title,
            'orientation' => $orientation,
            'html' => ScreenHtml::document($title, $body, ReportPdfTemplate::style(), $orientation,
                substr($context->languageCode, 0, 2)),
        ];
    }

    public static function words(FormatContext $context): OutputWords
    {
        $t = fn (string $label) => $context->language->translateLabel($label, 'labels', 'Report');

        return new OutputWords(
            total: $t('Total'),
            currency: $t('Currency'),
            mixedCurrencies: $t('mixedCurrencies'),
            noData: $t('No data'),
            totalRecords: $t('Total records'),
            column: $t('Column'),
            function: $t('Function'),
            value: $t('Value'),
            functions: array_combine(['SUM', 'AVG', 'MIN', 'MAX'], array_map(fn (string $fn) =>
                (string) $context->language->translateOption($fn, 'aggregateFunction', 'Report'),
                ['SUM', 'AVG', 'MIN', 'MAX'])),
        );
    }

    /**
     * @param array<string, mixed> $result
     * @return list<string>
     */
    public static function notes(array $result, FormatContext $context): array
    {
        $templates = [];

        foreach (self::NOTES as $key) {
            $templates[$key] = $context->language->translateLabel($key, 'labels', 'Report');
        }

        return LimitNotes::of($result, $templates);
    }

    /**
     * «Всего записей: N · Сформирован: <date time>» in the user's notation and time zone.
     *
     * @param array<string, mixed> $result
     * @return list<string>
     */
    private function meta(array $result, FormatContext $context): array
    {
        $now = (new DateTimeImmutable('now', new DateTimeZone('UTC')))->format('Y-m-d H:i:s');
        $t = fn (string $label) => $context->language->translateLabel($label, 'labels', 'Report');

        return [
            $t('Total records') . ': ' . ($result['recordCount'] ?? 0),
            $t('Generated') . ': ' . $context->dateTime->convertSystemDateTime($now, $context->timeZone,
                $context->dateFormat . ' ' . $context->timeFormat, $context->languageCode),
        ];
    }

    /**
     * The CSV delimiter of the user's export settings (Preferences of that user, then the system's), as the core
     * export takes it.
     */
    private function delimiter(User $user): string
    {
        $preferences = $this->entityManager->getEntityById(Preferences::ENTITY_TYPE, $user->getId());

        return CsvWriter::delimiter($preferences?->get('exportDelimiter') ?? $this->config->get('exportDelimiter'));
    }
}
