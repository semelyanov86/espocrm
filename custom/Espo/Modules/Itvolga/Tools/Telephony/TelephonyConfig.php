<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Telephony;

use Espo\Core\Utils\Config;
use Espo\Modules\Itvolga\Tools\Telephony\Core\TrackerSettings;
use InvalidArgumentException;

/**
 * Settings of the Asterisk integration (D-169). Secrets and the PBX description are system parameters
 * (data/config-internal.php, never in the API), written only by `itvolga-setup-telephony` from stdin:
 * - itvolgaTelephonyAmi: {address: tcp://127.0.0.1:5038 | unix:///…, listener: {username, secret}, dialer: {…}};
 * - itvolgaTelephonyRules: TrackerSettings keys + dialContext, originateTimeout (ms), callerIdTemplate;
 * - itvolgaTelephonyRecordings: {root: where EspoCRM reads the recordings, asteriskDir: where Asterisk writes them};
 * - itvolgaTelephonyEnabled (users read it: the phone links dial through the CRM);
 * - itvolgaTelephonyFallbackExtension (administrator setting, default 108).
 */
class TelephonyConfig
{
    public const DEFAULT_FALLBACK = '108';
    public const DEFAULT_DIAL_CONTEXT = 'call-out';
    public const DEFAULT_MONITOR_DIR = '/var/spool/asterisk/monitor';
    public const DEFAULT_CALLER_ID = '"{ext}" <{ext}>';
    public const STATUS_FILE = 'data/itvolga-telephony-status.json';
    public const LOCK_FILE = 'data/itvolga-telephony.lock';

    public function __construct(private Config $config) {}

    public function refresh(): void
    {
        $this->config->update();
    }

    public function isEnabled(): bool
    {
        return (bool) $this->config->get('itvolgaTelephonyEnabled') && $this->amiAddress() !== null;
    }

    public function amiAddress(): ?string
    {
        $address = $this->ami()['address'] ?? null;

        return is_string($address) && self::isLocalAddress($address) ? $address : null;
    }

    /**
     * @return ?array{string, string} [username, secret]
     */
    public function credentials(string $role): ?array
    {
        $item = $this->ami()[$role] ?? null;

        if (!is_array($item) || !is_string($item['username'] ?? null) || !is_string($item['secret'] ?? null)
            || $item['username'] === '' || $item['secret'] === '') {
            return null;
        }

        return [$item['username'], $item['secret']];
    }

    /**
     * @throws InvalidArgumentException
     */
    public function trackerSettings(): TrackerSettings
    {
        return TrackerSettings::fromArray($this->rules());
    }

    public function dialContext(): string
    {
        $context = $this->rules()['dialContext'] ?? self::DEFAULT_DIAL_CONTEXT;

        return is_string($context) && preg_match('/^[A-Za-z0-9_.-]{1,80}$/', $context) ? $context : self::DEFAULT_DIAL_CONTEXT;
    }

    public function originateTimeoutMs(): int
    {
        $value = $this->rules()['originateTimeout'] ?? 20000;

        return is_int($value) && $value >= 5000 && $value <= 120000 ? $value : 20000;
    }

    /**
     * Caller id of the Originate channel: the desk phone's own caller id, so that the dialplan routes the call as if
     * the user had dialled it (production: sub-ifrussia chooses the trunk by CALLERID(num)).
     */
    public function callerId(string $extension): string
    {
        $template = $this->rules()['callerIdTemplate'] ?? self::DEFAULT_CALLER_ID;

        if (!is_string($template) || !str_contains($template, '{ext}')) {
            $template = self::DEFAULT_CALLER_ID;
        }

        return str_replace('{ext}', $extension, $template);
    }

    public function recordingRoot(): ?string
    {
        $root = $this->recordings()['root'] ?? null;

        return is_string($root) && str_starts_with($root, '/') ? rtrim($root, '/') : null;
    }

    public function asteriskMonitorDir(): string
    {
        $dir = $this->recordings()['asteriskDir'] ?? self::DEFAULT_MONITOR_DIR;

        return is_string($dir) && str_starts_with($dir, '/') ? rtrim($dir, '/') : self::DEFAULT_MONITOR_DIR;
    }

    /**
     * The administrator's value as stored (null when never set).
     */
    public function fallbackExtensionSetting(): ?string
    {
        $value = $this->config->get('itvolgaTelephonyFallbackExtension');

        return is_string($value) && $value !== '' ? $value : null;
    }

    public function fallbackExtension(): string
    {
        $value = trim((string) $this->config->get('itvolgaTelephonyFallbackExtension'));

        return preg_match('/^[0-9]{2,10}$/', $value) ? $value : self::DEFAULT_FALLBACK;
    }

    /**
     * Only a loopback TCP address or a local Unix socket: the AMI is never reached over the network (D-169).
     */
    public static function isLocalAddress(string $address): bool
    {
        return (bool) preg_match('~^(tcp://(127\.0\.0\.1|\[::1\]):[0-9]{1,5}|unix:///[A-Za-z0-9_./-]+)$~', $address);
    }

    /**
     * @return array<string, mixed>
     */
    private function ami(): array
    {
        return self::toArray($this->config->get('itvolgaTelephonyAmi'));
    }

    /**
     * @return array<string, mixed>
     */
    private function rules(): array
    {
        return self::toArray($this->config->get('itvolgaTelephonyRules'));
    }

    /**
     * @return array<string, mixed>
     */
    private function recordings(): array
    {
        return self::toArray($this->config->get('itvolgaTelephonyRecordings'));
    }

    /**
     * @return array<string, mixed>
     */
    private static function toArray(mixed $value): array
    {
        if (is_object($value)) {
            $value = json_decode((string) json_encode($value), true);
        }

        return is_array($value) ? $value : [];
    }
}
