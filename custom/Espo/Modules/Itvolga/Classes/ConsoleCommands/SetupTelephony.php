<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Classes\ConsoleCommands;

use Espo\Core\Console\Command;
use Espo\Core\Console\Command\Params;
use Espo\Core\Console\IO;
use Espo\Core\Utils\Config\ConfigWriter;
use Espo\Modules\Itvolga\Tools\Telephony\AmiConnection;
use Espo\Modules\Itvolga\Tools\Telephony\AmiError;
use Espo\Modules\Itvolga\Tools\Telephony\Core\Ami\Message;
use Espo\Modules\Itvolga\Tools\Telephony\Core\TrackerSettings;
use Espo\Modules\Itvolga\Tools\Telephony\TelephonyConfig;
use InvalidArgumentException;
use JsonException;

/**
 * `itvolga-setup-telephony` (stage 07.1, D-169) — the settings of the Asterisk integration from a JSON object on
 * stdin, never from argv: {enabled, ami: {address, listener: {username, secret}, dialer: {…}}, rules: {…},
 * recordings: {root, asteriskDir}, fallbackExtension | fallbackExtensionIfMissing}. `{"enabled": false}` alone
 * switches the integration off (the
 * phone links dial as usual, no cards). Every value is checked before anything is written; the output names keys,
 * never values.
 *
 * `--check`: the AMI rights self-test of the configured users — the listener may list channels and may not
 * originate, the dialer may neither run CLI commands nor hang up calls. Prints codes only.
 */
class SetupTelephony implements Command
{
    private const MAX_INPUT = 65536;
    private const USER = '/^[A-Za-z0-9_.-]{1,40}$/';
    private const KEY_CHARACTERS = '/^[\x21-\x7e]{16,200}$/';
    private const PATH = '~^/[A-Za-z0-9_./-]{1,200}$~';

    public function __construct(
        private ConfigWriter $configWriter,
        private TelephonyConfig $config,
    ) {}

    public function run(Params $params, IO $io): void
    {
        if ($params->hasFlag('check')) {
            $this->check($io);

            return;
        }

        $raw = stream_get_contents(fopen('php://stdin', 'rb') ?: STDIN, self::MAX_INPUT + 1);

        try {
            if (!is_string($raw) || strlen($raw) > self::MAX_INPUT) {
                throw new InvalidArgumentException('input');
            }

            $values = $this->validate((array) json_decode($raw, true, 8, JSON_THROW_ON_ERROR));
        } catch (InvalidArgumentException | JsonException $e) {
            $io->writeErrorLine('itvolga-setup-telephony: invalid ' .
                ($e instanceof InvalidArgumentException ? $e->getMessage() : 'json'));
            $io->setExitStatus(1);

            return;
        }

        foreach ($values as $key => $value) {
            $this->configWriter->set($key, $value);
        }

        $this->configWriter->save();
        $io->writeLine('telephony settings saved: ' . implode(', ', array_keys($values)));
    }

