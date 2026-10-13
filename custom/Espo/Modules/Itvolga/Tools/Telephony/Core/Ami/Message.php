<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Telephony\Core\Ami;

/**
 * One AMI message (an event, a response or a list item): the ordered headers as received. Header names compare
 * case-insensitively; the first header of a repeated name wins in get().
 */
final class Message
{
    /**
     * @param list<array{string, string}> $headers
     */
    public function __construct(public readonly array $headers) {}

    /**
     * @param array<string, string> $map
     */
    public static function of(array $map): self
    {
        $headers = [];

        foreach ($map as $name => $value) {
            $headers[] = [(string) $name, $value];
        }

        return new self($headers);
    }

    public function get(string $name): ?string
    {
        foreach ($this->headers as [$header, $value]) {
            if (strcasecmp($header, $name) === 0) {
                return $value;
            }
        }

        return null;
    }

    public function event(): ?string
    {
        return $this->get('Event');
    }

    public function response(): ?string
    {
        return $this->get('Response');
    }

    public function actionId(): ?string
    {
        return $this->get('ActionID');
    }
}
