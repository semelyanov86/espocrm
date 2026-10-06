<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\SecurityKey\Core;

use InvalidArgumentException;

/**
 * The relying party of the CRM: its WebAuthn RP ID and the one origin the browser must report. Both come from the
 * configured site URL, never from request headers: origin = scheme://host[:port] (default ports omitted, host in
 * lower case, path dropped), RP ID = the host or, when overridden, a parent domain of it. A key is bound to the RP ID:
 * changing the domain makes every registered key unusable.
 */
final class RelyingParty
{
    private function __construct(
        public readonly string $id,
        public readonly string $origin,
        public readonly string $name,
    ) {}

    /**
     * @throws InvalidArgumentException A site URL or RP ID WebAuthn cannot work with.
     */
    public static function fromSiteUrl(string $siteUrl, ?string $rpIdOverride, string $name): self
    {
        $parts = parse_url(trim($siteUrl));
        $scheme = strtolower((string) ($parts['scheme'] ?? ''));
        $host = strtolower((string) ($parts['host'] ?? ''));
        $port = $parts['port'] ?? null;

        if (!in_array($scheme, ['http', 'https'], true) || isset($parts['user']) || isset($parts['pass'])) {
            throw new InvalidArgumentException('The site URL must be an http(s) URL without credentials.');
        }

        // WebAuthn needs a domain: an IP address is not a valid RP ID.
        if (!self::isDomain($host)) {
            throw new InvalidArgumentException('The site URL host must be a domain name.');
        }

        $defaultPort = $scheme === 'https' ? 443 : 80;
        $origin = $scheme . '://' . $host . ($port !== null && $port !== $defaultPort ? ':' . $port : '');

        $rpId = $rpIdOverride === null || trim($rpIdOverride) === '' ? $host : strtolower(trim($rpIdOverride));

        if (!self::isDomain($rpId) || ($rpId !== $host && !str_ends_with($host, '.' . $rpId))) {
            throw new InvalidArgumentException('The RP ID must be the site URL host or a parent domain of it.');
        }

        return new self($rpId, $origin, trim($name) !== '' ? trim($name) : $rpId);
    }

    public function idHash(): string
    {
        return hash('sha256', $this->id, true);
    }

    private static function isDomain(string $host): bool
    {
        return $host !== '' &&
            filter_var($host, FILTER_VALIDATE_IP) === false &&
            !str_starts_with($host, '[') &&
            filter_var($host, FILTER_VALIDATE_DOMAIN, FILTER_FLAG_HOSTNAME) !== false;
    }
}
