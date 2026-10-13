<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Telephony;

use Espo\Entities\User;
use Espo\ORM\EntityManager;
use Espo\ORM\Query\SelectBuilder;

/**
 * Extension → user of the telephony (D-168): an active regular user or administrator whose cPhoneExtension is the
 * extension. An extension of two active users belongs to nobody (never a guess); PhoneExtensionGuard prevents it
 * for every save except the Vtiger import. Cached for a few seconds inside the long-running listener.
 */
class ExtensionDirectory
{
    private const TTL = 10.0;

    /** @var ?array<string, list<string>> */
    private ?array $map = null;
    private float $loadedAt = 0.0;

    public function __construct(private EntityManager $entityManager) {}

    public function userId(?string $extension): ?string
    {
        if ($extension === null || $extension === '') {
            return null;
        }

        $ids = $this->map()[$extension] ?? [];

        return count($ids) === 1 ? $ids[0] : null;
    }

    public function isAmbiguous(string $extension): bool
    {
        return count($this->map()[$extension] ?? []) > 1;
    }

    public function ambiguousCount(): int
    {
        return count(array_filter($this->map(), static fn (array $ids) => count($ids) > 1));
    }

    public function forget(): void
    {
        $this->map = null;
    }

    /**
     * @return array<string, list<string>>
     */
    private function map(): array
    {
        if ($this->map !== null && microtime(true) - $this->loadedAt < self::TTL) {
            return $this->map;
        }

        $query = SelectBuilder::create()
            ->from(User::ENTITY_TYPE)
            ->select(['id', 'cPhoneExtension'])
            ->where([
                'isActive' => true,
                'type' => [User::TYPE_REGULAR, User::TYPE_ADMIN],
                'cPhoneExtension!=' => null,
            ])
            ->build();

        $map = [];

        foreach ($this->entityManager->getQueryExecutor()->execute($query) as $row) {
            $extension = trim((string) $row['cPhoneExtension']);

            if ($extension !== '') {
                $map[$extension][] = (string) $row['id'];
            }
        }

        $this->map = $map;
        $this->loadedAt = microtime(true);

        return $map;
    }
}
