<?php

namespace Espo\Modules\Itvolga\Classes\ConsoleCommands;

use Espo\Core\Console\Command;
use Espo\Core\Console\Command\Params;
use Espo\Core\Console\IO;
use Espo\Core\Utils\Log;
use Espo\Modules\Itvolga\Tools\Import\ImportError;
use Espo\Modules\Itvolga\Tools\Import\RecordWriter;
use Monolog\Handler\NullHandler;
use PDOException;
use stdClass;
use Throwable;

/**
 * Writer side of the Vtiger import (stage 06.2, docs/migration/import.md): `task espo -- itvolga-import`, run only by
 * scripts/import/importer.py. Source values come on stdin (never in argv or files: the stand user cannot read the
 * private directory), one JSON line each:
 *
 *   {"protocol": 1, "mode": "apply" | "check", "nonce": "<hex>", "adoptUserName": "admin" | null}   header
 *   {"key": "Contact:123", "entityType": "Contact", "vtigerId": 123, "attributes": {…}, "links": {…}, …}
 *   {"op": "inventory", "entityType": "Contact"}
 *
 * Every line is answered on stdout with `#itv#<nonce>#<json>` (status, ids, attribute names, closed error codes —
 * never values), then `{"done": n}`. Exception messages are never printed (they may quote values); the application
 * log is muted while the command runs (a failed SQL statement would be logged with its values).
 */
class Import implements Command
{
    private const PROTOCOL = 1;
    private const MAX_LINE = 8 * 1024 * 1024;

    public function __construct(
        private RecordWriter $writer,
        private Log $log,
    ) {}

    public function run(Params $params, IO $io): void
    {
        $this->log->pushHandler(new NullHandler());
        $stdin = fopen('php://stdin', 'rb');
        $header = $stdin ? $this->decode(fgets($stdin, self::MAX_LINE)) : null;

        if (!$header || ($header->protocol ?? null) !== self::PROTOCOL || !in_array($header->mode ?? null, ['apply', 'check'], true)
            || !is_string($header->nonce ?? null) || !preg_match('/^[0-9a-f]{16,64}$/', $header->nonce)) {
            $io->writeErrorLine('itvolga-import: bad header');
            $io->setExitStatus(1);

            return;
        }

        $prefix = "#itv#{$header->nonce}#";
        $adopt = is_string($header->adoptUserName ?? null) ? $header->adoptUserName : null;
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

                $result += ($op->op ?? null) === 'inventory' ?
                    $this->writer->inventory((string) ($op->entityType ?? '')) :
                    $this->writer->handle($op, $header->mode === 'check', $adopt);
            } catch (ImportError $e) {
                $result += ['status' => 'error', 'error' => $e->reason, 'attributes' => $e->attributes];
            } catch (PDOException $e) {
                $result += ['status' => 'error', 'error' => 'db:' . $e->getCode()];
            } catch (Throwable $e) {
                $result += ['status' => 'error', 'error' => 'exception:' . (new \ReflectionClass($e))->getShortName()];
            }

            echo $prefix, json_encode($result, JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE), "\n";
            flush();
        }

        echo $prefix, json_encode(['done' => $count]), "\n";
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
