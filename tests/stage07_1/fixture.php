<?php

/**
 * Stage 07.1 test fixture through the ORM — paths the API never takes. Runs as the stand user with the stand PHP; the
 * script comes on stdin, the operation as JSON in argv (synthetic records of the test run only):
 *
 *   {"phone": {"entityType": "Lead", "id": "<id>", "value": "<raw>"}} → stores the phone value as the Vtiger import
 *                             does (no API sanitizer: «… доб. 5» stays); prints {"ok": true}.
 *   {"guard": "<Call id>"}  → tries to change the status without the integration's save option, plainly and with
 *                             SaveOption::IMPORT, and to create a new Call with an Asterisk key;
 *                             prints {"ok": true, "plain": <exception class|saved>, "import": …, "create": …}.
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

$attempt = function (callable $save): string {
    try {
        $save();

        return 'saved';
    } catch (Throwable $e) {
        $parts = explode('\\', $e::class);

        return end($parts);
    }
};

if (isset($op['phone'])) {
    $entity = $entityManager->getEntityById($op['phone']['entityType'], $op['phone']['id']);

    if (!$entity) {
        echo json_encode(['ok' => false, 'error' => 'NotFound']) . "\n";
        exit;
    }

    $entity->set('phoneNumberData', [(object) ['phoneNumber' => $op['phone']['value'], 'primary' => true,
        'type' => 'Office', 'optOut' => false, 'invalid' => false]]);
    $entity->set('phoneNumber', $op['phone']['value']);
    $entityManager->saveEntity($entity, [SaveOption::IMPORT => true, SaveOption::SILENT => true]);

    echo json_encode(['ok' => true]) . "\n";
    exit;
}

if (isset($op['guard'])) {
    $call = $entityManager->getEntityById('Call', $op['guard']);

    if (!$call) {
        echo json_encode(['ok' => false, 'error' => 'NotFound']) . "\n";
        exit;
    }

    $status = $call->get('status') === 'Held' ? 'Not Held' : 'Held';
    $result = ['ok' => true];
    $result['plain'] = $attempt(function () use ($entityManager, $call, $status) {
        $call->set('status', $status);
        $entityManager->saveEntity($call);
    });
    $call = $entityManager->getEntityById('Call', $op['guard']);
    $result['import'] = $attempt(function () use ($entityManager, $call, $status) {
        $call->set('status', $status);
        $entityManager->saveEntity($call, [SaveOption::IMPORT => true, SaveOption::SILENT => true]);
    });
    $result['create'] = $attempt(function () use ($entityManager) {
        $entityManager->createEntity('Call', [
            'name' => 'SYNTH guard probe',
            'dateStart' => gmdate('Y-m-d H:i:s'),
            'dateEnd' => gmdate('Y-m-d H:i:s'),
            'cAsteriskLinkedId' => 'synth-guard-probe',
        ]);
    });
    $result['statusAfter'] = $entityManager->getEntityById('Call', $op['guard'])?->get('status');

    echo json_encode($result) . "\n";
    exit;
}

echo json_encode(['ok' => false, 'error' => 'operation']) . "\n";
