<?php

declare(strict_types=1);

/*
 * Tests of the pure telephony core (stage 07.1, D-166): php tests/telephony/run.php [filter]
 * (task test:telephony).
 *
 * Every *Test.php class in this directory; public methods named test*. Exit code 1 when a test fails or the filter
 * selects nothing. AMI transcripts are synthetic (the shapes recorded from Asterisk 22.5.2); the EspoCRM side and the
 * real PBX are covered by tests/stage07_1.
 */

namespace Itvolga\Tests\Telephony;

use Itvolga\Tests\Finance\AssertionFailed;
use Itvolga\Tests\Finance\Skipped;

require __DIR__ . '/bootstrap.php';

// A warning or notice of the code under test fails the test.
set_error_handler(static function (int $severity, string $message, string $file, int $line): bool {
    throw new \ErrorException($message, 0, $severity, $file, $line);
});

$filter = $argv[1] ?? null;
$files = glob(__DIR__ . '/*Test.php') ?: [];
sort($files);
$passed = $failed = $skipped = 0;

foreach ($files as $file) {
    $class = __NAMESPACE__ . '\\' . basename($file, '.php');

    foreach (get_class_methods($class) as $method) {
        if (!str_starts_with($method, 'test') || ($filter !== null && !str_contains("$class::$method", $filter))) {
            continue;
        }

        $name = basename($file, '.php') . "::$method";

        try {
            $case = new $class();
            $case->setUp();
            $case->$method();
            $passed++;
            echo "  ok    $name\n";
        } catch (Skipped $e) {
            $skipped++;
            echo "  skip  $name — {$e->getMessage()}\n";
        } catch (\Throwable $e) {
            $failed++;
            $where = $e instanceof AssertionFailed ? '' : ' (' . $e::class . ' at ' . basename($e->getFile()) . ':' . $e->getLine() . ')';
            echo "  FAIL  $name — {$e->getMessage()}$where\n";
        }
    }
}

echo "---\ntelephony tests: $passed passed, $failed failed, $skipped skipped\n";
exit($failed > 0 || $passed + $skipped === 0 ? 1 : 0);
