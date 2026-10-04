<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Format;

use Espo\Core\Utils\Config;
use Espo\Core\Utils\DateTime\DateTimeFactory;
use Espo\Core\Utils\Language\LanguageFactory;
use Espo\Core\Utils\Metadata;
use Espo\Entities\Preferences;
use Espo\Entities\User;
use Espo\Modules\Itvolga\Tools\Report\Core\Format\NumberText;
use Espo\Modules\Itvolga\Tools\Report\Core\Format\PeriodLabel;
use Espo\ORM\EntityManager;

/**
 * Builds the notation of a given user: his preferences, else the system settings (the runner of a report, later the
 * recipient of a mailing — 05.3).
 */
final class FormatContextFactory
{
    public function __construct(
        private readonly EntityManager $entityManager,
        private readonly Config $config,
        private readonly LanguageFactory $languageFactory,
        private readonly DateTimeFactory $dateTimeFactory,
        private readonly Metadata $metadata,
    ) {}

    public function create(User $user): FormatContext
    {
        $preferences = $this->entityManager->getEntityById(Preferences::ENTITY_TYPE, $user->getId());
        $get = fn (string $name, string $default) =>
            (string) ($preferences?->get($name) ?: ($this->config->get($name) ?: $default));

        $languageCode = $get('language', 'en_US');
        $language = $this->languageFactory->create($languageCode);
        $timeZone = $get('timeZone', 'UTC');
        $dateFormat = $get('dateFormat', 'DD.MM.YYYY');
        $timeFormat = $get('timeFormat', 'HH:mm');
        $dateTime = $this->dateTimeFactory->createWithTimeZone($timeZone);
        $decimalMark = (string) ($preferences?->get('decimalMark') ?: ($this->config->get('decimalMark') ?? ','));
        $thousandSeparator = $preferences?->get('thousandSeparator') ?? $this->config->get('thousandSeparator') ?? ' ';
        $monthNames = $language->get(['Global', 'lists', 'monthNames']) ?? [];

        return new FormatContext(
            language: $language,
            languageCode: $languageCode,
            dateTime: $dateTime,
            dateFormat: $dateFormat,
            timeFormat: $timeFormat,
            timeZone: $timeZone,
            numbers: new NumberText($decimalMark, (string) $thousandSeparator),
            periods: new PeriodLabel(
                array_values($monthNames),
                [
                    'week' => $language->translateLabel('periodWeek', 'labels', 'Report'),
                    'quarter' => $language->translateLabel('periodQuarter', 'labels', 'Report'),
                    'halfYear' => $language->translateLabel('periodHalfYear', 'labels', 'Report'),
                ],
                fn (string $date) => $dateTime->convertSystemDate($date, $dateFormat, $languageCode),
            ),
            currencySymbols: $this->metadata->get(['app', 'currency', 'symbolMap']) ?? [],
        );
    }
}
