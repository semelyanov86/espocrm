<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Classes\Select\Where;

use Espo\Core\AclManager;
use Espo\Core\Acl\Table;
use Espo\Core\Exceptions\BadRequest;
use Espo\Core\Exceptions\Forbidden;
use Espo\Core\Select\SelectBuilderFactory;
use Espo\Core\Select\Where\Item;
use Espo\Core\Select\Where\ItemConverter;
use Espo\Entities\User;
use Espo\ORM\EntityManager;
use Espo\ORM\Query\Part\Condition as Cond;
use Espo\ORM\Query\Part\Expression as Expr;
use Espo\ORM\Query\Part\WhereItem;
use Espo\ORM\Query\SelectBuilder;
use Espo\ORM\Type\RelationType;

/**
 * Where item `itvolgaRelated` (reports, D-89): records of the entity having at least one related record — through
 * the link `value.link` (belongsTo, hasMany, hasChildren, manyMany) — that matches the core where items `value.where`
 * AND that the user may read. The related condition is checked and converted by the core strict select builder of the
 * related entity (its field ACL, its access filter, its own date transformer), so a hidden related record never makes
 * a record match. The link must be readable by the user: its field and the related scope.
 *
 *   {"type": "itvolgaRelated", "attribute": "id", "value": {"link": "account", "where": [{"type": "in", ...}]}}
 */
class Related implements ItemConverter
{
    public function __construct(
        private string $entityType,
        private User $user,
        private AclManager $aclManager,
        private SelectBuilderFactory $selectBuilderFactory,
        private EntityManager $entityManager,
    ) {}

    public function convert(SelectBuilder $queryBuilder, Item $item): WhereItem
    {
        $value = $item->getValue();
        $link = is_array($value) ? ($value['link'] ?? null) : null;
        $where = is_array($value) ? ($value['where'] ?? null) : null;

        if ($item->getAttribute() !== 'id' || !is_string($link) || !is_array($where) || !array_is_list($where) ||
            $where === [] || self::hasModuleItem($where)) {
            throw new BadRequest('Bad itvolgaRelated where item.');
        }

        $entityDefs = $this->entityManager->getDefs()->getEntity($this->entityType);

        if (!$entityDefs->hasRelation($link)) {
            throw new BadRequest('Bad itvolgaRelated link.');
        }

        $relation = $entityDefs->getRelation($link);
        $foreign = $relation->tryGetForeignEntityType();
        $acl = $this->aclManager->createUserAcl($this->user);

        if ($foreign === null || in_array($link, $acl->getScopeForbiddenLinkList($this->entityType), true) ||
            in_array($link, $acl->getScopeForbiddenFieldList($this->entityType), true) ||
            !$acl->checkScope($foreign, Table::ACTION_READ)) {
            throw new Forbidden('Forbidden itvolgaRelated link.');
        }

        $matching = $this->selectBuilderFactory
            ->create()
            ->from($foreign)
            ->forUser($this->user)
            ->withStrictAccessControl()
            ->withWhere(Item::fromRaw(['type' => 'and', 'value' => $where]))
            ->buildQueryBuilder();

        switch ($relation->getType()) {
            case RelationType::BELONGS_TO:
                return Cond::in(Expr::column($relation->getKey()), $matching->select('id')->build());

            case RelationType::HAS_MANY:
                return Cond::in(Expr::column('id'), $matching->select($relation->getForeignKey())->build());

            case RelationType::HAS_CHILDREN:
                $foreignType = $relation->getParam('foreignType') ?? 'parentType';

                return Cond::in(
                    Expr::column('id'),
                    $matching->select($relation->getForeignKey())->where([$foreignType => $this->entityType])->build()
                );

            case RelationType::MANY_MANY:
                $where = [
                    'middle.' . $relation->getForeignMidKey() . '=s' => $matching->select('id')->build(),
                    'middle.deleted' => false,
                ];

                foreach ($relation->getConditions() as $key => $conditionValue) {
                    $where['middle.' . $key] = $conditionValue;
                }

                return Cond::in(
                    Expr::column('id'),
                    SelectBuilder::create()
                        ->from(ucfirst($relation->getRelationshipName()), 'middle')
                        ->select('middle.' . $relation->getMidKey())
                        ->where($where)
                        ->build()
                );
        }

        throw new BadRequest('Not supported itvolgaRelated link.');
    }

    /**
     * Module items are not nested: a related condition is one link deep.
     *
     * @param array<mixed> $items
     */
    private static function hasModuleItem(array $items): bool
    {
        foreach ($items as $item) {
            if (!is_array($item)) {
                return true;
            }

            if (str_starts_with((string) ($item['type'] ?? ''), 'itvolga') ||
                (is_array($item['value'] ?? null) && in_array($item['type'] ?? null, ['and', 'or'], true) &&
                    self::hasModuleItem($item['value']))) {
                return true;
            }
        }

        return false;
    }
}