    /**
     * @param array<string, mixed> $input
     * @return array<string, mixed>
     * @throws InvalidArgumentException
     */
    private function validate(array $input): array
    {
        $unknown = array_diff(array_keys($input),
            ['enabled', 'ami', 'rules', 'recordings', 'fallbackExtension', 'fallbackExtensionIfMissing']);

        if ($unknown !== [] || !is_bool($input['enabled'] ?? null)) {
            throw new InvalidArgumentException('keys');
        }

        $values = ['itvolgaTelephonyEnabled' => $input['enabled']];

        if (!$input['enabled'] && count($input) === 1) {
            return $values;
        }

        $ami = $input['ami'] ?? null;

        if (!is_array($ami) || !is_string($ami['address'] ?? null) || !TelephonyConfig::isLocalAddress($ami['address'])) {
            throw new InvalidArgumentException('ami.address');
        }

        $amiValue = ['address' => $ami['address']];

        foreach (['listener', 'dialer'] as $role) {
            $item = $ami[$role] ?? null;

            if (!is_array($item) || !is_string($item['username'] ?? null) || !preg_match(self::USER, $item['username'])
                || !is_string($item['secret'] ?? null) || !preg_match(self::KEY_CHARACTERS, $item['secret'])) {
                throw new InvalidArgumentException("ami.$role");
            }

            $amiValue[$role] = ['username' => $item['username'], 'secret' => $item['secret']];
        }

        $rules = $input['rules'] ?? [];

        if (!is_array($rules)) {
            throw new InvalidArgumentException('rules');
        }

        TrackerSettings::fromArray($rules);

        if (isset($rules['dialContext']) && (!is_string($rules['dialContext'])
                || !preg_match('/^[A-Za-z0-9_.-]{1,80}$/', $rules['dialContext']))) {
            throw new InvalidArgumentException('rules.dialContext');
        }

        if (isset($rules['originateTimeout']) && (!is_int($rules['originateTimeout'])
                || $rules['originateTimeout'] < 5000 || $rules['originateTimeout'] > 120000)) {
            throw new InvalidArgumentException('rules.originateTimeout');
        }

        if (isset($rules['callerIdTemplate']) && (!is_string($rules['callerIdTemplate'])
                || !preg_match('/^[^\r\n\0]{1,80}$/', $rules['callerIdTemplate'])
                || !str_contains($rules['callerIdTemplate'], '{ext}'))) {
            throw new InvalidArgumentException('rules.callerIdTemplate');
        }

        $recordings = $input['recordings'] ?? null;

        if (!is_array($recordings) || !is_string($recordings['root'] ?? null) || !preg_match(self::PATH, $recordings['root'])
            || str_contains($recordings['root'], '..')
            || (isset($recordings['asteriskDir']) && (!is_string($recordings['asteriskDir'])
                || !preg_match(self::PATH, $recordings['asteriskDir'])))) {
            throw new InvalidArgumentException('recordings');
        }

        $values['itvolgaTelephonyAmi'] = $amiValue;
        $values['itvolgaTelephonyRules'] = $rules;
        $values['itvolgaTelephonyRecordings'] = [
            'root' => rtrim($recordings['root'], '/'),
            'asteriskDir' => rtrim($recordings['asteriskDir'] ?? TelephonyConfig::DEFAULT_MONITOR_DIR, '/'),
        ];

        foreach (['fallbackExtension', 'fallbackExtensionIfMissing'] as $key) {
            if (!array_key_exists($key, $input)) {
                continue;
            }

            if (!is_string($input[$key]) || !preg_match('/^[0-9]{2,10}$/', $input[$key])) {
                throw new InvalidArgumentException($key);
            }

            // IfMissing: the stand's default never overwrites what the administrator chose (or a restored value).
            if ($key === 'fallbackExtension' || (string) $this->config->fallbackExtensionSetting() === '') {
                $values['itvolgaTelephonyFallbackExtension'] = $input[$key];
            }
        }

        return $values;
    }

    private function check(IO $io): void
    {
        $address = $this->config->amiAddress();
        $listener = $this->config->credentials('listener');
        $dialer = $this->config->credentials('dialer');

        if ($address === null || $listener === null || $dialer === null) {
            $io->writeLine('not_configured');
            $io->setExitStatus(1);

            return;
        }

        $results = [];

        try {
            $ami = AmiConnection::open($address, $listener, false);
            $results['listener.login'] = 'ok';
            $ami->requestList('CoreShowChannels', 'CoreShowChannel', 'CoreShowChannelsComplete', 10.0);
            $results['listener.CoreShowChannels'] = 'ok';
            $results['listener.Originate'] = self::outcome($ami->request('Originate', [
                'Channel' => 'Local/itvolga-check@itvolga-check', 'Application' => 'Wait', 'Data' => '1',
            ], 5.0));
            $ami->close();
        } catch (AmiError $e) {
            $results['listener'] = $e->reason;
        }

        try {
            $ami = AmiConnection::open($address, $dialer, false);
            $results['dialer.login'] = 'ok';
            $results['dialer.Command'] = self::outcome(
                $ami->request('Command', ['Command' => 'core show version'], 5.0)
            );
            $results['dialer.Hangup'] = self::outcome(
                $ami->request('Hangup', ['Channel' => 'PJSIP/itvolga-check-00000000'], 5.0)
            );
            $results['dialer.CoreShowChannels'] = self::outcome(
                $ami->request('CoreShowChannels', [], 5.0)
            );
            $ami->close();
        } catch (AmiError $e) {
            $results['dialer'] = $e->reason;
        }

        $expected = [
            'listener.login' => 'ok', 'listener.CoreShowChannels' => 'ok', 'listener.Originate' => 'denied',
            'dialer.login' => 'ok', 'dialer.Command' => 'denied', 'dialer.Hangup' => 'denied',
            'dialer.CoreShowChannels' => 'denied',
        ];

        foreach ($results as $key => $value) {
            $io->writeLine("$key: $value");
        }

        $io->setExitStatus($results === $expected ? 0 : 1);
    }

    /**
     * Success → allowed; «Permission denied» or the refused Originate application → denied; any other error → error
     * (an allowed action that failed for another reason must not pass as denied).
     */
    private static function outcome(Message $response): string
    {
        if (strcasecmp((string) $response->response(), 'Success') === 0) {
            return 'allowed';
        }

        $message = (string) $response->get('Message');

        return str_contains($message, 'Permission denied') || str_contains($message, 'Access Forbidden')
            ? 'denied' : 'error';
    }
}
