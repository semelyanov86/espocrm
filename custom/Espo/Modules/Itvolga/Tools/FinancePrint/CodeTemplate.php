<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\FinancePrint;

use Espo\Tools\Pdf\Template;
use RuntimeException;

/**
 * A print form template kept as module files (D-79: forms are code in Git, not Template records): the body
 * Resources/printForms/<template>.html (core Handlebars; shared inline partials <partials>.html before it) and the CSS
 * common.css + <style>.css. A4 portrait, 10 mm margins,
 * Liberation Sans (D-82); no fixed header or footer — the source prints its header block on the first page only, so it
 * is the top of the body.
 */
final class CodeTemplate implements Template
{
    private const DIR = __DIR__ . '/../../Resources/printForms/';
    private const MARGIN = 10.0;
    private const BOTTOM_MARGIN = 15.0;

    private function __construct(
        private readonly string $body,
        private readonly string $style,
        private readonly string $title,
    ) {}

    public static function load(PrintForm $form, string $title): self
    {
        return new self(
            ($form->partials !== null ? self::read("$form->partials.html") . "\n" : '') . self::read("$form->template.html"),
            self::read('common.css') . "\n" . self::read("$form->style.css"),
            $title,
        );
    }

    public function getFontFace(): ?string
    {
        return 'Liberation Sans';
    }

    public function getBottomMargin(): float
    {
        return self::BOTTOM_MARGIN;
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
        return $this->body;
    }

    public function getPageOrientation(): string
    {
        return self::PAGE_ORIENTATION_PORTRAIT;
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
        return $this->style;
    }

    private static function read(string $file): string
    {
        $content = @file_get_contents(self::DIR . $file);

        if ($content === false) {
            throw new RuntimeException("Print form file '$file' is missing.");
        }

        return $content;
    }
}
