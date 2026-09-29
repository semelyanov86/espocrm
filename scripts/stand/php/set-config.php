<?php
/**
 * Write EspoCRM config parameters from a JSON object on stdin.
 *
 * Used by scripts/stand/install.sh for values that must not appear in argv (the database
 * password): `bin/command config:set` only accepts values as arguments.
 * EspoCRM's ConfigWriter decides whether a parameter goes to data/config.php or
 * data/config-internal.php (the `database` block is internal). An object value is merged
 * into an existing associative parameter, so unrelated keys (e.g. `database.platform`) stay.
 *
 * Usage: php set-config.php <espo-root> < params.json
 */

declare(strict_types=1);

use Espo\Core\Application;
use Espo\Core\Utils\Config;
use Espo\Core\Utils\Config\ConfigWriter;

if ($argc !== 2 || !is_file($argv[1] . '/bootstrap.php')) {
    fwrite(STDERR, "usage: php set-config.php <espo-root> < params.json\n");
    exit(2);
}

$input = stream_get_contents(STDIN);

try {
    $params = json_decode((string) $input, true, 16, JSON_THROW_ON_ERROR);
} catch (JsonException $e) {
    fwrite(STDERR, "set-config.php: invalid JSON on stdin\n");
    exit(2);
}

if (!is_array($params) || $params === [] || array_is_list($params)) {
    fwrite(STDERR, "set-config.php: expected a non-empty JSON object\n");
    exit(2);
}

require $argv[1] . '/bootstrap.php';

$app = new Application();
$config = $app->getContainer()->getByClass(Config::class);
$writer = $app->getInjectableFactory()->create(ConfigWriter::class);

foreach ($params as $name => $value) {
    $current = $config->get((string) $name);

    if ($current instanceof stdClass) {
        $current = get_object_vars($current);
    }

    if (is_array($value) && !array_is_list($value) && is_array($current) && !array_is_list($current)) {
        $value = array_replace($current, $value);
    }

    $writer->set((string) $name, $value);
}

$writer->save();

fwrite(STDERR, 'set-config.php: saved ' . implode(', ', array_keys($params)) . "\n");
