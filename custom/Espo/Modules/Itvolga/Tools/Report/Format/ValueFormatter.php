<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Format;

use Espo\Modules\Itvolga\Tools\Finance\Decimal;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\Aggregate;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\FieldInfo;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\GroupLevel;
use Espo\Modules\Itvolga\Tools\Report\Core\Format\RawNumber;
use Espo\ORM\EntityManager;
use Espo\ORM\Query\SelectBuilder;
use PDO;
use Throwable;

/**
 * Cells of a report result (D-102): `v` — the raw value (numbers as decimal strings, dates ISO, ids), `f` — the text
 * for the user, `id`/`et` — the record a link value leads to, `cur` — the currency of money, `mixed` — a money
 * aggregate over several currencies (no value is shown then, D-94).
 *
 * Names of linked records are read in one query per entity type (prefetch), without ACL — like the record lists of the
 * core show the names of linked records.
 */
final class ValueFormatter
{
    /** @var array<string, array<string, string>> entity type → id → name */
    private array $names = [];
    /** @var array<string, array<string, true>> */
    private array $pending = [];

    public function __construct(
        private readonly FormatContext $context,
        private readonly EntityManager $entityManager,
    ) {}

    public function remember(?string $entityType, mixed $id): void
    {
        if ($entityType && is_string($id) && $id !== '' && !isset($this->names[$entityType][$id])) {
            $this->pending[$entityType][$id] = true;
        }
    }

    private function loadNames(): void
    {
        foreach ($this->pending as $entityType => $ids) {
            if (!$this->entityManager->hasRepository($entityType) ||
                !$this->entityManager->getDefs()->getEntity($entityType)->hasAttribute('name')) {
                continue;
            }

            // Like the core name join, which skips removed rows: a removed record shows its id, not its name.
            foreach (array_chunk(array_keys($ids), 500) as $chunk) {
                $query = SelectBuilder::create()
                    ->from($entityType)
                    ->select(['id', 'name'])
                    ->where(['id' => $chunk, 'deleted' => false])
                    ->build();

                foreach ($this->entityManager->getQueryExecutor()->execute($query)->fetchAll(PDO::FETCH_ASSOC) as $row) {
                    $this->names[$entityType][(string) $row['id']] = (string) $row['name'];
                }
            }
        }

        $this->pending = [];
    }

    public function name(?string $entityType, ?string $id): string
    {
        if ($entityType === null || $id === null) {
            return '';
        }

        if ($this->pending !== []) {
            $this->loadNames();
        }

        return $this->names[$entityType][$id] ?? $id;
    }

    /**
     * @param array<string, mixed> $raw role → value (value, currency, type) as selected by ReportQuery
     * @return array<string, mixed>
     */
    public function field(FieldInfo $field, array $raw): array
    {
        $value = $raw['value'] ?? null;

        if ($value === null || $value === '' && $field->family() !== 'text') {
            return ['v' => null, 'f' => ''];
        }

        switch ($field->family()) {
            case FieldInfo::FAMILY_ENUM:
                return ['v' => (string) $value, 'f' => $this->option((string) $value, $field)];

            case FieldInfo::FAMILY_MULTI_ENUM:
                $list = is_string($value) ? json_decode($value, true) : $value;
                $list = is_array($list) ? array_values(array_map('strval', $list)) : [];

                return ['v' => $list, 'f' => implode(', ', array_map(fn ($v) => $this->option($v, $field), $list))];

            case FieldInfo::FAMILY_BOOL:
                $bool = (bool) $value;

                return ['v' => $bool, 'f' => $this->context->language->translateLabel($bool ? 'Yes' : 'No')];

            case FieldInfo::FAMILY_NUMBER:
                return $this->number($field, RawNumber::read($value), $raw['currency'] ?? null);

            case FieldInfo::FAMILY_DATE:
                return ['v' => (string) $value, 'f' => $this->date((string) $value)];

            case FieldInfo::FAMILY_DATETIME:
                // A date-only value of an optional date-time shows its calendar date, as core lists do.
                if (is_string($raw['date'] ?? null) && $raw['date'] !== '') {
                    return ['v' => $raw['date'], 'f' => $this->date($raw['date'])];
                }

                return ['v' => (string) $value, 'f' => $this->dateTime((string) $value)];

            case FieldInfo::FAMILY_LINK:
                return ['v' => (string) $value, 'f' => $this->name($field->foreignEntityType, (string) $value),
                    'id' => (string) $value, 'et' => $field->foreignEntityType];

            case FieldInfo::FAMILY_LINK_PARENT:
                $type = is_string($raw['type'] ?? null) ? $raw['type'] : null;

                return ['v' => (string) $value, 'f' => $this->name($type, (string) $value), 'id' => (string) $value,
                    'et' => $type];
        }

        return ['v' => (string) $value, 'f' => (string) $value];
    }

