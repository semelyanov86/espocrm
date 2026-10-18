#!/usr/bin/env bash
# Syntax gate of the continuous deployment (D-194, .github/workflows/deploy.yml): `php -l` of every PHP file and
# json_decode of every JSON file of the Itvolga module — a parse error in either stops EspoCRM on the server. Needs
# the PHP of the server (8.5); CI runs it in the php:8.5-cli image, locally: scripts/deploy/lint-module.sh.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
paths=(custom/Espo/Modules/Itvolga client/custom/modules/itvolga)
fail=0

php_files="$(find "${paths[@]}" -type f -name '*.php' | wc -l)"
# exit 1 instead of the 255 of php -l: xargs goes on and reports every broken file.
# shellcheck disable=SC2016 # $1 of the inner shell
out="$(find "${paths[@]}" -type f -name '*.php' -print0 \
    | xargs -0 -n 1 -P 4 sh -c 'php -n -d display_errors=1 -l "$1" || exit 1' sh 2>&1)" || fail=1
grep -v '^No syntax errors detected in ' <<<"$out" || true

json_files="$(find "${paths[@]}" -type f -name '*.json' | wc -l)"
# shellcheck disable=SC2016 # PHP code
find "${paths[@]}" -type f -name '*.json' -print0 | xargs -0 php -n -r '
    $bad = 0;
    foreach (array_slice($argv, 1) as $file) {
        try {
            json_decode(file_get_contents($file), flags: JSON_THROW_ON_ERROR);
        } catch (JsonException $e) {
            fwrite(STDERR, "$file: {$e->getMessage()}\n");
            $bad = 1;
        }
    }
    exit($bad);' || fail=1

echo "lint-module: $php_files PHP, $json_files JSON — $([[ $fail == 0 ]] && echo OK || echo FAILED) ($(php -r 'echo PHP_VERSION;'))"
exit "$fail"
