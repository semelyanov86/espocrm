<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Metric;

use Espo\Core\Exceptions\BadRequest;
use Espo\Core\Exceptions\Forbidden;
use Espo\Core\Select\SearchParams;
use Espo\Core\Select\SelectBuilderFactory;
use Espo\Core\Utils\Config;
use Espo\Entities\Preferences;
use Espo\Entities\User;
use Espo\ORM\EntityManager;
use Espo\ORM\Query\Select;
use InvalidArgumentException;

/**
 * The query of the standard record list `GET <entity>?where=…` for a user (D-112): the where items of a list filter
 * (a primary filter, conditions copied from a saved filter) through the core search parameters and the strict select
 * builder — record ACL, the field check of the where items, the primary filters of the entity. Date-time conditions
 * take the time zone of the user, as their own list request would.
 */
final class FilterQuery
{
    public function __construct(
        private readonly SelectBuilderFactory $selectBuilderFactory,
        private readonly EntityManager $entityManager,
        private readonly Config $config,
    ) {}

    /**
     * @param list<array<string, mixed>> $where
     * @throws BadRequest
     * @throws Forbidden
     */
    public function build(string $entityType, array $where, User $user): Select
    {
        try {
            $params = SearchParams::fromRaw(['where' => $this->forUser($where, $user)]);
        } catch (InvalidArgumentException $e) {
            throw new BadRequest($e->getMessage());
        }

        return $this->selectBuilderFactory
            ->create()
            ->from($entityType)
            ->forUser($user)
            ->withStrictAccessControl()
            ->withSearchParams($params)
            ->build();
    }

    /**
     * @param list<array<string, mixed>> $where
     * @throws BadRequest
     * @throws Forbidden
     */
    public function count(string $entityType, array $where, User $user): int
    {
        return $this->entityManager->getRDBRepository($entityType)
            ->clone($this->build($entityType, $where, $user))
            ->count();
    }

    /**
     * The where items as the user's own list would send them: date-time conditions in their time zone. The values API
     * returns them too, so the records opened from a metric are those it counted.
     *
     * @param list<array<string, mixed>> $where
     * @return list<array<string, mixed>>
     */
    public function forUser(array $where, User $user): array
    {
        return self::withTimeZone($where, $this->timeZone($user));
    }

    private function timeZone(User $user): string
    {
        $preferences = $this->entityManager->getEntityById(Preferences::ENTITY_TYPE, $user->getId());

        return (string) ($preferences?->get('timeZone') ?: ($this->config->get('timeZone') ?: 'UTC'));
    }

    /**
     * @param list<mixed> $items
     * @return list<mixed>
     */
    private static function withTimeZone(array $items, string $timeZone): array
    {
        return array_map(function (mixed $item) use ($timeZone): mixed {
            if (!is_array($item)) {
                return $item;
            }

            if (!empty($item['dateTime'])) {
                $item['timeZone'] = $timeZone;
            }

            if (is_array($item['value'] ?? null) && array_is_list($item['value']) &&
                in_array($item['type'] ?? null, ['and', 'or', 'not', 'having'], true)) {
                $item['value'] = self::withTimeZone($item['value'], $timeZone);
            }

            return $item;
        }, $items);
    }
}
