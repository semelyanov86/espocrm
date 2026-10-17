<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Telephony;

use Espo\Modules\Itvolga\Tools\Telephony\Core\RecordingPath;
use Espo\ORM\EntityManager;
use Espo\ORM\Query\SelectBuilder;

/**
 * Call recordings below the configured recordings root (D-171): one check for the player (RecordingService), the live
 * writer and the history import of stage 07.2 (D-177) — a path the integration stored, in the YYYY/MM/DD/<name>.wav
 * layout, a regular file inside the root with no symbolic link anywhere on the way. Reads only.
 */
class RecordingFiles
{
    public const OK = 'ok';
    private const CHUNK = 1 << 20;

    public function __construct(
        private EntityManager $entityManager,
        private TelephonyConfig $config,
    ) {}

    /**
     * The absolute path of a stored recording, or null: an unsafe path, no root, a missing or irregular file, a link.
     */
    public function path(?string $relative): ?string
    {
        if ($relative === null || !RecordingPath::isSafe($relative)) {
            return null;
        }

        $root = $this->config->recordingRoot();
        $realRoot = $root !== null ? realpath($root) : false;

        if ($realRoot === false || !is_dir($realRoot)) {
            return null;
        }

        $path = $realRoot . '/' . $relative;

        // realpath() resolves every link on the way: equal only when no part below the root is a symbolic link.
        return realpath($path) === $path && is_file($path) && !is_link($path) ? $path : null;
    }

    /**
     * The file at a path a snapshot inventory describes: `ok`, or why not (`unsafe`, `no_root`, `missing`, `size`,
     * `sha256`, `unreadable`) — closed codes, never the path.
     */
    public function verify(string $relative, int $size, string $sha256): string
    {
        if (!RecordingPath::isSafe($relative)) {
            return 'unsafe';
        }

        $root = $this->config->recordingRoot();

        if ($root === null || realpath($root) === false) {
            return 'no_root';
        }

        $path = $this->path($relative);

        if ($path === null) {
            return 'missing';
        }

        if (filesize($path) !== $size) {
            return 'size';
        }

        $handle = @fopen($path, 'rb');

        if ($handle === false) {
            return 'unreadable';
        }

        $context = hash_init('sha256');

        while (!feof($handle)) {
            $chunk = fread($handle, self::CHUNK);

            if ($chunk === false) {
                fclose($handle);

                return 'unreadable';
            }

            hash_update($context, $chunk);
        }

        fclose($handle);

        return hash_equals($sha256, hash_final($context)) ? self::OK : 'sha256';
    }

    /**
     * The production file name (sub-monitor) carries the minute and the two numbers, not the call: a second call
     * between the same numbers within a minute overwrites the file of the first. A path stored on another Call
     * (deleted ones too) has no certain owner (external review 2026-10-17).
     */
    public function isShared(string $relative, ?string $callId): bool
    {
        $where = ['cRecordingPath' => $relative];

        if ($callId !== null) {
            $where['id!='] = $callId;
        }

        $query = SelectBuilder::create()
            ->from('Call')
            ->select(['id'])
            ->where($where)
            ->withDeleted()
            ->limit(0, 1)
            ->build();

        return iterator_to_array($this->entityManager->getQueryExecutor()->execute($query), false) !== [];
    }
}
