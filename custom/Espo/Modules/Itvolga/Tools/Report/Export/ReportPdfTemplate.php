<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Export;

use Espo\Tools\Pdf\Template;
use RuntimeException;

/**
 * Page of the PDF of a report result for the core Dompdf initializer (D-119): A4, landscape for a matrix and wide
 * tables, DejaVu Sans of the core (it has «₽», the money cells print as on the screen). The page itself is the complete
 * document of Core\Export\ScreenHtml (margins in its @page rule), so the body and style here are not used.
 */
final class ReportPdfTemplate implements Template
{
    private const STYLE = __DIR__ . '/../../../Resources/reports/output/report.css';
    private const MARGIN = 10.0;

    public function __construct(
        private readonly string $title,
        private readonly string $orientation,
    ) {}

    public static function style(): string
    {
        $style = @file_get_contents(self::STYLE);

        if ($style === false) {
            throw new RuntimeException('The report output style is missing.');
        }

        return $style;
    }

    public function getFontFace(): ?string
    {
        return 'DejaVu Sans';
    }

    public function getBottomMargin(): float
    {
        return self::MARGIN;
    }

    public function getTopMargin(): float
    {
        return self::MARGIN;
    }

    public function getLeftMargin(): float
    {
        return self::MARGIN;
    }

    public function getRightMargin(): float
    {
        return self::MARGIN;
    }

    public function hasFooter(): bool
    {
        return false;
    }

    public function getFooter(): string
    {
        return '';
    }

    public function getFooterPosition(): float
    {
        return 0.0;
    }

    public function hasHeader(): bool
    {
        return false;
    }

    public function getHeader(): string
    {
        return '';
    }

    public function getHeaderPosition(): float
    {
        return 0.0;
    }

    public function getBody(): string
    {
        return '';
    }

    public function getPageOrientation(): string
    {
        return $this->orientation === self::PAGE_ORIENTATION_LANDSCAPE ? self::PAGE_ORIENTATION_LANDSCAPE :
            self::PAGE_ORIENTATION_PORTRAIT;
    }

    public function getPageFormat(): string
    {
        return 'A4';
    }

    public function getPageWidth(): float
    {
        return 210.0;
    }

    public function getPageHeight(): float
    {
        return 297.0;
    }

    public function hasTitle(): bool
    {
        return true;
    }

    public function getTitle(): string
    {
        return $this->title;
    }

    public function getStyle(): ?string
    {
        return null;
    }
}
