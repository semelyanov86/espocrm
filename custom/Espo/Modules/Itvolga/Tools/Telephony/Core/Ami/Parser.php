<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Telephony\Core\Ami;

/**
 * Splits the AMI byte stream into messages. TCP delivers arbitrary pieces: feed() keeps the incomplete tail for the
 * next call. The greeting line «Asterisk Call Manager/<version>» comes once, without an empty line after it; messages
 * are header lines «Name: value» ended by an empty line (CRLF; a bare LF is accepted too). A value keeps everything
 * after the first colon and one space. Limits protect the long-running listener from an endless message.
 */
final class Parser
{
    public const MAX_MESSAGE = 65536;
    public const MAX_BUFFER = 1048576;
    private const BANNER = 'Asterisk Call Manager/';

    private string $buffer = '';
    private bool $bannerDone = false;
    private ?string $banner = null;

    /**
     * @return list<Message>
     * @throws ProtocolError
     */
    public function feed(string $bytes): array
    {
        $this->buffer .= $bytes;

        if (strlen($this->buffer) > self::MAX_BUFFER) {
            throw new ProtocolError(ProtocolError::BUFFER_TOO_LARGE);
        }

        $this->buffer = str_replace("\r\n", "\n", $this->buffer);

        if (!$this->bannerDone) {
            if (strlen($this->buffer) < strlen(self::BANNER) && str_starts_with(self::BANNER, $this->buffer)) {
                return [];
            }

            if (str_starts_with($this->buffer, self::BANNER)) {
                $end = strpos($this->buffer, "\n");

                if ($end === false) {
                    return [];
                }

                $this->banner = substr($this->buffer, 0, $end);
                $this->buffer = substr($this->buffer, $end + 1);
            }

            $this->bannerDone = true;
        }

        $messages = [];

        while (($end = strpos($this->buffer, "\n\n")) !== false) {
            if ($end > self::MAX_MESSAGE) {
                throw new ProtocolError(ProtocolError::MESSAGE_TOO_LARGE);
            }

            $block = substr($this->buffer, 0, $end);
            $this->buffer = substr($this->buffer, $end + 2);
            $message = self::parseBlock($block);

            if ($message !== null) {
                $messages[] = $message;
            }
        }

        if (strlen($this->buffer) > self::MAX_MESSAGE) {
            throw new ProtocolError(ProtocolError::MESSAGE_TOO_LARGE);
        }

        return $messages;
    }

    public function banner(): ?string
    {
        return $this->banner;
    }

    private static function parseBlock(string $block): ?Message
    {
        $headers = [];

        foreach (explode("\n", ltrim($block, "\n")) as $line) {
            $line = rtrim($line, "\r");
            $colon = strpos($line, ':');

            if ($colon === false || $colon === 0) {
                continue;
            }

            $value = substr($line, $colon + 1);

            if (str_starts_with($value, ' ')) {
                $value = substr($value, 1);
            }

            $headers[] = [substr($line, 0, $colon), $value];
        }

        return $headers === [] ? null : new Message($headers);
    }
}
