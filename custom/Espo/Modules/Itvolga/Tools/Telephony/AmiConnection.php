<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Telephony;

use Espo\Modules\Itvolga\Tools\Telephony\Core\Ami\Action;
use Espo\Modules\Itvolga\Tools\Telephony\Core\Ami\Inbox;
use Espo\Modules\Itvolga\Tools\Telephony\Core\Ami\Message;
use Espo\Modules\Itvolga\Tools\Telephony\Core\Ami\Parser;
use Espo\Modules\Itvolga\Tools\Telephony\Core\Ami\ProtocolError;

/**
 * One AMI session over a loopback TCP address or a local Unix socket (D-169). Responses are matched by ActionID in
 * the Inbox; events read meanwhile — before or after the awaited answer in the same read — wait there for read().
 */
final class AmiConnection
{
    /** @var resource */
    private $socket;
    private Parser $parser;
    private Inbox $inbox;
    private int $counter = 0;
    private float $lastReceivedAt;

    private function __construct(string $address, float $timeout)
    {
        if (!TelephonyConfig::isLocalAddress($address)) {
            throw new AmiError(AmiError::CONNECT);
        }

        $socket = @stream_socket_client($address, $code, $message, $timeout);

        if ($socket === false) {
            throw new AmiError(AmiError::CONNECT);
        }

        stream_set_blocking($socket, false);
        $this->socket = $socket;
        $this->parser = new Parser();
        $this->inbox = new Inbox();
        $this->lastReceivedAt = microtime(true);
    }

    /**
     * @param array{string, string} $credentials
     * @throws AmiError
     */
    public static function open(string $address, array $credentials, bool $events, float $timeout = 5.0): self
    {
        $connection = new self($address, $timeout);
        $response = $connection->request('Login', [
            'Username' => $credentials[0],
            'Secret' => $credentials[1],
            'Events' => $events ? 'on' : 'off',
        ], $timeout);

        if (strcasecmp((string) $response->response(), 'Success') !== 0) {
            $connection->close();

            throw new AmiError(AmiError::AUTH);
        }

        return $connection;
    }

    /**
     * Sends an action and waits for its response; every other message read meanwhile stays queued for read().
     *
     * @param array<string, string|list<string>> $headers
     * @throws AmiError
     */
    public function request(string $action, array $headers, float $timeout): Message
    {
        $id = $this->send($action, $headers);
        $this->inbox->expectResponse($id);
        $deadline = microtime(true) + $timeout;

        while (($response = $this->inbox->takeResponse($id)) === null) {
            if (microtime(true) >= $deadline) {
                throw new AmiError(AmiError::TIMEOUT);
            }

            $this->receive(max(0.0, $deadline - microtime(true)));
        }

        return $response;
    }

    /**
     * An action answered by a list of events (CoreShowChannels): the items up to the completion event.
     *
     * @return list<Message>
     * @throws AmiError
     */
    public function requestList(string $action, string $itemEvent, string $completeEvent, float $timeout): array
    {
        $id = $this->send($action, []);
        $this->inbox->expectList($id, $itemEvent, $completeEvent);
        $deadline = microtime(true) + $timeout;

        while (($items = $this->inbox->takeList($id)) === null) {
            if (microtime(true) >= $deadline) {
                throw new AmiError(AmiError::TIMEOUT);
            }

            $this->receive(max(0.0, $deadline - microtime(true)));
        }

        if ($items === false) {
            throw new AmiError(AmiError::DENIED);
        }

        return $items;
    }

    /**
     * Events and other messages not awaited by an action, waiting up to $timeout seconds for data when none is
     * queued.
     *
     * @return list<Message>
     * @throws AmiError
     */
    public function read(float $timeout): array
    {
        $queued = $this->inbox->drain();

        if ($queued !== []) {
            $this->receive(0.0);

            return [...$queued, ...$this->inbox->drain()];
        }

        $this->receive($timeout);

        return $this->inbox->drain();
    }

    /**
     * @param array<string, string|list<string>> $headers
     * @throws AmiError
     */
    public function send(string $action, array $headers): string
    {
        $id = 'itv' . getmypid() . '-' . (++$this->counter);

        try {
            $wire = Action::toWire($action, ['ActionID' => $id] + $headers);
        } catch (ProtocolError) {
            throw new AmiError(AmiError::PROTOCOL);
        }

        $written = 0;
        $deadline = microtime(true) + 5.0;

        while ($written < strlen($wire)) {
            $chunk = @fwrite($this->socket, substr($wire, $written));

            if ($chunk === false) {
                throw new AmiError(AmiError::CLOSED);
            }

            $written += $chunk;

            if ($chunk === 0) {
                if (microtime(true) > $deadline) {
                    throw new AmiError(AmiError::TIMEOUT);
                }

                usleep(10000);
            }
        }

        return $id;
    }

    public function secondsSinceData(): float
    {
        return microtime(true) - $this->lastReceivedAt;
    }

    public function close(): void
    {
        if (is_resource($this->socket)) {
            @fwrite($this->socket, Action::toWire('Logoff', ['ActionID' => 'itv-logoff']));
            @fclose($this->socket);
        }
    }

    /**
     * Reads what has arrived (waiting up to $timeout seconds) into the inbox: the whole batch, every message.
     *
     * @throws AmiError
     */
    private function receive(float $timeout): void
    {
        $read = [$this->socket];
        $write = $except = null;
        $seconds = (int) floor($timeout);
        $micro = (int) (($timeout - $seconds) * 1_000_000);
        $ready = @stream_select($read, $write, $except, $seconds, $micro);

        if ($ready === false || $ready === 0) {
            // Nothing yet, or interrupted by a signal (SIGTERM): the caller checks its deadline or stop flag.
            return;
        }

        $bytes = @fread($this->socket, 65536);

        if ($bytes === false || ($bytes === '' && feof($this->socket))) {
            throw new AmiError(AmiError::CLOSED);
        }

        $this->lastReceivedAt = microtime(true);

        try {
            foreach ($this->parser->feed($bytes) as $message) {
                $this->inbox->push($message);
            }
        } catch (ProtocolError) {
            throw new AmiError(AmiError::PROTOCOL);
        }
    }
}
