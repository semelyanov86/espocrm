<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Finance;

use Espo\Modules\Itvolga\Tools\Finance\Exceptions\UnknownLegalEntity;

/**
 * Maps the spcompany value of a source record to the single legal entity (D-04).
 *
 * 'Default' is the key of the only vtiger_organizationdetails row; 'По умолчанию' is the Russian UI label of that key
 * (languages/ru_ru/Vtiger.php: 'Default' => 'По умолчанию') that was stored as a second picklist value: it has no
 * requisites row and no numbering counter of its own. Empty/NULL (bank import payments) means the default company too
 * (SalesPlatform PDF controller: empty spcompany → 'Default'). Any other value is not a spelling of this entity:
 * it is rejected, never turned into a second company.
 */
final class LegalEntityResolver
{
    public const KEY = 'Default';

    /** @var list<string> */
    public const SOURCE_VALUES = ['Default', 'По умолчанию', ''];

    public function resolve(?string $spcompany): string
    {
        if ($spcompany === null || in_array($spcompany, self::SOURCE_VALUES, true)) {
            return self::KEY;
        }

        throw new UnknownLegalEntity("Unknown spcompany value (length " . mb_strlen($spcompany) . ') is not the known legal entity.');
    }
}
