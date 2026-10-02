<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\FinanceDocument;

use Espo\Core\Acl;
use Espo\Core\Acl\Table;
use Espo\Core\Exceptions\Forbidden;
use Espo\Core\Exceptions\NotFound;
use Espo\Core\Utils\FieldUtil;
use Espo\ORM\EntityManager;
use stdClass;

/**
 * Attributes of a new document prefilled from another one («Создать заказ» from a quote; owner decision
 * 2026-10-01): the header fields of the registry's fieldList, the line inputs and the link to the source. Nothing is
 * created and no number is taken: the user reviews the form (historical tax rates stay visible to be set to 0, D-21)
 * and saves it as a new document, calculated by the core.
 */
class DocumentConverter
{
    /** Line attributes that are not copied: identity and outputs of the source document. */
    private const SKIPPED_LINE_ATTRIBUTES = ['id', 'order', 'amount', 'margin'];

    public function __construct(
        private EntityManager $entityManager,
        private Acl $acl,
        private FieldUtil $fieldUtil,
        private DocumentTypes $types,
        private DocumentProcessor $processor,
    ) {}

    /**
     * @throws Forbidden
     * @throws NotFound
     */
    public function attributes(string $from, string $id, string $to): stdClass
    {
        $conversion = $this->types->conversion($from, $to) ?? throw new NotFound();
        $sourceType = $this->types->find($from) ?? throw new NotFound();
        $source = $this->entityManager->getEntityById($from, $id) ?? throw new NotFound();

        if (
            !$this->acl->checkEntity($source, Table::ACTION_READ) ||
            !$this->acl->checkScope($to, Table::ACTION_CREATE)
        ) {
            throw new Forbidden();
        }

        $forbidden = $this->acl->getScopeForbiddenAttributeList($to, Table::ACTION_EDIT);
        $attributes = (object) [];

        foreach ($conversion['fieldList'] as $field) {
            foreach ($this->fieldUtil->getAttributeList($from, $field) as $attribute) {
                if (!in_array($attribute, $forbidden, true)) {
                    $attributes->$attribute = $source->get($attribute);
                }
            }
        }

        $attributes->{$conversion['link'] . 'Id'} = $source->getId();
        $attributes->{$conversion['link'] . 'Name'} = $source->get('name');
        $attributes->{DocumentProcessor::ITEM_LIST} = array_map(
            static function (stdClass $line): stdClass {
                foreach (self::SKIPPED_LINE_ATTRIBUTES as $attribute) {
                    unset($line->$attribute);
                }

                return $line;
            },
            $this->processor->loadItemList($source, $sourceType),
        );

        return $attributes;
    }
}
