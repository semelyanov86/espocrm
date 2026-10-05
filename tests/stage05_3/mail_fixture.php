<?php

/**
 * Removes the letters, files and notifications a stage 05.3 test made (synthetic data only): every Email of the given
 * ids with its attachments (removed through the ORM, so the core hook deletes a stored file with its last copy), its
 * relation rows and the e-mail addresses only these letters used; the given export attachments and notifications. Runs
 * as the stand user with the stand PHP; the script comes on stdin, the operation as JSON in argv:
 *
 *   {"emails": [...], "attachments": [...], "notifications": [...], "addresses": ["synth-…@example.com"],
 *    "groupAccounts": [...]}
 *   {"createGroupAccount": {"name": …, "emailAddress": …, "smtpHost": "127.0.0.1", "smtpPort": 1}}
 *
 * The second form makes a synthetic group e-mail account with SMTP only (no IMAP; the send path of the tests on a
 * closed local port) and prints {"ok": true, "id": …}. Otherwise prints {"ok": true, "removed": n} or
 * {"ok": false, "error": <class>}.
 */

declare(strict_types=1);

$root = getenv('ESPO_ROOT') ?: '';
include $root . '/bootstrap.php';

use Espo\Core\Application;
use Espo\ORM\EntityManager;
use Espo\ORM\Query\DeleteBuilder;

$app = new Application();
$app->setupSystemUser();
$entityManager = $app->getContainer()->getByClass(EntityManager::class);
$op = json_decode($argv[1] ?? '{}', true, 512, JSON_THROW_ON_ERROR);
$removed = 0;

$purge = function (string $entityType, string $id) use ($entityManager, &$removed): void {
    $entity = $entityManager->getRDBRepository($entityType)->getById($id);

    if ($entity) {
        $entityManager->removeEntity($entity);
    }

    $entityManager->getRDBRepository($entityType)->deleteFromDb($id);
    $removed++;
};
$delete = function (string $from, array $where) use ($entityManager): void {
    $entityManager->getQueryExecutor()->execute(DeleteBuilder::create()->from($from)->where($where)->build());
};

try {
    if (is_array($op['createGroupAccount'] ?? null)) {
        $data = $op['createGroupAccount'];
        $account = $entityManager->getRDBRepository('InboundEmail')->getNew();
        $account->set(['name' => $data['name'], 'emailAddress' => $data['emailAddress'], 'status' => 'Active',
            'useImap' => false, 'useSmtp' => true, 'smtpHost' => $data['smtpHost'], 'smtpPort' => $data['smtpPort'],
            'smtpAuth' => false, 'smtpSecurity' => '']);
        $entityManager->saveEntity($account);
        echo json_encode(['ok' => true, 'id' => $account->getId()]), "\n";

        return;
    }

    foreach (array_values(array_filter($op['groupAccounts'] ?? [], 'is_string')) as $id) {
        $purge('InboundEmail', $id);
    }

    $emails = array_values(array_filter($op['emails'] ?? [], 'is_string'));
    $attachments = array_values(array_filter($op['attachments'] ?? [], 'is_string'));

    if ($emails !== []) {
        $query = $entityManager->getQueryBuilder()->select(['id'])->from('Attachment')
            ->where(['parentType' => 'Email', 'parentId' => $emails])->withDeleted()->build();

        foreach ($entityManager->getQueryExecutor()->execute($query)->fetchAll(PDO::FETCH_COLUMN) as $id) {
            $attachments[] = (string) $id;
        }
    }

    foreach (array_unique($attachments) as $id) {
        $purge('Attachment', $id);
    }

    foreach ($emails as $id) {
        $purge('Email', $id);
        $delete('EmailUser', ['emailId' => $id]);
        $delete('EmailEmailAddress', ['emailId' => $id]);
    }

    foreach (array_values(array_filter($op['notifications'] ?? [], 'is_string')) as $id) {
        $purge('Notification', $id);
    }

    foreach (array_values(array_filter($op['addresses'] ?? [], 'is_string')) as $address) {
        $record = $entityManager->getRDBRepository('EmailAddress')->where(['lower' => strtolower($address)])->findOne();

        if (!$record) {
            continue;
        }

        $usedBy = $entityManager->getRDBRepository('EmailEmailAddress')->where(['emailAddressId' => $record->getId()])
            ->count() + $entityManager->getRDBRepository('EntityEmailAddress')
            ->where(['emailAddressId' => $record->getId()])->count();

        if ($usedBy === 0) {
            $entityManager->getRDBRepository('EmailAddress')->deleteFromDb($record->getId());
            $removed++;
        }
    }

    echo json_encode(['ok' => true, 'removed' => $removed]), "\n";
} catch (Throwable $e) {
    echo json_encode(['ok' => false, 'error' => $e::class, 'at' => basename($e->getFile()) . ':' . $e->getLine()]), "\n";
}
