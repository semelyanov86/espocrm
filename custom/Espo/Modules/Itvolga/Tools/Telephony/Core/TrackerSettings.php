<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Telephony\Core;

use InvalidArgumentException;

/**
 * What the listener needs to know about the PBX to classify calls (D-166). Endpoints are classified by name, never by
 * the dialplan context of a channel: a trunk channel created for an outgoing call is in the trunk's inbound context
 * too. Defaults describe the production PBX (read-only check 2026-10-13): desk phones `_[12][01]X`, trunks to the
 * providers, the German trainer's trunk ignored, inbound context `call-in`.
 */
final class TrackerSettings
{
    public const INBOUND = 'inbound';
    public const IGNORED = 'ignored';

    public const DEFAULTS = [
        'extensionPattern' => '^[12][01][0-9]$',
        'trunks' => ['trunk-russia' => self::INBOUND, 'trunk-megafon' => self::INBOUND, 'trunk-easybell' => self::IGNORED],
        'inboundContexts' => ['call-in'],
        'originatePrefix' => 'crm-',
        'localAreaCode' => '8352',
    ];

    private const NAME = '/^[A-Za-z0-9_.+-]{1,80}$/';

    /**
     * @param array<string, string> $trunks endpoint name => INBOUND | IGNORED
     * @param list<string> $inboundContexts
     */
    private function __construct(
        public readonly string $extensionPattern,
        public readonly array $trunks,
        public readonly array $inboundContexts,
        public readonly string $originatePrefix,
        public readonly string $localAreaCode,
    ) {}

    /**
     * @param array<string, mixed> $data missing keys take the defaults
     * @throws InvalidArgumentException
     */
    public static function fromArray(array $data): self
    {
        $data += self::DEFAULTS;
        $pattern = $data['extensionPattern'];
        $trunks = $data['trunks'];
        $contexts = $data['inboundContexts'];

        if (!is_string($pattern) || $pattern === '' || str_contains($pattern, '~') || !self::compiles($pattern)) {
            throw new InvalidArgumentException('extensionPattern');
        }

        if (!is_array($trunks) || $trunks === []) {
            throw new InvalidArgumentException('trunks');
        }

        foreach ($trunks as $name => $class) {
            if (!is_string($name) || !preg_match(self::NAME, $name) || !in_array($class, [self::INBOUND, self::IGNORED], true)) {
                throw new InvalidArgumentException('trunks');
            }
        }

        if (!is_array($contexts) || $contexts === [] || !array_is_list($contexts)) {
            throw new InvalidArgumentException('inboundContexts');
        }

        foreach ($contexts as $context) {
            if (!is_string($context) || !preg_match(self::NAME, $context)) {
                throw new InvalidArgumentException('inboundContexts');
            }
        }

        if (!is_string($data['originatePrefix']) || !preg_match('/^[a-z]{1,10}-$/', $data['originatePrefix'])) {
            throw new InvalidArgumentException('originatePrefix');
        }

        if (!is_string($data['localAreaCode']) || !preg_match('/^[0-9]{0,6}$/', $data['localAreaCode'])) {
            throw new InvalidArgumentException('localAreaCode');
        }

        return new self($pattern, $trunks, $contexts, $data['originatePrefix'], $data['localAreaCode']);
    }

    private static function compiles(string $pattern): bool
    {
        set_error_handler(static fn () => true);

        try {
            return preg_match('~' . $pattern . '~', '') !== false;
        } finally {
            restore_error_handler();
        }
    }

    /**
     * The PJSIP endpoint of a channel name (`PJSIP/<endpoint>-<8 hex>`); null for any other technology.
     */
    public function endpointOf(?string $channel): ?string
    {
        if ($channel === null || !preg_match('~^PJSIP/(.+)-[0-9a-f]{8}$~', $channel, $m)) {
            return null;
        }

        return $m[1];
    }

    public function isExtension(?string $endpoint): bool
    {
        return $endpoint !== null && preg_match('~' . $this->extensionPattern . '~', $endpoint) === 1;
    }

    public function trunkClass(?string $endpoint): ?string
    {
        return $endpoint !== null ? ($this->trunks[$endpoint] ?? null) : null;
    }

    public function isTrunk(?string $endpoint): bool
    {
        return $this->trunkClass($endpoint) !== null;
    }

    /**
     * A trunk whose calls are CRM calls (class INBOUND); an IGNORED trunk (the German trainer) never makes one, in
     * either direction.
     */
    public function isCrmTrunk(?string $endpoint): bool
    {
        return $this->trunkClass($endpoint) === self::INBOUND;
    }

    public function isInboundContext(?string $context): bool
    {
        return $context !== null && in_array($context, $this->inboundContexts, true);
    }
}
