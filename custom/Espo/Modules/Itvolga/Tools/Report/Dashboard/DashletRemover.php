<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Dashboard;

use Closure;
use Espo\Core\Utils\Config;
use Espo\Core\Utils\Config\ConfigWriter;
use Espo\Core\Utils\Json;
use Espo\Entities\DashboardTemplate;
use Espo\Entities\Preferences;
use Espo\Modules\Itvolga\Entities\ReportFolder;
use Espo\Modules\Itvolga\Tools\FinanceDocument\RowLock;
use Espo\Modules\Itvolga\Tools\Report\Core\Dashboard\DashboardPruner;
use Espo\ORM\EntityManager;
use Espo\ORM\Query\SelectBuilder;
use PDO;
use stdClass;

/**
 * Removes the dashlets of a deleted key-metrics set from every dashboard (D-113): the users' preferences (rows whose
 * JSON mentions the set are changed under a lock of the row), the dashboard templates of the administrator (each under a
 * lock of its row) and the default dashboard of the settings (read again under the lock of the system report folder).
 * Other dashlets and options stay as they are.
 */
final class DashletRemover
{
    public const DASHLET = 'ReportMetrics';
    public const OPTION = 'metricSetId';

    public function __construct(
        private readonly EntityManager $entityManager,
        private readonly Config $config,
        private readonly ConfigWriter $configWriter,
        private readonly RowLock $rowLock,
    ) {}

    /**
     * @return int number of removed dashlets
     */
    public function remove(string $setId): int
    {
        $isTarget = fn (string $name, array $options) =>
            $name === self::DASHLET && ($options[self::OPTION] ?? null) === $setId;
        $removed = 0;

        $query = SelectBuilder::create()
            ->from(Preferences::ENTITY_TYPE)
            ->select(['id', 'data'])
            ->build();

        foreach ($this->entityManager->getQueryExecutor()->execute($query)->fetchAll(PDO::FETCH_ASSOC) as $row) {
            // The ORM compares a JSON attribute as JSON: the text of the row is looked through for the set id.
            if (str_contains((string) $row['data'], $setId)) {
                $removed += $this->entityManager->getTransactionManager()->run(fn () =>
                    $this->prunePreferences((string) $row['id'], $isTarget));
            }
        }

        $query = SelectBuilder::create()
            ->from(DashboardTemplate::ENTITY_TYPE)
            ->select(['id'])
            ->build();

        foreach ($this->entityManager->getQueryExecutor()->execute($query)->fetchAll(PDO::FETCH_COLUMN) as $id) {
            $removed += $this->entityManager->getTransactionManager()->run(fn () =>
                $this->pruneTemplate((string) $id, $isTarget));
        }

        return $removed + $this->entityManager->getTransactionManager()->run(fn () => $this->pruneSettings($isTarget));
    }

    /**
     * The default dashboard of the settings (a file): read again and written under the lock of the system report folder
     * row, so two cleanups do not write back each other's old copy (the folder guard orders its name checks on it too).
     *
     * @param Closure(string, array<string, mixed>): bool $isTarget
     */
    private function pruneSettings(Closure $isTarget): int
    {
        $this->rowLock->query(ReportFolder::ENTITY_TYPE)->where(['isSystem' => true])->findOne();
        $this->config->update();
        $result = DashboardPruner::prune(self::decode($this->config->get('dashboardLayout')),
            self::decode($this->config->get('dashletsOptions')), $isTarget);

        if ($result === null) {
            return 0;
        }

        $this->configWriter->set('dashboardLayout', self::encode($result[0]));
        $this->configWriter->set('dashletsOptions', self::encodeObject($result[1]));
        $this->configWriter->save();

        return count($result[2]);
        return $removed;
    }

    /**
     * A dashboard template, read under a lock of its row (a save of the template or another cleanup waits).
     *
     * @param Closure(string, array<string, mixed>): bool $isTarget
     */
    private function pruneTemplate(string $id, Closure $isTarget): int
    {
        $template = $this->rowLock->one(DashboardTemplate::ENTITY_TYPE, $id);
        $result = $template ? DashboardPruner::prune(self::decode($template->get('layout')),
            self::decode($template->get('dashletsOptions')), $isTarget) : null;

        if (!$template || !$result) {
            return 0;
        }

        $template->set(['layout' => self::encode($result[0]), 'dashletsOptions' => self::encodeObject($result[1])]);
        $this->entityManager->saveEntity($template);

        return count($result[2]);
    }

    /**
     * The preferences of one user, read under a lock of their row and written back as a whole: a change the user saves
     * meanwhile waits for this one instead of being overwritten by an older copy (the core stores them as one JSON).
     *
     * @param Closure(string, array<string, mixed>): bool $isTarget
     */
    private function prunePreferences(string $id, Closure $isTarget): int
    {
        $query = SelectBuilder::create()
            ->from(Preferences::ENTITY_TYPE)
            ->select(['data'])
            ->where(['id' => $id])
            ->forUpdate()
            ->build();
        $data = json_decode((string) $this->entityManager->getQueryExecutor()->execute($query)->fetchColumn(), true);

        if (!is_array($data)) {
            return 0;
        }

        $result = DashboardPruner::prune($data['dashboardLayout'] ?? null, $data['dashletsOptions'] ?? null, $isTarget);

        if ($result === null) {
            return 0;
        }

        $data['dashboardLayout'] = $result[0];
        $data['dashletsOptions'] = self::encodeObject($result[1]);
        $update = $this->entityManager->getQueryBuilder()
            ->update()
            ->in(Preferences::ENTITY_TYPE)
            ->set(['data' => Json::encode($data, JSON_PRETTY_PRINT)])
            ->where(['id' => $id])
            ->build();
        $this->entityManager->getQueryExecutor()->execute($update);

        return count($result[2]);
    }

    private static function decode(mixed $value): mixed
    {
        return json_decode((string) json_encode($value), true);
    }

    private static function encode(mixed $value): mixed
    {
        return json_decode((string) json_encode($value));
    }

    /**
     * Options keep the JSON object form also when empty.
     *
     * @param array<string, mixed> $value
     */
    private static function encodeObject(array $value): stdClass
    {
        return $value === [] ? new stdClass() : (object) self::encode($value);
    }
}
