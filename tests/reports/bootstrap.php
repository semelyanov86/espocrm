<?php

declare(strict_types=1);

// Standalone autoloading of the pure report core (stage 05.1) and of the finance Decimal it computes with; the test
// helpers (TestCase, AssertionFailed, Skipped) are the finance ones. No EspoCRM core or container is loaded.

if (PHP_VERSION_ID < 80300 || !extension_loaded('bcmath')) {
    fwrite(STDERR, "The report core needs PHP >= 8.3 with bcmath (found " . PHP_VERSION . ").\n");
    exit(2);
}

define('ITVOLGA_REPO', dirname(__DIR__, 2));

spl_autoload_register(static function (string $class): void {
    $roots = [
        'Espo\\Modules\\Itvolga\\Tools\\Report\\Core\\' => ITVOLGA_REPO . '/custom/Espo/Modules/Itvolga/Tools/Report/Core/',
        'Espo\\Modules\\Itvolga\\Tools\\Finance\\' => ITVOLGA_REPO . '/custom/Espo/Modules/Itvolga/Tools/Finance/',
        'Itvolga\\Tests\\Reports\\' => __DIR__ . '/',
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
