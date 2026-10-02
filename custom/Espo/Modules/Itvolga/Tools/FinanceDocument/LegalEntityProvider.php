<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\FinanceDocument;

use Espo\Core\Exceptions\Error;
use Espo\Modules\Itvolga\Tools\Finance\Exceptions\UnknownLegalEntity;
use Espo\Modules\Itvolga\Tools\Finance\LegalEntityResolver;
use Espo\ORM\Entity;
use Espo\ORM\EntityManager;
use stdClass;

/**
 * The single legal entity of the company (D-04, D-48), key `Default`. Its requisites come only from the import
 * (stage 06); until then the record is a placeholder with the key and a neutral name.
 */
class LegalEntityProvider
{
    public const ENTITY_TYPE = 'LegalEntity';
    /** vtigerData key of the source spcompany value (the import input of legalEntity, D-48, D-60). */
    public const SOURCE_KEY = 'spcompany';

    public function __construct(private EntityManager $entityManager) {}

    public function findDefaultId(): ?string
    {
        return $this->findIdByKey(LegalEntityResolver::KEY);
    }

    /**
     * The legal entity of a source record by its spcompany value (D-48: exact spellings only).
     *
     * @throws UnknownLegalEntity a value that is not a spelling of the single legal entity
     */
    public function findIdForSource(?string $spcompany): ?string
    {
        return $this->findIdByKey((new LegalEntityResolver())->resolve($spcompany));
    }

    /**
     * One legal entity (D-04, D-48): a finance record (document, payment) saved in EspoCRM belongs to it; an imported
     * one only when its source spcompany is a known spelling of it — an unknown value stops the import instead of
     * becoming a second legal entity.
     *
     * @throws Error the legal entity is not configured; an imported record of an unknown legal entity
     */
    public function assign(Entity $record, bool $import): void
    {
        $kept = !$record->isNew() && $record->get('legalEntityId') && !$record->isAttributeChanged('legalEntityId');

        if (!$import && $kept) {
            return;
        }

        $id = $import ? $this->sourceIdOf($record) : $this->findDefaultId();

        $id ??= throw new Error('The legal entity is not configured: run itvolga-setup-finance.');

        if ($record->get('legalEntityId') !== $id) {
            $record->set('legalEntityId', $id);
        }
    }

    /**
     * @return bool whether the placeholder was created
     */
    public function ensure(): bool
    {
        if ($this->entityManager->getRDBRepository(self::ENTITY_TYPE)->count() > 0) {
            return false;
        }

        $this->entityManager->createEntity(self::ENTITY_TYPE, [
            'name' => LegalEntityResolver::KEY,
            'vtigerCompanyKey' => LegalEntityResolver::KEY,
        ]);

        return true;
    }

    /**
     * The importer keeps the source value in vtigerData.spcompany; no key (records without a source value) and empty
     * values mean the default company, as in SalesPlatform. Messages never carry the value.
     */
    private function sourceIdOf(Entity $record): ?string
    {
        $data = $record->get('vtigerData');
        $value = $data instanceof stdClass ? ($data->{self::SOURCE_KEY} ?? null) : null;
        $name = "{$record->getEntityType()} vtigerId {$record->get('vtigerId')}";

        if ($value !== null && !is_string($value)) {
            throw new Error("$name: vtigerData.spcompany is not a string.");
        }

        try {
            return $this->findIdForSource($value);
        } catch (UnknownLegalEntity $e) {
            throw new Error("$name: {$e->getMessage()}");
        }
    }

    private function findIdByKey(string $key): ?string
    {
        return $this->entityManager
            ->getRDBRepository(self::ENTITY_TYPE)
            ->where(['vtigerCompanyKey' => $key])
            ->findOne()
            ?->getId();
    }
}
