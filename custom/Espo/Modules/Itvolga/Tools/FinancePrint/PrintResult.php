<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\FinancePrint;

use Espo\Tools\Pdf\Contents;

/**
 * A printed form: the PDF and its file name («Счёт С-637.pdf»).
 */
final class PrintResult
{
    public function __construct(
        public readonly Contents $contents,
        private readonly string $fileName,
    ) {}

    /**
     * File name for Content-Disposition: spaces and Cyrillic kept, path separators and control characters replaced.
     */
    public function fileName(): string
    {
        return preg_replace('/[\x00-\x1F\x7F\/\\\\:*?"<>|]/u', '_', $this->fileName) ?? 'document.pdf';
    }

    /**
     * inline, an ASCII fallback name and the UTF-8 name (RFC 6266 / RFC 5987).
     */
    public function contentDisposition(string $fallbackName): string
    {
        return sprintf("inline; filename=\"%s\"; filename*=UTF-8''%s", $fallbackName, rawurlencode($this->fileName()));
    }
}
