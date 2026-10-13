<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Telephony\Core\Ami;

/**
 * Wire form of an AMI action. A value with CR, LF or NUL would start a new header or a new action (header injection),
 * a header name outside [A-Za-z0-9-] is not a header: both are refused before anything is sent.
 */
final class Action
{
    /**
     * @param array<string, string|list<string>> $headers repeated headers (Variable) as a list
     * @throws ProtocolError
     */
    public static function toWire(string $action, array $headers = []): string
    {
        $lines = [self::line('Action', $action)];

        foreach ($headers as $name => $values) {
            foreach ((array) $values as $value) {
                $lines[] = self::line((string) $name, $value);
            }
        }

        return implode("\r\n", $lines) . "\r\n\r\n";
    }

    /**
     * @throws ProtocolError
     */
    private static function line(string $name, string $value): string
    {
        if (!preg_match('/^[A-Za-z][A-Za-z0-9-]*$/', $name) || preg_match('/[\r\n\0]/', $value)) {
            throw new ProtocolError(ProtocolError::BAD_HEADER);
        }

        return $name . ': ' . $value;
    }
}
