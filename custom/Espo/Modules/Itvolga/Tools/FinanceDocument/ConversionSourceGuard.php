<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\FinanceDocument;

use Espo\Core\Exceptions\Conflict;
use Espo\Core\Exceptions\Error\Body;
use Espo\Core\Utils\Language;
use Espo\Core\Utils\Metadata;
use Espo\ORM\Entity;
use Espo\ORM\EntityManager;

/**
 * Reverse conversions of the registry (app.itvolgaFinance.conversions): when the conversion link is has-many on the
 * new document, the key lives on the source (Invoice → Act, «Создать акт»: invoice.actId, as SalesPlatform wrote
 * vtiger_invoice.sp_act_id on saving the act). The prefilled form carries the source in the core link stub
 * `<link>Ids`; the core checks it before the save (the source exists, edit access to it, one id: Record LinkCheck)
 * and relates it inside the document's transaction (Hooks/Common/FieldProcessing, afterSave).
 *
 * A source holds one target: a source that already points to a live target gets no new document (owner decision
 * 2026-10-03; re-pointing it to another existing target stays an ordinary edit of its link field). Refused when the
 * form is prefilled and again when the new document is saved: the source row is locked and its target is read with a
 * locking read (fresh, not the snapshot the transaction may already hold), before the number is taken. Lock order:
 * source rows (sorted) → their targets → the number counter of the new document; the payment side (ledger → payment →
 * documents) never locks a target or its counter, so the orders cannot cross. A removed (soft-deleted) target frees
 * the source; a source removed meanwhile is refused too, as the core relate would silently skip it.
 */
class ConversionSourceGuard
{
    public const LINKED = 'financeConversionLinked';
    public const SOURCE_MISSING = 'financeConversionSourceMissing';

    public function __construct(
        private EntityManager $entityManager,
        private Metadata $metadata,
        private Language $language,
        private DocumentTypes $types,
        private RowLock $rowLock,
    ) {}

    /**
     * The link of the source that holds its target when the conversion link is has-many on the new document
     * (`act` for Invoice → Act); null for a forward conversion (a belongs-to link on the new document).
     */
    public function sourceLink(string $to, string $link): ?string
    {
        $defs = $this->metadata->get(['entityDefs', $to, 'links', $link]) ?? [];

        return ($defs['type'] ?? null) === Entity::HAS_MANY ? $defs['foreign'] : null;
    }

    /**
     * The prefill of a reverse conversion (nothing is locked yet; the save checks again).
     *
     * @throws Conflict
     */
    public function assertFree(Entity $source, string $to, string $sourceLink): void
    {
        $targetId = $source->get($sourceLink . 'Id');

        if ($targetId && $this->entityManager->getEntityById($to, $targetId)) {
            throw $this->conflict(self::LINKED, $source->getEntityType(), $to);
        }
    }

    /**
     * A new document of the registry: lock and re-check every source given in the stub of a reverse conversion.
     *
     * @throws Conflict
     */
    public function claimSources(Entity $document): void
    {
        $to = $document->getEntityType();

        foreach ($this->types->conversionsTo($to) as $from => $conversion) {
            $sourceLink = $this->sourceLink($to, $conversion['link']);
            $ids = $sourceLink ? $document->get($conversion['link'] . 'Ids') : null;

            if (!is_array($ids)) {
                continue;
            }

            $ids = array_values(array_unique(array_filter($ids, 'is_string')));
            sort($ids);

            foreach ($ids as $id) {
                $source = $this->rowLock->one($from, $id) ?? throw $this->conflict(self::SOURCE_MISSING, $from, $to);
                $targetId = $source->get($sourceLink . 'Id');

                if ($targetId && $this->rowLock->one($to, $targetId)) {
                    throw $this->conflict(self::LINKED, $from, $to);
                }
            }
        }
    }

    private function conflict(string $label, string $from, string $to): Conflict
    {
        $data = [
            'source' => $this->language->translateLabel($from, 'scopeNames'),
            'target' => $this->language->translateLabel($to, 'scopeNames'),
        ];

        // The target's scope may word the refusal for its own case (Act.messages); Global is the fallback.
        return Conflict::createWithBody($label, Body::create()->withMessageTranslation($label, $to, $data));
    }
}
