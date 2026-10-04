<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Format;

use Espo\Core\Utils\DateTime as DateTimeUtil;
use Espo\Core\Utils\Language;
use Espo\Modules\Itvolga\Tools\Report\Core\Format\NumberText;
use Espo\Modules\Itvolga\Tools\Report\Core\Format\PeriodLabel;

/**
 * Notation of the user a result is formatted for (D-102): language, date and number formats, time zone.
 */
final class FormatContext
{
    /**
     * @param array<string, string> $currencySymbols
     */
    public function __construct(
        public readonly Language $language,
        public readonly string $languageCode,
        public readonly DateTimeUtil $dateTime,
        public readonly string $dateFormat,
        public readonly string $timeFormat,
        public readonly string $timeZone,
        public readonly NumberText $numbers,
        public readonly PeriodLabel $periods,
        public readonly array $currencySymbols,
    ) {}
}
