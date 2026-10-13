<?php

declare(strict_types=1);

// Standalone autoloading of the pure telephony core (stage 07.1, D-166); the test helpers (TestCase, AssertionFailed,
// Skipped) are the finance ones. No EspoCRM core or container is loaded: a core class that imports EspoCRM fails here.

if (PHP_VERSION_ID < 80300 || PHP_INT_SIZE < 8) {
    fwrite(STDERR, "The telephony core needs 64-bit PHP >= 8.3 (found " . PHP_VERSION . ").\n");
    exit(2);
}

define('ITVOLGA_REPO', dirname(__DIR__, 2));

spl_autoload_register(static function (string $class): void {
    $roots = [
        'Espo\\Modules\\Itvolga\\Tools\\Telephony\\Core\\' => ITVOLGA_REPO . '/custom/Espo/Modules/Itvolga/Tools/Telephony/Core/',
        'Itvolga\\Tests\\Telephony\\' => __DIR__ . '/',
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
