<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\FinanceDocument;

use Espo\Modules\Itvolga\Tools\Finance\LegalEntityResolver;
use Espo\ORM\EntityManager;

/**
 * The single legal entity of the company (D-04, D-48), key `Default`. Its requisites come only from the import
 * (stage 06); until then the record is a placeholder with the key and a neutral name.
 */
class LegalEntityProvider
{
    public const ENTITY_TYPE = 'LegalEntity';

    public function __construct(private EntityManager $entityManager) {}

    public function findDefaultId(): ?string
    {
        return $this->entityManager
            ->getRDBRepository(self::ENTITY_TYPE)
            ->where(['vtigerCompanyKey' => LegalEntityResolver::KEY])
            ->findOne()
            ?->getId();
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
}
