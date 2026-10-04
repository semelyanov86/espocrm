<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report;

use Espo\Core\Utils\Language;
use Espo\Core\Utils\Metadata;
use Espo\Entities\User;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\DefinitionError;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\FieldInfo;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\FieldRef;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\WhereRules;
use Espo\Modules\Itvolga\Tools\Report\Schema\MetadataSchema;
use Espo\Modules\Itvolga\Tools\Report\Schema\SchemaFactory;
use Espo\ORM\EntityManager;

/**
 * What the report builder may offer a user (D-99): the reportable entity types and, for one of them, every usable
 * field of the entity and of the entities one link away, with the operations a report allows on it. It is computed by
 * the same Schema that checks a definition on save and run, so the builder never offers a field the server refuses.
 */
final class Catalog
{
    public function __construct(
        private readonly SchemaFactory $schemaFactory,
        private readonly Metadata $metadata,
        private readonly EntityManager $entityManager,
        private readonly Language $language,
    ) {}

    /**
     * @return list<array{entityType: string, label: string}>
     */
    public function entityTypes(User $user): array
    {
        $list = array_map(fn (string $type) => ['entityType' => $type,
            'label' => $this->language->translateLabel($type, 'scopeNamesPlural')],
            $this->schemaFactory->create($user)->entityList());
        usort($list, fn ($a, $b) => strcmp(mb_strtolower($a['label']), mb_strtolower($b['label'])));

        return $list;
    }

    /**
     * @return array<string, mixed>
     */
    public function fields(string $entityType, User $user): array
    {
        $schema = $this->schemaFactory->create($user);
        $links = [];

        foreach ($this->entityManager->getDefs()->getEntity($entityType)->getRelationList() as $relation) {
            $kind = MetadataSchema::linkKind($relation);
            $foreign = $relation->tryGetForeignEntityType();
            $link = $relation->getName();

            if ($kind === null || $foreign === null || !preg_match('/^[a-z][a-zA-Z0-9]*$/', $link)) {
                continue;
            }

            $fields = $this->fieldsOf($schema, $entityType, $link, $foreign);

            if ($fields !== []) {
                $links[] = ['link' => $link, 'kind' => $kind, 'entityType' => $foreign,
                    'label' => $this->language->translate($link, 'links', $entityType), 'fields' => $fields];
            }
        }

        usort($links, fn ($a, $b) => strcmp(mb_strtolower($a['label']), mb_strtolower($b['label'])));

        return [
            'entityType' => $entityType,
            'fields' => $this->fieldsOf($schema, $entityType, null, $entityType),
            'links' => $links,
        ];
    }

    /**
     * @return list<array<string, mixed>>
     */
    private function fieldsOf(MetadataSchema $schema, string $entityType, ?string $link, string $owner): array
    {
        $result = [];

        foreach (array_keys($this->metadata->get(['entityDefs', $owner, 'fields']) ?? []) as $name) {
            $ref = FieldRef::parse($link === null ? $name : "$link.$name");

            if ($ref === null) {
                continue;
            }

            try {
                $field = $schema->field($entityType, $ref);
            } catch (DefinitionError $e) {
                if ($e->key === 'linkForbidden') {
                    return [];
                }

                continue;
            }

            if ($field === null) {
                continue;
            }

            $result[] = [
                'ref' => $ref->toString(),
                'field' => $name,
                'label' => $this->language->translate($name, 'fields', $owner),
                'type' => $field->type,
                'family' => $field->family(),
                'entityType' => $owner,
                'foreignEntityType' => $field->foreignEntityType,
                'column' => $field->canColumn(),
                'group' => $field->canGroup(),
                'sort' => $field->canSort(),
                'aggregate' => $field->isNumeric(),
                'filter' => $field->canFilter(),
                'quickFilter' => $field->canQuickFilter(),
                'date' => $field->isDate(),
                'operators' => $field->canFilter() ? WhereRules::typesFor($field) : [],
            ];
        }

        usort($result, fn ($a, $b) => strcmp(mb_strtolower($a['label']), mb_strtolower($b['label'])));

        return $result;
    }
}
