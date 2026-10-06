<?php

declare(strict_types=1);

namespace Itvolga\Tests\SecurityKey;

use Espo\Modules\Itvolga\Tools\SecurityKey\Core\VerificationFailed;
use Itvolga\Tests\Finance\AssertionFailed;
use Itvolga\Tests\Finance\TestCase;

abstract class SecurityKeyTestCase extends TestCase
{
    protected const RP_ID = 'crm.example.test';
    protected const ORIGIN = 'https://crm.example.test';

    protected function assertRefused(string $reason, callable $callback, string $message = ''): void
    {
        $e = $this->assertThrows(VerificationFailed::class, $callback);
        assert($e instanceof VerificationFailed);

        if ($e->reason !== $reason) {
            throw new AssertionFailed(trim("$message expected reason $reason, got {$e->reason}"));
        }
    }
}
