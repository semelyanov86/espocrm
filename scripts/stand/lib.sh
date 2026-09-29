#!/usr/bin/env bash
# Shared helpers for the local EspoCRM stand (stage 02).
# Scripts run as the developer; privileged steps go through `sudo -n` (see docs/local-stand.md).
# Secrets are read from $STAND_PRIVATE_ENV and passed to programs via stdin, never via argv.
set -euo pipefail

STAND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$STAND_DIR/../.." && pwd)"
TEMPLATE_DIR="$REPO_ROOT/deploy/local/templates"
export REPO_ROOT

set -a
# shellcheck source=../../deploy/local/stand.conf
source "$REPO_ROOT/deploy/local/stand.conf"
set +a

# Every file rendered from deploy/local/templates carries this marker (see uninstall.sh).
STAND_MARKER="Rendered from deploy/local/templates/"

log()  { printf '[stand] %s\n' "$*" >&2; }
warn() { printf '[stand] WARNING: %s\n' "$*" >&2; }
die()  { printf '[stand] ERROR: %s\n' "$*" >&2; exit 1; }

as_root() {
    if [[ $EUID -eq 0 ]]; then "$@"; else sudo -n -- "$@"; fi
}

as_user() { # user cmd...
    local user="$1"; shift
    if [[ "$(id -un)" == "$user" ]]; then "$@"; else sudo -n -u "$user" -- "$@"; fi
}

# EspoCRM console (bin/command) under the web user and the pinned PHP version.
# bin/command itself uses `#!/usr/bin/env php`, which may resolve to another PHP version.
espo_cmd() {
    as_user "$ESPO_USER" env PATH="$STAND_PATH" "$PHP_BIN" "$ESPO_ROOT/command.php" "$@"
}

# MySQL client of the stand instance as MySQL root (auth_socket => OS root).
mysql_root() {
    as_root "$MYSQL_HOME/bin/mysql" --defaults-file="$ETC_DIR/my.cnf" -uroot "$@"
}

load_private_env() {
    [[ -f "$STAND_PRIVATE_ENV" ]] || die "no private settings $STAND_PRIVATE_ENV (run: task stand:install)"
    local mode
    mode="$(stat -c %a "$STAND_PRIVATE_ENV")"
    [[ "$mode" == 600 ]] || die "$STAND_PRIVATE_ENV must have mode 600 (has $mode)"
    # Not exported: secrets reach only the process they are handed to (stdin or an explicit
    # per-command environment), never argv or the environment of unrelated children.
    # shellcheck disable=SC1090
    source "$STAND_PRIVATE_ENV"
    local key
    for key in DB_PASSWORD ESPO_ADMIN_USERNAME ESPO_ADMIN_PASSWORD; do
        [[ -n "${!key:-}" && "${!key}" != changeme ]] || die "$key is empty in $STAND_PRIVATE_ENV"
    done
}

# Render TEMPLATE into DEST (as root) only when the content differs.
# Sets RENDER_CHANGED=1 when the file was (re)written (read by the callers in install.sh).
# shellcheck disable=SC2034
render_to() { # template dest mode [owner] [group]
    local template="$TEMPLATE_DIR/$1" dest="$2" mode="$3" owner="${4:-root}" group="${5:-root}"
    local tmp
    tmp="$(mktemp)"
    python3 "$STAND_DIR/render.py" "$template" >"$tmp" || { rm -f "$tmp"; die "cannot render $1"; }
    RENDER_CHANGED=0
    if ! as_root test -f "$dest" || ! as_root cmp -s "$tmp" "$dest"; then
        as_root install -D -m "$mode" -o "$owner" -g "$group" "$tmp" "$dest"
        RENDER_CHANGED=1
        log "wrote $dest"
    fi
    rm -f "$tmp"
}

sha256_of() { sha256sum "$1" | awk '{print $1}'; }

# Download URL into the cache (once) and verify the pinned sha256.
fetch_verified() { # url file sha256
    local url="$1" file="$CACHE_DIR/$2" sha="$3"
    mkdir -p "$CACHE_DIR"
    if [[ ! -f "$file" ]]; then
        log "downloading $url"
        curl -fsSL --retry 3 -o "$file.part" "$url"
        mv "$file.part" "$file"
    fi
    local actual
    actual="$(sha256_of "$file")"
    [[ "$actual" == "$sha" ]] || die "sha256 mismatch for $file: $actual (expected $sha)"
    printf '%s\n' "$file"
}

