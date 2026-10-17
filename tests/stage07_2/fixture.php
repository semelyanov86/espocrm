<?php

/**
 * Stage 07.2 test fixture through the ORM: a Call of the live integration (written with its save option, as the AMI
 * listener writes it — a path the API never takes). Runs as the stand user with the stand PHP; the script comes on
 * stdin, the operation as JSON in argv (synthetic values of the test run only):
 *
 *   {"live": {"linkedId": "<key>", "name": "<name>", "recordingPath"?: "<YYYY/MM/DD/name.wav>"}}
 *                             → prints {"ok": true, "id": "<Call id>"}
 */

declare(strict_types=1);

$root = getenv('ESPO_ROOT') ?: '';
include $root . '/bootstrap.php';

use Espo\Core\Application;
use Espo\Core\ORM\Repository\Option\SaveOption;
use Espo\Modules\Itvolga\Tools\Telephony\CallFacts;
use Espo\ORM\EntityManager;

$app = new Application();
$app->setupSystemUser();
$entityManager = $app->getContainer()->getByClass(EntityManager::class);
$op = json_decode($argv[1] ?? '{}', true, 512, JSON_THROW_ON_ERROR);

if (isset($op['live'])) {
    $call = $entityManager->getNewEntity('Call');
    $call->setMultiple([
        'name' => $op['live']['name'],
        'cAsteriskLinkedId' => $op['live']['linkedId'],
        'status' => 'Held',
        'direction' => 'Outbound',
        'dateStart' => '2001-01-02 09:30:00',
        'dateEnd' => '2001-01-02 09:31:00',
        'cLiveState' => 'ended',
        'cCallStatusRaw' => 'ANSWER',
        'cBillDuration' => 50,
        'cRecordingPath' => $op['live']['recordingPath'] ?? null,
        'cRecording' => isset($op['live']['recordingPath']),
    ]);
    $entityManager->saveEntity($call, [SaveOption::SILENT => true, SaveOption::NO_NOTIFICATIONS => true,
        CallFacts::SAVE_OPTION => true]);

    echo json_encode(['ok' => true, 'id' => $call->getId()]) . "\n";
    exit;
}

echo json_encode(['ok' => false, 'error' => 'operation']) . "\n";