    public function rememberField(FieldInfo $field, array $raw): void
    {
        if ($field->family() === FieldInfo::FAMILY_LINK) {
            $this->remember($field->foreignEntityType, $raw['value'] ?? null);
        }

        if ($field->family() === FieldInfo::FAMILY_LINK_PARENT) {
            $this->remember(is_string($raw['type'] ?? null) ? $raw['type'] : null, $raw['value'] ?? null);
        }
    }

    /**
     * @return array<string, mixed>
     */
    public function number(FieldInfo $field, ?Decimal $value, mixed $currency = null, ?int $scale = null): array
    {
        if ($value === null) {
            return ['v' => null, 'f' => ''];
        }

        if ($field->isCurrency()) {
            $cell = ['v' => $value->toString(), 'f' => $this->context->numbers->format($value, $scale ?? 2)];

            if (is_string($currency) && $currency !== '') {
                $cell['cur'] = $currency;
                $cell['f'] .= ' ' . ($this->context->currencySymbols[$currency] ?? $currency);
            }

            return $cell;
        }

        return ['v' => $value->toString(), 'f' => $this->context->numbers->format($value, $scale)];
    }

    /**
     * @param array<string, mixed> $raw role → value (value, currencyMin, currencyMax)
     * @return array<string, mixed>
     */
    public function aggregate(Aggregate $aggregate, array $raw): array
    {
        $value = RawNumber::read($raw['value'] ?? null);

        if ($aggregate->field === null) {
            $count = $value ?? Decimal::zero();

            return ['v' => (int) $count->toString(), 'f' => $this->context->numbers->format($count)];
        }

        if ($aggregate->field->isCurrency() && ($raw['currencyMin'] ?? null) !== ($raw['currencyMax'] ?? null)) {
            return ['v' => null, 'f' => $this->context->language->translateLabel('mixedCurrencies', 'labels',
                'Report'), 'mixed' => true];
        }

        $scale = null;

        if ($aggregate->function === 'AVG') {
            $scale = 2;
        } elseif ($aggregate->field->isCurrency()) {
            $scale = 2;
        } elseif ($value !== null && $value->significantScale() > 8) {
            $scale = 8;
        }

        return $this->number($aggregate->field, $value, $raw['currencyMin'] ?? null, $scale);
    }

    /**
     * @return array<string, mixed>
     */
    public function groupKey(GroupLevel $group, mixed $key, ?string $parentType = null): array
    {
        if ($key === null || $key === '') {
            return ['v' => null, 'f' => $this->context->language->translateLabel('emptyValue', 'labels', 'Report')];
        }

        if ($group->granularity !== null) {
            $key = (string) $key;

            return ['v' => $key, 'f' => $this->context->periods->label($group->granularity, $key)];
        }

        return $this->field($group->field, ['value' => $key, 'type' => $parentType]);
    }

    private function option(string $value, FieldInfo $field): string
    {
        $text = $this->context->language->translateOption($value, $field->ref->field, $field->entityType);

        return is_string($text) ? $text : $value;
    }

    private function date(string $value): string
    {
        try {
            return $this->context->dateTime->convertSystemDate(substr($value, 0, 10), $this->context->dateFormat,
                $this->context->languageCode);
        } catch (Throwable) {
            return $value;
        }
    }

    private function dateTime(string $value): string
    {
        try {
            return $this->context->dateTime->convertSystemDateTime($value, $this->context->timeZone,
                $this->context->dateFormat . ' ' . $this->context->timeFormat, $this->context->languageCode);
        } catch (Throwable) {
            return $value;
        }
    }

    public function context(): FormatContext
    {
        return $this->context;
    }
}
