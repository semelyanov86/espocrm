<?php

declare(strict_types=1);

// Standalone autoloading of the pure security-key core (D-128); the test helpers (TestCase, AssertionFailed, Skipped)
// are the finance ones. No EspoCRM core or container is loaded.

if (PHP_VERSION_ID < 80300 || PHP_INT_SIZE < 8 || !extension_loaded('openssl') || !extension_loaded('sodium')) {
    fwrite(STDERR, "The security-key core needs 64-bit PHP >= 8.3 with openssl and sodium (found " . PHP_VERSION . ").\n");
    exit(2);
}

define('ITVOLGA_REPO', dirname(__DIR__, 2));

spl_autoload_register(static function (string $class): void {
    $roots = [
        'Espo\\Modules\\Itvolga\\Tools\\SecurityKey\\Core\\' => ITVOLGA_REPO . '/custom/Espo/Modules/Itvolga/Tools/SecurityKey/Core/',
        'Itvolga\\Tests\\SecurityKey\\' => __DIR__ . '/',
        'Itvolga\\Tests\\Finance\\' => ITVOLGA_REPO . '/tests/finance/',
    ];

    foreach ($roots as $prefix => $dir) {
        if (str_starts_with($class, $prefix)) {
            $file = $dir . str_replace('\\', '/', substr($class, strlen($prefix))) . '.php';

            if (is_file($file)) {
                require $file;
            }

            return;
        }
    }
});
