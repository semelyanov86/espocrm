<?php

/**
 * The import write path of stage 06.3 on synthetic records (stage 04.4 tests): saves or removes one record through
 * the ORM with SaveOption::IMPORT, as the importer will. Runs as the stand user with the stand PHP; the script comes
 * on stdin (the stand user does not read tests/), the operation as JSON in argv:
 *
 *   {"op": "save", "entityType": "PaymentAllocation", "id": null, "attributes": {...}}
 *   {"op": "remove", "entityType": "PaymentAllocation", "id": "...", "attributes": {...}, "import": true}
 *
 * A removal may first set attributes on the loaded copy (a stale copy, as the core cascade reads from an older
 * snapshot) and may run without SaveOption::IMPORT (`"import": false`, the core cascade's options).
 *
 * Prints {"ok": true, "id": ...} or {"ok": false, "error": <class>, "message": <message>}; messages of the finance
 * code never carry values.
 */

declare(strict_types=1);

$root = getenv('ESPO_ROOT') ?: '';
include $root . '/bootstrap.php';

use Espo\Core\Application;
use Espo\Core\ORM\Repository\Option\SaveOption;
use Espo\ORM\EntityManager;

$app = new Application();
$app->setupSystemUser();
$entityManager = $app->getContainer()->getByClass(EntityManager::class);
$op = json_decode($argv[1] ?? '{}', true, 512, JSON_THROW_ON_ERROR);

try {
    $entity = $op['id'] ?? null
        ? $entityManager->getEntityById($op['entityType'], $op['id'])
        : $entityManager->getRDBRepository($op['entityType'])->getNew();

    if (!$entity) {
        throw new RuntimeException('no such record');
    }

    if ($op['op'] === 'remove') {
        $entity->set($op['attributes'] ?? []);
        $entityManager->removeEntity($entity, ($op['import'] ?? true) ? [SaveOption::IMPORT => true] : []);
    } else {
        $entity->set($op['attributes'] ?? []);
        $entityManager->saveEntity($entity, [SaveOption::IMPORT => true]);
    }

    echo json_encode(['ok' => true, 'id' => $entity->getId()]), "\n";
} catch (Throwable $e) {
    echo json_encode(['ok' => false, 'error' => $e::class, 'message' => $e->getMessage()], JSON_UNESCAPED_UNICODE), "\n";
}