random_secret() { # length
    local out=""
    while [[ ${#out} -lt $1 ]]; do
        out+="$(head -c 64 /dev/urandom | base64 | tr -dc 'A-Za-z0-9')"
    done
    printf '%s' "${out:0:$1}"
}

unit_active() { systemctl is-active --quiet "$1"; }

# Exact row count of every base table of a database (default: the stand DB): "<table>\t<count>", sorted.
table_counts() { # [db]
    local db="${1:-$DB_NAME}" sql
    sql="$(mysql_root -N -B -e "SET SESSION group_concat_max_len = 1048576; SELECT GROUP_CONCAT(CONCAT('SELECT ''', table_name, ''', COUNT(*) FROM \`',
            table_name, '\`') ORDER BY table_name SEPARATOR ' UNION ALL ') FROM information_schema.tables
            WHERE table_schema='$db' AND table_type='BASE TABLE'" 2>/dev/null)"
    [[ -n "$sql" && "$sql" != NULL ]] || return 1
    mysql_root -N -B "$db" <<<"$sql;" | sort
}

# Move every base table of database FROM into database TO with one atomic RENAME TABLE.
move_tables() { # from to
    local sql
    sql="$(mysql_root -N -B -e "SET SESSION group_concat_max_len = 1048576; SELECT CONCAT('RENAME TABLE ',
            GROUP_CONCAT(CONCAT('\`$1\`.\`', table_name, '\` TO \`$2\`.\`', table_name, '\`') ORDER BY table_name SEPARATOR ', '))
            FROM information_schema.tables WHERE table_schema='$1' AND table_type='BASE TABLE'")"
    [[ -n "$sql" && "$sql" != NULL ]] || die "no tables in $1"
    mysql_root <<<"$sql;"
}

# Objects that RENAME TABLE cannot move between databases (EspoCRM creates none of them).
db_extra_objects() { # db
    mysql_root -N -B -e "SELECT (SELECT COUNT(*) FROM information_schema.views WHERE table_schema='$1')
        + (SELECT COUNT(*) FROM information_schema.triggers WHERE trigger_schema='$1')
        + (SELECT COUNT(*) FROM information_schema.routines WHERE routine_schema='$1')
        + (SELECT COUNT(*) FROM information_schema.events WHERE event_schema='$1')"
}

newest_backup() {
    find "$BACKUP_DIR" -mindepth 2 -maxdepth 2 -name MANIFEST -printf '%T@ %h\n' 2>/dev/null \
        | sort -n | tail -n1 | cut -d' ' -f2-
}

# Wait (up to 150 s) until cron.php has run at or after the epoch SINCE (default: now),
# then give parallel job processes a few seconds to finish.
wait_cron_run() { # [since]
    local since="${1:-$(date +%s)}" f="$ESPO_ROOT/data/cache/application/cronLastRunTime.php" m
    for _ in $(seq 150); do
        m="$(as_root stat -c %Y "$f" 2>/dev/null || echo 0)"
        if [[ $m -ge $since ]]; then sleep 10; return 0; fi
        [[ $_ == 1 ]] && log "waiting for cron.php (up to 150 s)"
        sleep 1
    done
    warn "cron.php did not run within 150 s"
    return 1
}

# Stop every writer of the stand DB and files: the cron entry is parked (cron ignores file names
# with a dot), PHP-FPM is stopped, then we wait until no process of $ESPO_USER is left (cron.php and
# its parallel job processes). resume_writers restores exactly what pause_writers stopped.
pause_writers() {
    WRITERS_CRON=0 WRITERS_FPM=0
    if as_root grep -qsF "$STAND_MARKER" "$CRON_FILE"; then
        as_root mv "$CRON_FILE" "$CRON_FILE.paused"; WRITERS_CRON=1
    fi
    if unit_active "$FPM_UNIT"; then
        as_root systemctl stop "$FPM_UNIT"; WRITERS_FPM=1
    fi
    local i
    for i in $(seq 120); do
        pgrep -u "$ESPO_USER" >/dev/null 2>&1 || return 0
        [[ $i == 1 ]] && log "waiting for processes of $ESPO_USER (cron.php, job processes) to finish"
        sleep 1
    done
    die "processes of $ESPO_USER are still running after 120 s"
}

resume_writers() {
    if [[ "${WRITERS_FPM:-0}" == 1 ]]; then as_root systemctl start "$FPM_UNIT"; fi
    if [[ "${WRITERS_CRON:-0}" == 1 ]] && as_root test -f "$CRON_FILE.paused"; then
        as_root mv "$CRON_FILE.paused" "$CRON_FILE"
    fi
    WRITERS_CRON=0 WRITERS_FPM=0
}
