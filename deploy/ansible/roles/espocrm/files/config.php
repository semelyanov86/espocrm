<?php
/**
 * EspoCRM configuration helper of the role espocrm (stage 09, D-184; the server variant of
 * scripts/stand/php/set-config.php). Values never travel in argv: `bin/command config:set` only takes them as
 * arguments, and the database password must not appear there.
 *
 *   php config.php <espo-root> set  < {"name": value, …}  — writes only the parameters whose value differs and
 *                                                            prints {"changed": [names]} (names, never values);
 *                                                            null removes a parameter
 *   php config.php <espo-root> diff < {"name": value, …}  — the same comparison without writing (drift check)
 *   php config.php <espo-root> get name…                 — prints {"name": value, …} of the present parameters
 *
 * An object value is merged into the current associative parameter (database.password keeps database.platform).
 * ConfigWriter decides between data/config.php and data/config-internal.php (the database block is internal).
 * Runs as the EspoCRM user (files of data/ belong to it).
 */

declare(strict_types=1);

use Espo\Core\Application;
use Espo\Core\Utils\Config;
use Espo\Core\Utils\Config\ConfigWriter;

function fail(string $message): never
{
    fwrite(STDERR, "config.php: $message\n");
    exit(2);
}

function normalize(mixed $value): mixed
{
    if ($value instanceof stdClass) {
        $value = get_object_vars($value);
    }

    return is_array($value) ? array_map('normalize', $value) : $value;
}

$root = $argv[1] ?? '';
$mode = $argv[2] ?? '';

if (!is_file($root . '/bootstrap.php') || !in_array($mode, ['set', 'diff', 'get'], true)) {
    fail('usage: php config.php <espo-root> set|diff < params.json | get name…');
}

require $root . '/bootstrap.php';

$app = new Application();
$config = $app->getContainer()->getByClass(Config::class);
$flags = JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR;

if ($mode === 'get') {
    $out = [];

    foreach (array_slice($argv, 3) as $name) {
        if ($config->has($name)) {
            $out[$name] = normalize($config->get($name));
        }
    }

    echo json_encode((object) $out, $flags), "\n";

    exit(0);
}

try {
    $params = json_decode((string) stream_get_contents(STDIN), true, 32, JSON_THROW_ON_ERROR);
} catch (JsonException) {
    fail('invalid JSON on stdin');
}

if (!is_array($params) || $params === [] || array_is_list($params)) {
    fail('expected a non-empty JSON object');
}

$writer = $app->getInjectableFactory()->create(ConfigWriter::class);
$changed = [];

foreach ($params as $name => $value) {
    $name = (string) $name;

    if ($value === null) {
        if ($config->has($name)) {
            if ($mode === 'set') {
                $writer->remove($name);
            }

            $changed[] = $name;
        }

        continue;
    }

    $current = $config->has($name) ? normalize($config->get($name)) : null;

    if (is_array($value) && !array_is_list($value) && is_array($current) && !array_is_list($current)) {
        $value = array_replace($current, $value);
    }

    if ($current === $value) {
        continue;
    }

    if ($mode === 'set') {
        $writer->set($name, $value);
    }

    $changed[] = $name;
}

if ($changed !== [] && $mode === 'set') {
    $writer->save();
}

echo json_encode(['changed' => $changed], $flags), "\n";
