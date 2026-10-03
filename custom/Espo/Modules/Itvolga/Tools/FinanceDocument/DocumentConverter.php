<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\FinanceDocument;

use Espo\Core\Acl;
use Espo\Core\Acl\Table;
use Espo\Core\Exceptions\Conflict;
use Espo\Core\Exceptions\Forbidden;
use Espo\Core\Exceptions\NotFound;
use Espo\Core\ORM\Entity as CoreEntity;
use Espo\Core\Utils\FieldUtil;
use Espo\Modules\Itvolga\Tools\FinancePayment\PaymentPrefill;
use Espo\ORM\EntityManager;
use stdClass;

/**
 * Attributes of a new document prefilled from another one («Создать заказ» from a quote; owner decision
 * 2026-10-01): the header fields of the registry's fieldList, the line inputs and the link to the source. Nothing is
 * created and no number is taken: the user reviews the form (historical tax rates stay visible to be set to 0, D-21)
 * and saves it as a new document, calculated by the core. «Добавить платёж» on an invoice or a sales order goes the
 * same way (PaymentPrefill, stage 04.4). «Создать акт» on an invoice is a reverse conversion: the key stays on the
 * source, the form carries it in the link stub `<link>Ids`, saving it needs edit access to the source, and a source
 * already linked to a live act gets no form (ConversionSourceGuard, stage 04.5).
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
        private PaymentPrefill $paymentPrefill,
        private ConversionSourceGuard $sources,
    ) {}

    /**
     * @throws Conflict a reverse conversion from a source already linked to a live target
     * @throws Forbidden
     * @throws NotFound
     */
    public function attributes(string $from, string $id, string $to): stdClass
    {
        if ($paymentType = $this->types->findPayment($to)) {
            return $this->paymentPrefill->attributes($from, $id, $paymentType);
        }

        $conversion = $this->types->conversion($from, $to) ?? throw new NotFound();
        $sourceType = $this->types->find($from) ?? throw new NotFound();
        $source = $this->entityManager->getEntityById($from, $id) ?? throw new NotFound();
        $link = $conversion['link'];
        $sourceLink = $this->sources->sourceLink($to, $link);

        if (
            !$this->acl->checkEntity($source, Table::ACTION_READ) ||
            !$this->acl->checkScope($to, Table::ACTION_CREATE) ||
            ($sourceLink && !$this->acl->checkEntity($source, Table::ACTION_EDIT))
        ) {
            throw new Forbidden();
        }

        if ($sourceLink) {
            $this->sources->assertFree($source, $to, $sourceLink);
        }

        $forbidden = $this->acl->getScopeForbiddenAttributeList($to, Table::ACTION_EDIT);
        $attributes = (object) [];

        foreach ($conversion['fieldList'] as $field) {
            // A record read by id carries no link-multiple values (teams): without loading them the form got null and
            // the new document no teams (D-52, D-71; stage 04.6).
            if ($source instanceof CoreEntity && $source->hasLinkMultipleField($field)) {
                $source->loadLinkMultipleField($field);
            }

            foreach ($this->fieldUtil->getAttributeList($from, $field) as $attribute) {
                if (!in_array($attribute, $forbidden, true)) {
                    $attributes->$attribute = $source->get($attribute);
                }
            }
        }

        if ($sourceLink) {
            $attributes->{$link . 'Ids'} = [$source->getId()];
            $attributes->{$link . 'Names'} = (object) [$source->getId() => $source->get('name')];
        } else {
            $attributes->{$link . 'Id'} = $source->getId();
            $attributes->{$link . 'Name'} = $source->get('name');
        }

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
