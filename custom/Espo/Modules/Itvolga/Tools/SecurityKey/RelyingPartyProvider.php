<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\SecurityKey;

use Espo\Core\Authentication\TwoFactor\Exceptions\NotConfigured;
use Espo\Core\Utils\Config;
use Espo\Modules\Itvolga\Tools\SecurityKey\Core\RelyingParty;
use InvalidArgumentException;

/**
 * The relying party of this installation from the configuration (D-128): the site URL, the optional system parameter
 * `itvolgaSecurityKeyRpId` (a parent domain; not readable or writable through the API, set with `config:set`) and the
 * application name shown by the browser. A site URL WebAuthn cannot work with is a configuration error.
 */
class RelyingPartyProvider
{
    public function __construct(private Config $config) {}

    /**
     * @throws NotConfigured
     */
    public function get(): RelyingParty
    {
        $rpId = $this->config->get('itvolgaSecurityKeyRpId');

        try {
            return RelyingParty::fromSiteUrl(
                (string) $this->config->get('siteUrl'),
                is_string($rpId) ? $rpId : null,
                (string) $this->config->get('applicationName'),
            );
        } catch (InvalidArgumentException $e) {
            throw new NotConfigured('Security key: ' . $e->getMessage());
        }
    }
}
