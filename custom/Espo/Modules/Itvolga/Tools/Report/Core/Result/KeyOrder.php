<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Result;

use Collator;
use Espo\Modules\Itvolga\Tools\Finance\Decimal;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\FieldInfo;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\GroupLevel;
use Espo\Modules\Itvolga\Tools\Report\Core\Format\RawNumber;
use Espo\Modules\Itvolga\Tools\Report\Core\Granularity;

/**
 * Order of group keys (D-91): periods chronologically (ISO weeks by number), enum values in the order of the field
 * options, links by the name shown, texts by the language collation, numbers and booleans by value; the empty group
 * is always last. The SQL only groups; ordering and the group limit apply in PHP to all groups of a level (capped).
 */
final class KeyOrder
{
    public function __construct(private readonly ?Collator $collator = null) {}

    /**
     * @param array{v: mixed, f: string} $a
     * @param array{v: mixed, f: string} $b
     */
    public function compare(GroupLevel $group, array $a, array $b): int
    {
        $aEmpty = $a['v'] === null;
        $bEmpty = $b['v'] === null;

        if ($aEmpty || $bEmpty) {
            return $aEmpty <=> $bEmpty;
        }

        $result = $this->compareValues($group, $a, $b);

        return $group->direction === 'desc' ? -$result : $result;
    }

    /**
     * @param array{v: mixed, f: string} $a
     * @param array{v: mixed, f: string} $b
     */
    private function compareValues(GroupLevel $group, array $a, array $b): int
    {
        $field = $group->field;

        if ($group->granularity !== null) {
            return $group->granularity === Granularity::WEEK || $group->granularity === Granularity::YEAR ?
                self::numericParts((string) $a['v']) <=> self::numericParts((string) $b['v']) :
                strcmp((string) $a['v'], (string) $b['v']);
        }

        switch ($field->family()) {
            case FieldInfo::FAMILY_ENUM:
                $ia = array_search($a['v'], $field->options, true);
                $ib = array_search($b['v'], $field->options, true);

                return [$ia === false ? PHP_INT_MAX : $ia, $a['v']] <=> [$ib === false ? PHP_INT_MAX : $ib, $b['v']];

            case FieldInfo::FAMILY_NUMBER:
                return (RawNumber::read($a['v']) ?? Decimal::zero())->compare(RawNumber::read($b['v']) ??
                    Decimal::zero());

            case FieldInfo::FAMILY_BOOL:
                return (int) $a['v'] <=> (int) $b['v'];

            case FieldInfo::FAMILY_DATE:
            case FieldInfo::FAMILY_DATETIME:
                return strcmp((string) $a['v'], (string) $b['v']);
        }

        return $this->text($a['f'], $b['f']) ?: strcmp((string) $a['v'], (string) $b['v']);
    }

    public function text(string $a, string $b): int
    {
        return $this->collator ? (int) $this->collator->compare($a, $b) : strcmp(mb_strtolower($a), mb_strtolower($b));
    }

    /**
     * @return list<int>
     */
    private static function numericParts(string $key): array
    {
        return array_map('intval', preg_split('/\D+/', $key) ?: []);
    }
}
