<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Mailing;

use Espo\Core\AclManager;
use Espo\Core\Select\SelectBuilderFactory;
use Espo\Entities\User;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\FieldInfo;
use Espo\Modules\Itvolga\Tools\Report\Core\Info\ConditionWords;
use Espo\Modules\Itvolga\Tools\Report\Format\FormatContext;
use Espo\Modules\Itvolga\Tools\Report\Run\Labels;
use Espo\ORM\EntityManager;
use PDO;
use Throwable;

/**
 * Words of the condition text for one reader (D-124): his language; option labels; dates in his format; names of the
 * records in the conditions only when he may read them and their name field (the access filter of the core and the
 * field level for him), others — «(нет доступа)».
 */
final class LanguageConditionWords implements ConditionWords
{
    public function __construct(
        private readonly FormatContext $context,
        private readonly Labels $labels,
        private readonly string $entityType,
        private readonly User $reader,
        private readonly SelectBuilderFactory $selectBuilderFactory,
        private readonly EntityManager $entityManager,
        private readonly AclManager $aclManager,
    ) {}

    private function label(string $label): string
    {
        return $this->context->language->translateLabel($label, 'labels', 'Report');
    }

    public function joiner(string $type): string
    {
        return $this->label($type === 'or' ? 'OR' : 'AND');
    }

    public function field(FieldInfo $field): string
    {
        return $this->labels->field($field);
    }

    public function operator(string $type): string
    {
        $language = $this->context->language;

        foreach ([['conditionOperator', 'Report'], ['searchRanges', 'Report'], ['dateSearchRanges', 'Global']] as
            [$list, $scope]) {
            $text = $language->translateOption($type, $list, $scope);

            if (is_string($text) && $text !== $type) {
                return $text;
            }
        }

        return $type;
    }

    public function compare(string $operator, string $otherField): string
    {
        return $this->context->language->translateOption($operator, 'havingOperator', 'Report') . ' ' .
            $this->context->language->translate($otherField, 'fields', $this->entityType);
    }

    public function values(FieldInfo $field, array $values): array
    {
        $family = $field->family();

        if (in_array($family, [FieldInfo::FAMILY_LINK, FieldInfo::FAMILY_LINK_MULTIPLE], true) &&
            $field->foreignEntityType !== null) {
            $names = $this->names($field->foreignEntityType, array_map('strval', array_filter($values,
                fn ($v) => is_string($v) && $v !== '')));

            return array_map(fn ($v) => $names[(string) $v] ?? $this->label('noAccessRecord'), $values);
        }

        return array_map(function ($value) use ($field, $family): string {
            $value = is_bool($value) ? ($value ? 'true' : 'false') : (string) $value;

            if (in_array($family, [FieldInfo::FAMILY_ENUM, FieldInfo::FAMILY_MULTI_ENUM], true)) {
                $text = $this->context->language->translateOption($value, $field->ref->field, $field->entityType);

                return is_string($text) ? $text : $value;
            }

            if ($field->isDate() && preg_match('/^\d{4}-\d{2}-\d{2}/', $value)) {
                try {
                    return $this->context->dateTime->convertSystemDate(substr($value, 0, 10),
                        $this->context->dateFormat, $this->context->languageCode);
                } catch (Throwable) {
                    return $value;
                }
            }

            return $value;
        }, $values);
    }

    /**
     * Names of the records the reader may read, when their name field is not closed to him (external review 05.3 B4).
     *
     * @param list<string> $ids
     * @return array<string, string>
     */
    private function names(string $entityType, array $ids): array
    {
        if ($ids === [] || !$this->entityManager->hasRepository($entityType) ||
            in_array('name', $this->aclManager->getScopeForbiddenFieldList($this->reader, $entityType), true)) {
            return [];
        }

        try {
            $query = $this->selectBuilderFactory
                ->create()
                ->from($entityType)
                ->forUser($this->reader)
                ->withStrictAccessControl()
                ->buildQueryBuilder()
                ->select(['id', 'name'])
                ->where(['id' => array_values(array_unique($ids))])
                ->order([])
                ->build();

            $names = [];

            foreach ($this->entityManager->getQueryExecutor()->execute($query)->fetchAll(PDO::FETCH_ASSOC) as $row) {
                $names[(string) $row['id']] = (string) $row['name'];
            }

            return $names;
        } catch (Throwable) {
            // No access to the entity at all: no names.
            return [];
        }
    }
}
