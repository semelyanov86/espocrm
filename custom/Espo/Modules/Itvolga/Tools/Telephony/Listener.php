<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Telephony;

use Espo\Modules\Itvolga\Tools\Telephony\Core\CallSnapshot;
use Espo\Modules\Itvolga\Tools\Telephony\Core\CallTracker;
use InvalidArgumentException;
use Throwable;

/**
 * The AMI listener (D-166): one session with the listener user, CallTracker in memory, CallWriter for the CRM.
 *
 * After login it asks CoreShowChannels and reconciles the channels with the calls the CRM stored as live (calls that
 * ended while nobody listened are closed as lost), then follows the events. Every 15 s the live calls are marked as
 * seen and the settings re-read (the fallback extension of the administrator page applies to the next call), every
 * 10 min the channels are compared again, every 30 s a Ping proves the session (no data for 90 s → exit); an
 * integration switched off in the settings ends the process (exit 78, not restarted).
 * Any AMI or database failure ends the process with a code; systemd starts a new one, which reconciles — a single
 * recovery path, a fresh database connection and the current code and settings every time. SIGTERM stops it cleanly.
 * Nothing it logs or writes to the status file carries numbers, names or secrets.
 */
class Listener
{
    public const EXIT_OK = 0;
    public const EXIT_UNAVAILABLE = 69;
    public const EXIT_RETRY = 75;
    public const EXIT_NOT_CONFIGURED = 78;

    private const READ_TIMEOUT = 1.0;
    private const TOUCH_EVERY = 15.0;
    private const STATUS_EVERY = 5.0;
    private const PING_EVERY = 30.0;
    private const SILENCE_LIMIT = 90.0;
    private const RECONCILE_EVERY = 600.0;
    private const RECONCILE_STALE = 60.0;
    private const SWEEP_EVERY = 60.0;
    private const PURGE_EVERY = 3600.0;
    private const CARD_GRACE = 30.0;

    private bool $stop = false;
    private int $events = 0;
    private int $writes = 0;

    public function __construct(
        private TelephonyConfig $config,
        private CallWriter $writer,
        private ExtensionDirectory $directory,
    ) {}

    public function stop(): void
    {
        $this->stop = true;
    }

    public function run(StatusFile $status): int
    {
        $status->write(['state' => 'starting', 'startedAt' => gmdate('Y-m-d\TH:i:s\Z')]);
        $address = $this->config->amiAddress();
        $credentials = $this->config->credentials('listener');

        if (!$this->config->isEnabled() || $address === null || $credentials === null) {
            $status->write(['state' => 'not_configured']);

            return self::EXIT_NOT_CONFIGURED;
        }

        try {
            $tracker = new CallTracker($this->config->trackerSettings());
        } catch (InvalidArgumentException) {
            $status->write(['state' => 'bad_rules']);

            return self::EXIT_NOT_CONFIGURED;
        }

        $lock = @fopen(TelephonyConfig::LOCK_FILE, 'c');

        if ($lock === false || !flock($lock, LOCK_EX | LOCK_NB)) {
            $status->write(['state' => 'already_running']);

            return self::EXIT_RETRY;
        }

        $ami = null;

        try {
            $status->write(['state' => 'connecting']);
            $ami = AmiConnection::open($address, $credentials, true);
            $this->reconcile($ami, $tracker, 0.0, true);
            $status->write(['state' => 'connected', 'connectedAt' => gmdate('Y-m-d\TH:i:s\Z')]);

            $last = array_fill_keys(['touch', 'status', 'ping', 'reconcile', 'sweep', 'purge'], microtime(true));

            while (!$this->stop) {
                foreach ($ami->read(self::READ_TIMEOUT) as $message) {
                    if ($message->event() === null) {
                        continue;
                    }

                    $this->events++;
                    $this->apply($tracker->accept($message, microtime(true)));
                }

                $now = microtime(true);

                if ($now - $last['touch'] >= self::TOUCH_EVERY) {
                    $this->writer->touch($tracker->liveStoredIds(), $now);
                    $this->config->refresh();
                    $last['touch'] = $now;

                    if (!$this->config->isEnabled()) {
                        // switched off (itvolga-setup-telephony {"enabled": false}): no more calls; 78 — systemd
                        // does not restart; the next start reconciles the calls left in progress (review 2026-10-17)
                        $status->write($this->counters($tracker, 'disabled'));

                        return self::EXIT_NOT_CONFIGURED;
                    }
                }

                if ($now - $last['ping'] >= self::PING_EVERY) {
                    if ($ami->secondsSinceData() > self::SILENCE_LIMIT) {
                        throw new AmiError(AmiError::TIMEOUT);
                    }

                    $ami->send('Ping', []);
                    $last['ping'] = $now;
                }

                if ($now - $last['reconcile'] >= self::RECONCILE_EVERY) {
                    $this->reconcile($ami, $tracker, self::RECONCILE_STALE, false);
                    $last['reconcile'] = $now;
                }

                if ($now - $last['sweep'] >= self::SWEEP_EVERY) {
                    $tracker->sweep($now);
                    $last['sweep'] = $now;
                }

                if ($now - $last['purge'] >= self::PURGE_EVERY) {
                    $this->writer->purge($now);
                    $last['purge'] = $now;
                }

                if ($now - $last['status'] >= self::STATUS_EVERY) {
                    $status->write($this->counters($tracker, 'connected'));
                    $last['status'] = $now;
                }
            }

            $status->write($this->counters($tracker, 'stopped'));

            return self::EXIT_OK;
        } catch (AmiError $e) {
            $status->write($this->counters($tracker, $e->reason));

            return self::EXIT_UNAVAILABLE;
        } catch (Throwable $e) {
            $status->write($this->counters($tracker, 'error_' . self::shortClass($e)));

            return self::EXIT_RETRY;
        } finally {
            $ami?->close();
            flock($lock, LOCK_UN);
            fclose($lock);
        }
    }

    /**
     * @throws AmiError
     */
    private function reconcile(AmiConnection $ami, CallTracker $tracker, float $staleAfter, bool $adoptUnknown): void
    {
        $channels = $ami->requestList('CoreShowChannels', 'CoreShowChannel', 'CoreShowChannelsComplete', 15.0);
        $now = microtime(true);
        $this->apply($tracker->reconcile($channels, $this->writer->openCalls(), $now, $staleAfter, $adoptUnknown));

        // A card or a click-to-call request of a call that is neither on the PBX nor in memory (it ended while the
        // listener was away before any Call was stored) is closed too (review 2026-10-17).
        $alive = $tracker->trackedIds();

        foreach ($channels as $item) {
            $alive[] = (string) $item->get('Linkedid');
        }

        $this->writer->closeStale(array_values(array_unique(array_filter($alive))), $now - self::CARD_GRACE);
    }

    /**
     * @param list<CallSnapshot> $snapshots
     */
    private function apply(array $snapshots): void
    {
        foreach ($snapshots as $snapshot) {
            $this->writer->apply($snapshot, microtime(true));
            $this->writes++;
        }
    }

    /**
     * @return array<string, int|string>
     */
    private function counters(CallTracker $tracker, string $state): array
    {
        return [
            'state' => $state,
            'events' => $this->events,
            'writes' => $this->writes,
            'calls' => $tracker->count(),
            'liveCalls' => count($tracker->liveStoredIds()),
            'ambiguousExtensions' => $this->directory->ambiguousCount(),
        ];
    }

    private static function shortClass(Throwable $e): string
    {
        $parts = explode('\\', $e::class);

        return (string) end($parts);
    }
}
