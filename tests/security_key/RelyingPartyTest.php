<?php

declare(strict_types=1);

namespace Itvolga\Tests\SecurityKey;

use Espo\Modules\Itvolga\Tools\SecurityKey\Core\RelyingParty;
use InvalidArgumentException;

final class RelyingPartyTest extends SecurityKeyTestCase
{
    public function testOriginAndIdFromTheSiteUrl(): void
    {
        $cases = [
            'http://crm.itvolga.test' => ['crm.itvolga.test', 'http://crm.itvolga.test'],
            'http://crm.itvolga.test/' => ['crm.itvolga.test', 'http://crm.itvolga.test'],
            'https://CRM.Example.test/espo/' => ['crm.example.test', 'https://crm.example.test'],
            'https://crm.example.test:443' => ['crm.example.test', 'https://crm.example.test'],
            'http://crm.example.test:80/' => ['crm.example.test', 'http://crm.example.test'],
            'https://crm.example.test:8443' => ['crm.example.test', 'https://crm.example.test:8443'],
            ' https://localhost:8080 ' => ['localhost', 'https://localhost:8080'],
        ];

        foreach ($cases as $siteUrl => [$id, $origin]) {
            $rp = RelyingParty::fromSiteUrl($siteUrl, null, 'CRM');
            $this->assertSame($id, $rp->id, $siteUrl);
            $this->assertSame($origin, $rp->origin, $siteUrl);
            $this->assertSame(hash('sha256', $id, true), $rp->idHash());
        }

        $this->assertSame('crm.example.test', RelyingParty::fromSiteUrl('https://crm.example.test', null, ' ')->name);
    }

    public function testParentDomainOverride(): void
    {
        $this->assertSame('example.test', RelyingParty::fromSiteUrl('https://crm.example.test', 'Example.test', 'CRM')->id);
        $this->assertSame('crm.example.test', RelyingParty::fromSiteUrl('https://crm.example.test', '', 'CRM')->id);

        foreach (['evil.test', 'xample.test', 'sub.crm.example.test', '127.0.0.1'] as $override) {
            $this->assertThrows(
                InvalidArgumentException::class,
                fn () => RelyingParty::fromSiteUrl('https://crm.example.test', $override, 'CRM'),
            );
        }
    }

    public function testRefusesUrlsWebAuthnCannotUse(): void
    {
        foreach ([
            '',
            'crm.example.test',
            'ftp://crm.example.test',
            'https://127.0.0.1',
            'https://[::1]:8443',
            // Credentials in the URL (built from parts: the literal would look like an e-mail address).
            'https://u:p' . '@' . 'crm.example.test',
            'https://crm_example.test',
        ] as $siteUrl) {
            $this->assertThrows(InvalidArgumentException::class, fn () => RelyingParty::fromSiteUrl($siteUrl, null, 'CRM'));
        }
    }
}
