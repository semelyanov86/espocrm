<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Telephony;

/**
 * State of the listener for `task telephony:status` and the stand health check (data/itvolga-telephony-status.json):
 * process, AMI state, time of the last sign of life and counters. No numbers, names or secrets.
 */
class StatusFile
{
    /** @var array<string, int|string|null> */
    private array $data = [];

    public function __construct(private string $path = TelephonyConfig::STATUS_FILE) {}

    /**
     * @param array<string, int|string|null> $values
     */
    public function write(array $values): void
    {
        $this->data = array_merge($this->data, $values, [
            'pid' => getmypid() ?: null,
            'aliveAt' => gmdate('Y-m-d\TH:i:s\Z'),
        ]);

        $tmp = $this->path . '.tmp';

        if (@file_put_contents($tmp, json_encode($this->data, JSON_PRETTY_PRINT) . "\n") !== false) {
            @rename($tmp, $this->path);
        }
    }
}
