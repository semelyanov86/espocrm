<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Telephony\Core;

/**
 * The single byte range of an HTTP Range header (RFC 9110 §14) for seeking in a recording: «bytes=a-b», «bytes=a-»,
 * «bytes=-n». A header that is not one valid byte range is ignored (the whole file); a range that starts beyond the
 * end is unsatisfiable (416).
 */
final class ByteRange
{
    public const FULL = 'full';
    public const PARTIAL = 'partial';
    public const UNSATISFIABLE = 'unsatisfiable';

    private function __construct(
        public readonly string $kind,
        public readonly int $start,
        public readonly int $end,
    ) {}

    public static function parse(?string $header, int $size): self
    {
        $full = new self(self::FULL, 0, max(0, $size - 1));

        if ($header === null || !preg_match('/^\s*bytes\s*=\s*(\d{0,15})\s*-\s*(\d{0,15})\s*$/i', $header, $m)) {
            return $full;
        }

        [, $from, $to] = $m;

        if ($from === '' && $to === '') {
            return $full;
        }

        if ($from === '') {
            $suffix = (int) $to;

            if ($suffix === 0 || $size === 0) {
                return new self(self::UNSATISFIABLE, 0, 0);
            }

            return new self(self::PARTIAL, max(0, $size - $suffix), $size - 1);
        }

        $start = (int) $from;

        if ($to !== '' && (int) $to < $start) {
            return $full;
        }

        if ($start >= $size) {
            return new self(self::UNSATISFIABLE, 0, 0);
        }

        $end = $to === '' ? $size - 1 : min((int) $to, $size - 1);

        return new self(self::PARTIAL, $start, $end);
    }

    public function length(): int
    {
        return $this->kind === self::UNSATISFIABLE ? 0 : $this->end - $this->start + 1;
    }
}
