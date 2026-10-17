<?php

declare(strict_types=1);

/*
 * Stage 08 (docs/migration/rehearsal.md): the first imported file of a fresh EspoCRM installation, which has no upload
 * directory yet (the core creates data/upload on its first upload; the rehearsal's first full import failed every
 * file with `file_storage`). BlobReceiver receives and places a synthetic file in an empty temporary working
 * directory with the core autoloader — no stand, no database. Prints one status line; exit code 1 on failure.
 *
 *   php tests/stage08/blob_receiver_fresh.php     (run by tests/stage08/test_stage08.py)
 */

use Espo\Core\Utils\File\Manager as FileManager;
use Espo\Modules\Itvolga\Tools\Import\BlobReceiver;
use Espo\Modules\Itvolga\Tools\Import\ImportError;

require dirname(__DIR__, 2) . '/vendor/autoload.php';

$work = sys_get_temp_dir() . '/itvolga-stage08-' . bin2hex(random_bytes(6));
mkdir($work, 0700);
chdir($work);

$bytes = "synthetic file of the stage 08 test\n";
$stdin = fopen('php://memory', 'w+b');
fwrite($stdin, json_encode(['seq' => 0, 'data' => base64_encode($bytes)]) . "\n");
rewind($stdin);
$file = (object) ['chunks' => 1, 'size' => strlen($bytes), 'sha256' => hash('sha256', $bytes)];
$receiver = new BlobReceiver(new FileManager());
$status = 'ok';

try {
    $blob = $receiver->receive($stdin, $file, 4 * 1024 * 1024);
    $receiver->place($blob, BlobReceiver::DIR . 'stage08-synthetic');

    if (!is_file(BlobReceiver::DIR . 'stage08-synthetic') ||
        hash_file('sha256', BlobReceiver::DIR . 'stage08-synthetic') !== $file->sha256) {
        $status = 'stored file differs';
    }
} catch (ImportError $e) {
    $status = 'error ' . $e->reason;
} finally {
    $receiver->cleanup();

    foreach (glob(BlobReceiver::DIR . '{,.}*', GLOB_BRACE) ?: [] as $path) {
        if (is_file($path)) {
            unlink($path);
        }
    }

    if (is_dir(BlobReceiver::DIR)) {
        rmdir(BlobReceiver::DIR);
    }

    if (is_dir('data')) {
        rmdir('data');
    }

    chdir(sys_get_temp_dir());
    rmdir($work);
}

echo $status, "\n";
exit($status === 'ok' ? 0 : 1);
