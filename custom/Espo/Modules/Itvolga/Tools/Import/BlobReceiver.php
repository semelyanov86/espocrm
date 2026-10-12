<?php

namespace Espo\Modules\Itvolga\Tools\Import;

use Espo\Core\Utils\File\Manager as FileManager;
use stdClass;

/**
 * Bytes of an imported file (stage 06.3, import.md «Файлы»). They come only on stdin, right after their Attachment
 * operation, as `file.chunks` lines `{"seq": n, "data": "<base64 ≤ 3 MiB>"}` (a frame stays under the line limit of
 * the protocol). Every declared line is consumed even after an error, so the next operation is read in frame. The
 * bytes are written to a part file next to the upload storage, hashed on the way and checked against the declared
 * size and sha256 before anything can use them; a part file never outlives the command.
 */
class BlobReceiver
{
    public const DIR = 'data/upload/';
    private const PART = '.itvolga-import-';
    private const MAX_CHUNKS = 100000;

    /** @var array<string, true> part files this instance received and may still have to remove */
    private array $parts = [];

    public function __construct(private FileManager $fileManager) {}

    /**
     * @param resource $stdin
     * @throws ImportError file_frame, file_truncated, file_size, file_hash
     */
    public function receive($stdin, stdClass $file, int $maxLine): Blob
    {
        $chunks = $file->chunks ?? null;
        $size = $file->size ?? null;
        $sha256 = $file->sha256 ?? null;

        if (!is_int($chunks) || $chunks < 1 || $chunks > self::MAX_CHUNKS || !is_int($size) || $size < 0 ||
            !is_string($sha256) || !preg_match('/^[0-9a-f]{64}$/', $sha256)) {
            throw new ImportError('file_frame'); // the chunk count itself is unknown: nothing to consume
        }

        $path = self::DIR . self::PART . bin2hex(random_bytes(12)) . '.part';
        $handle = fopen($path, 'xb');
        $error = $handle === false ? 'file_storage' : null;
        $this->parts[$path] = true;
        $hash = hash_init('sha256');
        $received = 0;

        for ($seq = 0; $seq < $chunks; $seq++) {
            $line = fgets($stdin, $maxLine);

            if ($line === false) {
                $error = 'file_truncated';

                break;
            }

            $frame = json_decode($line);
            $bytes = is_object($frame) && ($frame->seq ?? null) === $seq && is_string($frame->data ?? null) ?
                base64_decode($frame->data, true) : false;

            if ($bytes === false) {
                $error ??= 'file_frame';

                continue;
            }

            if ($error === null && fwrite($handle, $bytes) !== strlen($bytes)) {
                $error = 'file_storage';
            }

            hash_update($hash, $bytes);
            $received += strlen($bytes);
        }

        if ($handle !== false) {
            fclose($handle);
        }

        $error ??= $received !== $size ? 'file_size' : (hash_final($hash) !== $sha256 ? 'file_hash' : null);

        if ($error !== null) {
            $this->discard($path);

            throw new ImportError($error);
        }

        return new Blob($path, $size, $sha256);
    }

    /**
     * Moves the received bytes to their storage path (atomic within the upload directory).
     */
    public function place(Blob $blob, string $target): void
    {
        if (!$this->isPart($blob->path) || !is_file($blob->path) || !rename($blob->path, $target)) {
            throw new ImportError('file_storage');
        }

        unset($this->parts[$blob->path]);
        $this->fileManager->getPermissionUtils()->setDefaultPermissions($target);
    }

    /**
     * Removes a part file (any instance may: the command receives, the attachment writer places or discards).
     */
    public function discard(string $path): void
    {
        if ($this->isPart($path) && is_file($path)) {
            @unlink($path);
        }

        unset($this->parts[$path]);
    }

    /**
     * Part files left by a writer that was killed (its `finally` never ran). Called at the start of an apply session
     * under the writer lock (no other writer is alive), so every part file left is stale (stage 06.4).
     *
     * @return int part files removed
     */
    public function sweep(): int
    {
        $removed = 0;

        foreach (glob(self::DIR . self::PART . '*.part') ?: [] as $path) {
            if ($this->isPart($path) && is_file($path) && @unlink($path)) {
                $removed++;
            }
        }

        return $removed;
    }

    private function isPart(string $path): bool
    {
        return str_starts_with($path, self::DIR . self::PART) && !str_contains(substr($path, strlen(self::DIR)), '/');
    }

    /**
     * Removes every part file of this command (end of the command, or an interrupted operation).
     */
    public function cleanup(): void
    {
        foreach (array_keys($this->parts) as $path) {
            $this->discard($path);
        }
    }

    /**
     * 'equal' when the stored file has the size and sha256 of the source, 'missing' or 'differs' otherwise.
     */
    public static function state(string $path, int $size, string $sha256): string
    {
        if (!is_file($path)) {
            return 'missing';
        }

        return filesize($path) === $size && hash_file('sha256', $path) === $sha256 ? 'equal' : 'differs';
    }
}
