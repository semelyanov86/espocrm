<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Seed;

use Espo\Core\Exceptions\HasBody;
use Espo\Core\Utils\Config;
use Espo\Core\Utils\Metadata;
use Espo\Entities\User;
use Espo\Modules\Itvolga\Entities\Report;
use Espo\Modules\Itvolga\Entities\ReportFolder;
use Espo\ORM\EntityManager;
use Espo\ORM\Query\SelectBuilder;
use PDO;
use RuntimeException;
use Throwable;

/**
 * Folders and standard reports of the module (reports.md §8, D-100): the registry `app.itvolgaReports` lists the
 * folders and the manifests `Resources/reports/standard/<file>.json`. Insert-only by a stable `seedKey`: a folder or
 * report whose key exists — even soft-deleted or changed by a user — is left as it is, so a rerun creates nothing
 * twice and never overwrites a user's change nor brings back a deleted report. A report whose entity is disabled on the
 * installation is skipped with a message. Reports belong to the first active administrator and are public; each is
 * saved through the ORM, so the definition hook checks it like a report saved by a user.
 */
final class StandardReports
{
    public const MANIFEST_DIR = __DIR__ . '/../../../Resources/reports/standard';

    public function __construct(
        private readonly EntityManager $entityManager,
        private readonly Metadata $metadata,
        private readonly Config $config,
    ) {}

    /**
     * @return array{list<string>, list<string>} changes and errors
     */
    public function apply(bool $dryRun): array
    {
        $changes = [];
        $errors = [];
        $language = str_starts_with((string) ($this->config->get('language') ?? 'ru_RU'), 'en') ? 'en' : 'ru';
        $owner = $this->owner();
        $folders = [];

        foreach ($this->metadata->get(['app', 'itvolgaReports', 'folders']) ?? [] as $folder) {
            $existing = $this->bySeedKey(ReportFolder::ENTITY_TYPE, $folder['seedKey']);

            if ($existing) {
                // A deleted folder stays deleted; its new standard reports go to the default folder.
                if (!$existing['deleted']) {
                    $folders[$folder['seedKey']] = $existing['id'];
                }

                continue;
            }

            if (!empty($folder['onlyIfEntity']) && !$this->isEnabled($folder['onlyIfEntity'])) {
                continue;
            }

            $changes[] = "folder + {$folder['seedKey']}";

            if ($dryRun) {
                continue;
            }

            $entity = $this->entityManager->getRDBRepositoryByClass(ReportFolder::class)->getNew();
            $entity->setMultiple([
                'name' => $folder['name'][$language] ?? $folder['name']['ru'],
                'description' => $folder['description'][$language] ?? null,
                'isSystem' => !empty($folder['isSystem']),
                'seedKey' => $folder['seedKey'],
                'assignedUserId' => $owner?->getId(),
            ]);
            $this->entityManager->saveEntity($entity);
            $folders[$folder['seedKey']] = $entity->getId();
        }

        foreach ($this->manifests() as $file => $manifest) {
            $key = $manifest['seedKey'] ?? null;

            if (!is_string($key) || $key === '') {
                $errors[] = "report ! $file: no seedKey";

                continue;
            }

            if ($this->bySeedKey(Report::ENTITY_TYPE, $key)) {
                continue;
            }

            if (!$this->isEnabled((string) ($manifest['entityType'] ?? ''))) {
                $changes[] = "report - $key: entity {$manifest['entityType']} is disabled, skipped";

                continue;
            }

            $changes[] = "report + $key";

            if ($dryRun) {
                continue;
            }

            try {
                $report = $this->entityManager->getRDBRepositoryByClass(Report::class)->getNew();
                $report->setMultiple(array_intersect_key($manifest['definition'] ?? [],
                    array_flip(Report::DEFINITION_ATTRIBUTES)));
                $report->setMultiple([
                    'name' => $manifest['name'][$language] ?? $manifest['name']['ru'],
                    'description' => $manifest['description'][$language] ?? ($manifest['description']['ru'] ?? null),
                    'type' => $manifest['type'],
                    'entityType' => $manifest['entityType'],
                    'folderId' => $folders[$manifest['folder'] ?? ''] ?? null,
                    'accessType' => Report::ACCESS_PUBLIC,
                    'assignedUserId' => $owner?->getId(),
                    'seedKey' => $key,
                ]);
                $this->entityManager->saveEntity($report);
            } catch (Throwable $e) {
                array_pop($changes);
                $detail = $e instanceof HasBody ? (string) $e->getBody() : $e->getMessage();
                $errors[] = "report ! $key: $detail";
            }
        }

        return [$changes, $errors];
    }

    /**
     * @return array<string, array<string, mixed>> file name → manifest
     */
    public function manifests(): array
    {
        $result = [];

        foreach ($this->metadata->get(['app', 'itvolgaReports', 'standardReports']) ?? [] as $name) {
            $path = self::MANIFEST_DIR . "/$name.json";
            $data = is_file($path) ? json_decode((string) file_get_contents($path), true) : null;

            if (!is_array($data)) {
                throw new RuntimeException("Standard report manifest '$name' is missing or not JSON.");
            }

            $result[$name] = $data;
        }

        return $result;
    }

    private function isEnabled(string $entityType): bool
    {
        $scope = $this->metadata->get(['scopes', $entityType]);

        return is_array($scope) && !empty($scope['entity']) && empty($scope['disabled']) &&
            $this->entityManager->hasRepository($entityType);
    }

    /**
     * The record with the seed key, soft-deleted ones included (a deleted standard report or folder stays deleted;
     * a removed folder leaves such a row, see Repositories\ReportFolder).
     *
     * @return ?array{id: string, deleted: bool}
     */
    private function bySeedKey(string $entityType, string $key): ?array
    {
        $query = SelectBuilder::create()
            ->from($entityType)
            ->select(['id', 'deleted'])
            ->where(['seedKey' => $key])
            ->withDeleted()
            ->build();
        $row = $this->entityManager->getQueryExecutor()->execute($query)->fetch(PDO::FETCH_ASSOC);

        return is_array($row) ? ['id' => (string) $row['id'], 'deleted' => (bool) $row['deleted']] : null;
    }

    private function owner(): ?User
    {
        return $this->entityManager->getRDBRepositoryByClass(User::class)
            ->where(['type' => User::TYPE_ADMIN, 'isActive' => true])
            ->order('createdAt')
            ->findOne();
    }
}
