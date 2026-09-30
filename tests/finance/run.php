<?php

declare(strict_types=1);

/*
 * Tests of the finance core (stage 04.1): php tests/finance/run.php [filter]
 *
 * Every *Test.php class in this directory; public methods named test*. Exit code 1 when a test fails.
 * SourceSnapshotTest needs the private numeric snapshot of the source (outside Git) and is skipped without it;
 * its output is counts and pass/fail only, never amounts.
 */

namespace Itvolga\Tests\Finance;

require __DIR__ . '/bootstrap.php';

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
            // Messages of unexpected exceptions may quote a value; tests over private data show only where it failed.
            $message = !$e instanceof AssertionFailed && defined("$class::PRIVATE_DATA") ? '(message hidden: private data)' : $e->getMessage();
            echo "  FAIL  $name — $message$where\n";
        }
    }
}

echo "---\nfinance tests: $passed passed, $failed failed, $skipped skipped\n";
// Fail on a failure or when the filter selected nothing; a run where every selected test is skipped is not a failure.
exit($failed > 0 || $passed + $skipped === 0 ? 1 : 0);
