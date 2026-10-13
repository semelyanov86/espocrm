<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Telephony\Core;

/**
 * Where a call recording lives, relative to the recordings root. Asterisk reports the absolute file name of MixMonitor
 * (MIXMONITOR_FILENAME); the Call keeps only the part below the Asterisk monitor directory, in the layout the
 * production dialplan writes (`sub-monitor`: YYYY/MM/DD/<name>.wav). Anything else — another directory, «..», a
 * hidden or non-WAV file — is not a recording of this integration and is never stored nor served.
 */
final class RecordingPath
{
    private const SAFE = '~^[0-9]{4}/[0-9]{2}/[0-9]{2}/[^/.\\\\\x00][^/\\\\\x00]{0,200}\.wav$~';

    public static function relative(string $monitorDir, string $absolute): ?string
    {
        $prefix = rtrim($monitorDir, '/') . '/';

        if ($monitorDir === '' || !str_starts_with($absolute, $prefix)) {
            return null;
        }

        $relative = substr($absolute, strlen($prefix));

        return self::isSafe($relative) ? $relative : null;
    }

    public static function isSafe(string $relative): bool
    {
        return (bool) preg_match(self::SAFE, $relative) && !in_array('..', explode('/', $relative), true);
    }
}
