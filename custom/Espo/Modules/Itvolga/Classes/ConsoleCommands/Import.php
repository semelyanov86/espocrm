<?php

namespace Espo\Modules\Itvolga\Classes\ConsoleCommands;

use Espo\Core\Console\Command;
use Espo\Core\Console\Command\Params;
use Espo\Core\Console\IO;
use Espo\Core\Utils\Log;
use Espo\Modules\Itvolga\Tools\Import\BlobReceiver;
use Espo\Modules\Itvolga\Tools\Import\ImportError;
use Espo\Modules\Itvolga\Tools\Import\RecordWriter;
use Espo\Modules\Itvolga\Tools\Import\RunContext;
use Monolog\Handler\NullHandler;
use PDOException;
use stdClass;
use Throwable;

/**
 * Writer side of the Vtiger import (stage 06.2, docs/migration/import.md): `task espo -- itvolga-import`, run only by
 * scripts/import/importer.py. Source values come on stdin (never in argv or files: the stand user cannot read the
 * private directory), one JSON line each:
 *
 *   {"protocol": 2, "mode": "apply" | "check", "nonce": "<hex>", "adoptUserName": "admin" | null}   header
 *   {"key": "Contact:123", "entityType": "Contact", "vtigerId": 123, "attributes": {…}, "links": {…}, …}
 *   {"key": "Attachment:9", "entityType": "Attachment", "vtigerId": 9, …, "file": {"size": n, "sha256": "…",
 *    "chunks": k}}  followed (apply only) by k lines {"seq": i, "data": "<base64>"} — the bytes of the file (06.3)
 *   {"op": "inventory", "entityType": "Contact"}
 *   {"op": "remove", "key": "remove:Contact:123", "entityType": "Contact", "vtigerId": 123}   protocol 3 (06.4)
 *   {"op": "telephonyRules"} | {"op": "callInventory"} | {"op": "callHistory", "key": "cdr:<linkedid>", …}   stage
 *    07.2: the classification rules of the installation, the keys of its Asterisk calls by owner, a call of the CDR
 *    history (CdrCallWriter; additive operation kinds, the protocol number stays)
 *
 * Every operation line is answered on stdout with `#itv#<nonce>#<json>` (status, ids, attribute names, closed error
 * codes — never values), then `{"done": n, "swept": k}`; after a COMMIT that failed (`transaction_failed`) the command
 * stops there and `done` counts the lines read. Exception messages are never printed (they may quote values); the
 * application log is muted while the command runs (a failed SQL statement would be logged with its values). Protocol 1
 * (stage 06.2) is the same without files; protocol 3 (stage 06.4) adds `keyRange` and `ownedTypes` to the header
 * (RunContext: removals, owned links), and the `remove` operation.
 *
 * An apply session holds an exclusive lock (one writer per installation) and first removes the part files of a writer
 * that was killed (`swept`): under the lock no other writer can own them.
 */
class Import implements Command
{
    private const PROTOCOLS = [1, 2, 3];
    private const MAX_LINE = 8 * 1024 * 1024;
    private const LOCK = 'data/.itvolga-import.lock';

    public function __construct(
        private RecordWriter $writer,
        private BlobReceiver $blobs,
        private Log $log,
    ) {}

    public function run(Params $params, IO $io): void
    {
        $this->log->pushHandler(new NullHandler());
        $stdin = fopen('php://stdin', 'rb');
        $header = $stdin ? $this->decode(fgets($stdin, self::MAX_LINE)) : null;

        if (!$header || !in_array($header->protocol ?? null, self::PROTOCOLS, true) ||
            !in_array($header->mode ?? null, ['apply', 'check'], true)
            || !is_string($header->nonce ?? null) || !preg_match('/^[0-9a-f]{16,64}$/', $header->nonce)) {
            $io->writeErrorLine('itvolga-import: bad header');
            $io->setExitStatus(1);

            return;
        }

        $prefix = "#itv#{$header->nonce}#";

        try {
            $run = RunContext::fromHeader($header);
        } catch (ImportError) {
            $io->writeErrorLine('itvolga-import: bad header');
            $io->setExitStatus(1);

            return;
        }

        $lock = $header->mode === 'apply' ? fopen(self::LOCK, 'c') : null;

        if ($lock === false || ($lock && !flock($lock, LOCK_EX | LOCK_NB))) {
            $io->writeErrorLine('itvolga-import: busy'); // another writer applies to this installation
            $io->setExitStatus(1);

            return;
        }

        $swept = $lock ? $this->blobs->sweep() : 0;
        $count = 0;

        while (($line = fgets($stdin, self::MAX_LINE)) !== false) {
            if (trim($line) === '') {
                continue;
            }

            $count++;
            $op = $this->decode($line);
            $result = ['key' => is_string($op->key ?? null) ? $op->key : null];

            try {
                if (!$op) {
                    throw new ImportError('bad_frame');
                }

                // the bytes of a file follow its operation: read (and checked) before the operation runs
                $blob = $header->mode === 'apply' && isset($op->file->chunks) && $header->protocol >= 2 ?
                    $this->blobs->receive($stdin, $op->file, self::MAX_LINE) : null;

                $result += match ($op->op ?? null) {
                    null => $this->writer->handle($op, $header->mode === 'check', $run, $blob),
                    'inventory' => $this->writer->inventory((string) ($op->entityType ?? '')),
                    'remove' => $this->writer->remove($op, $header->mode === 'check', $run),
                    'callHistory' => $this->writer->history($op, $header->mode === 'check'),
                    'telephonyRules' => $this->writer->telephonyRules(),
                    'callInventory' => $this->writer->callInventory(),
                    default => throw new ImportError('bad_operation'),
                };
            } catch (ImportError $e) {
                $result += ['status' => 'error', 'error' => $e->reason, 'attributes' => $e->attributes];
            } catch (PDOException $e) {
                $result += ['status' => 'error', 'error' => 'db:' . $e->getCode()];
            } catch (Throwable $e) {
                $result += ['status' => 'error', 'error' => 'exception:' . (new \ReflectionClass($e))->getShortName()];
            } finally {
                $this->blobs->cleanup(); // a part file never outlives its operation
            }

            echo $prefix, json_encode($result, JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE), "\n";
            flush();

            if (($result['error'] ?? null) === 'transaction_failed') {
                break; // an uncertain COMMIT: the run stops (the importer sees fewer answers than operations)
            }
        }

        echo $prefix, json_encode(['done' => $count, 'swept' => $swept]), "\n";
    }

    private function decode(string|false $line): ?stdClass
    {
        if ($line === false) {
            return null;
        }

        try {
            $value = json_decode($line, false, 512, JSON_THROW_ON_ERROR);
        } catch (Throwable) {
            return null;
        }

        return $value instanceof stdClass ? $value : null;
    }
}
