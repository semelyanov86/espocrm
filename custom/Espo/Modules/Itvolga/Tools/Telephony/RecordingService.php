<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Telephony;

use Espo\Core\Acl;
use Espo\Core\Exceptions\Forbidden;
use Espo\Core\Exceptions\NotFound;
use Espo\Core\Field\LinkParent;
use Espo\Entities\ActionHistoryRecord;
use Espo\Entities\User;
use Espo\Modules\Itvolga\Tools\Telephony\Core\ByteRange;
use Espo\Modules\Itvolga\Tools\Telephony\Core\CallSnapshot;
use Espo\Modules\Itvolga\Tools\Telephony\Core\RecordingPath;
use Espo\ORM\EntityManager;
use GuzzleHttp\Psr7\LimitStream;
use GuzzleHttp\Psr7\Stream;
use Psr\Http\Message\StreamInterface;

/**
 * Playback of a call recording (owner decision 2026-10-13, D-171): read access to the Call and to its field
 * «Запись разговора» (cRecording: roles may forbid it), a finished call with a recording. The file is found only from
 * the path the integration stored on the Call, below the configured recordings root, with no symbolic link anywhere
 * on the way and as a regular WAV file; the request names a Call, never a file. A range request (seeking) is
 * answered with 206. Every playback is logged in Action History (action «listen»): a response is logged unless
 * the same user's playback of the same call is already logged for the last 10 minutes (seeking would add rows).
 */
class RecordingService
{
    public const FIELD = 'cRecording';
    public const ACTION_LISTEN = 'listen';
    private const LOG_WINDOW = 600;

    public function __construct(
        private EntityManager $entityManager,
        private Acl $acl,
        private User $user,
        private TelephonyConfig $config,
    ) {}

    /**
     * @return array{status: int, headers: array<string, string>, body: ?StreamInterface}
     * @throws NotFound
     * @throws Forbidden
     */
    public function open(string $callId, ?string $rangeHeader): array
    {
        $call = $this->entityManager->getEntityById('Call', $callId) ?? throw new NotFound();

        if (!$this->acl->checkEntityRead($call) || !$this->acl->checkField('Call', self::FIELD, Acl\Table::ACTION_READ)) {
            throw new Forbidden('No access to the recording.');
        }

        $relative = (string) $call->get('cRecordingPath');

        if (!$call->get(self::FIELD) || !in_array($call->get('cLiveState'), [CallSnapshot::ENDED, CallSnapshot::LOST], true)
            || !RecordingPath::isSafe($relative)) {
            throw new NotFound('No recording.');
        }

        $handle = $this->openFile($relative) ?? throw new NotFound('No recording.');
        $size = (int) (fstat($handle)['size'] ?? 0);
        $range = ByteRange::parse($rangeHeader, $size);

        if ($range->kind === ByteRange::UNSATISFIABLE) {
            fclose($handle);

            return ['status' => 416, 'headers' => ['Content-Range' => "bytes */$size"], 'body' => null];
        }

        $this->log($call->getId());

        $headers = [
            'Content-Type' => 'audio/wav',
            'Accept-Ranges' => 'bytes',
            'Content-Length' => (string) $range->length(),
            'Content-Disposition' => 'inline; filename="call-' . $call->getId() . '.wav"',
        ];
        $stream = new Stream($handle);

        if ($range->kind === ByteRange::PARTIAL) {
            $headers['Content-Range'] = "bytes {$range->start}-{$range->end}/$size";

            return ['status' => 206, 'headers' => $headers, 'body' => new LimitStream($stream, $range->length(), $range->start)];
        }

        return ['status' => 200, 'headers' => $headers, 'body' => $stream];
    }

    /**
     * @return ?resource
     */
    private function openFile(string $relative)
    {
        $root = $this->config->recordingRoot();
        $realRoot = $root !== null ? realpath($root) : false;

        if ($realRoot === false || !is_dir($realRoot)) {
            return null;
        }

        $path = $realRoot . '/' . $relative;

        // realpath() resolves every link on the way: equal only when no part below the root is a symbolic link.
        if (realpath($path) !== $path || !is_file($path) || is_link($path)) {
            return null;
        }

        $handle = @fopen($path, 'rb');

        return $handle === false ? null : $handle;
    }

    private function log(string $callId): void
    {
        $recent = $this->entityManager->getRDBRepositoryByClass(ActionHistoryRecord::class)
            ->where([
                'action' => self::ACTION_LISTEN,
                'userId' => $this->user->getId(),
                'targetType' => 'Call',
                'targetId' => $callId,
                'createdAt>' => gmdate('Y-m-d H:i:s', time() - self::LOG_WINDOW),
            ])
            ->findOne();

        if ($recent) {
            return;
        }

        $record = $this->entityManager->getRDBRepositoryByClass(ActionHistoryRecord::class)->getNew();
        $record
            ->setAction(self::ACTION_LISTEN)
            ->setUserId($this->user->getId())
            ->setAuthTokenId($this->user->get('authTokenId'))
            ->setAuthLogRecordId($this->user->get('authLogRecordId'))
            ->setIpAddress($this->user->get('ipAddress'))
            ->setTarget(LinkParent::create('Call', $callId));
        $record->set('data', (object) ['field' => self::FIELD]);

        $this->entityManager->saveEntity($record);
    }
}
