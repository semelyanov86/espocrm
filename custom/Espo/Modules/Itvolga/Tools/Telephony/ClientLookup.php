<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Telephony;

use Espo\Modules\Itvolga\Tools\Telephony\Core\PhoneNumbers;
use Espo\ORM\EntityManager;
use Espo\ORM\Query\SelectBuilder;

/**
 * Clients of a telephone number (D-167), without access control — the integration links the Call once; every
 * viewer of a call card sees only what CardService lets them read. Exact: PhoneNumber.numeric equal to one of the
 * stored forms of the canonical number (main and additional numbers of contacts, accounts and leads). Possible: no
 * exact match, but the last ten digits occur inside a non-standard stored value («… доб. 12»); never linked.
 * PhoneNumber::getIds() is not used: it creates numbers. A number shared by more records than the limits is reported
 * incomplete: the writer then picks no parent (a cut list could look unambiguous).
 */
class ClientLookup
{
    public const TYPES = ['Contact', 'Account', 'Lead'];
    private const LIMIT = 100;

    public function __construct(private EntityManager $entityManager) {}

    /**
     * @return array{matches: list<array{entityType: string, id: string, possible: bool, accountId: ?string}>, complete: bool}
     */
    public function find(?string $canonical, string $localAreaCode): array
    {
        if ($canonical === null) {
            return ['matches' => [], 'complete' => true];
        }

        $exact = $this->owners(
            $this->phoneNumberIds(['numeric' => PhoneNumbers::numericCandidates($canonical, $localAreaCode)]),
            false,
        );

        if ($exact['matches'] !== []) {
            return $exact;
        }

        $tail = PhoneNumbers::tail($canonical);

        if ($tail === null) {
            return ['matches' => [], 'complete' => true];
        }

        return $this->owners($this->phoneNumberIds(['numeric*' => '%' . $tail . '%']), true);
    }

    /**
     * @param array<string, mixed> $where
     * @return array{list<string>, bool} ids, complete
     */
    private function phoneNumberIds(array $where): array
    {
        $query = SelectBuilder::create()
            ->from('PhoneNumber')
            ->select(['id'])
            ->where($where)
            ->limit(0, self::LIMIT + 1)
            ->build();

        $ids = array_map(
            static fn (array $row) => (string) $row['id'],
            iterator_to_array($this->entityManager->getQueryExecutor()->execute($query), false),
        );

        return [array_slice($ids, 0, self::LIMIT), count($ids) <= self::LIMIT];
    }

    /**
     * @param array{list<string>, bool} $phoneNumbers
     * @return array{matches: list<array{entityType: string, id: string, possible: bool, accountId: ?string}>, complete: bool}
     */
    private function owners(array $phoneNumbers, bool $possible): array
    {
        [$phoneNumberIds, $complete] = $phoneNumbers;

        if ($phoneNumberIds === []) {
            return ['matches' => [], 'complete' => $complete];
        }

        $query = SelectBuilder::create()
            ->from('EntityPhoneNumber')
            ->select(['entityType', 'entityId'])
            ->where(['phoneNumberId' => $phoneNumberIds, 'entityType' => self::TYPES])
            ->order('entityType')
            ->order('entityId')
            ->limit(0, self::LIMIT * 2 + 1)
            ->build();

        $out = [];
        $rows = iterator_to_array($this->entityManager->getQueryExecutor()->execute($query), false);

        if (count($rows) > self::LIMIT * 2) {
            $complete = false;
        }

        foreach ($rows as $row) {
            $entity = $this->entityManager->getEntityById((string) $row['entityType'], (string) $row['entityId']);

            if (!$entity || isset($out[$row['entityType'] . ':' . $row['entityId']])) {
                continue;
            }

            $out[$row['entityType'] . ':' . $row['entityId']] = [
                'entityType' => $entity->getEntityType(),
                'id' => $entity->getId(),
                'possible' => $possible,
                'accountId' => $entity->getEntityType() === 'Contact' ? ($entity->get('accountId') ?: null) : null,
            ];

            if (count($out) >= self::LIMIT) {
                $complete = false;

                break;
            }
        }

        return ['matches' => array_values($out), 'complete' => $complete];
    }
}
