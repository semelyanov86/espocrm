# shellcheck shell=bash
# Shared helpers of the EspoCRM maintenance tools on the server (role espocrm, stage 09; port of scripts/stand/lib.sh).
# Sourced by /usr/local/sbin/espocrm-*; every tool runs as root. Paths and names come from /etc/espocrm/espocrm.env
# (rendered by Ansible, no secrets). Secrets are never put into argv: they stay in the EspoCRM configuration and in
# /root/.my.cnf (MySQL root, role mysql).
set -euo pipefail

ESPOCRM_ENV="${ESPOCRM_ENV:-/etc/espocrm/espocrm.env}"
[[ -r "$ESPOCRM_ENV" ]] || { echo "espocrm: $ESPOCRM_ENV is missing (deploy the role espocrm)" >&2; exit 1; }
set -a
# shellcheck source=/dev/null
source "$ESPOCRM_ENV"
set +a

TOOL="$(basename "$0")"
log()  { printf '[%s] %s\n' "$TOOL" "$*" >&2; }
warn() { printf '[%s] WARNING: %s\n' "$TOOL" "$*" >&2; }
die()  { printf '[%s] ERROR: %s\n' "$TOOL" "$*" >&2; exit 1; }

require_root() { [[ $EUID -eq 0 ]] || die "run as root (sudo $TOOL …)"; }

# PHP as the EspoCRM user with the pinned PHP version and a clean environment (D-35: `php` in PATH is the shim).
# umask 0007: no access for others, like data/ itself (0770).
espo_php() {
    ( umask 0007; /usr/sbin/runuser -u "$ESPO_USER" -- env -i PATH="$ESPO_PATH" HOME=/nonexistent LANG=C.UTF-8 \
        "$PHP_BIN" "$@" )
}

# EspoCRM console (bin/command) — never bin/command directly: its `#!/usr/bin/env php` may pick another PHP and the
# files it creates would belong to root.
espo_cmd() { ( cd "$ESPO_ROOT" && espo_php "$ESPO_ROOT/command.php" "$@" ); }

# Configuration helper (values on stdin / stdout, never in argv): espo_config set < json | espo_config get name...
espo_config() { espo_php "$LIB_DIR/config.php" "$ESPO_ROOT" "$@"; }

# MySQL as root through the unix socket (/root/.my.cnf of the role mysql).
mysql_root() { mysql --default-character-set=utf8mb4 "$@"; }

# One maintenance operation at a time (backup, restore, restore check); Ansible checks the same lock.
ops_lock() {
    exec 9>"$OPS_LOCK"
    flock -n 9 || die "another EspoCRM backup/restore is running (lock $OPS_LOCK)"
}

unit_active() { systemctl is-active --quiet "$1"; }

# Exact row count of every base table: "<table>\t<count>", sorted (the same format as the stand, restore checks it).
table_counts() { # [db]
    local db="${1:-$DB_NAME}" sql
    sql="$(mysql_root -N -B -e "SET SESSION group_concat_max_len = 1048576; SELECT GROUP_CONCAT(CONCAT('SELECT ''',
            table_name, ''', COUNT(*) FROM \`', table_name, '\`') ORDER BY table_name SEPARATOR ' UNION ALL ')
            FROM information_schema.tables WHERE table_schema='$db' AND table_type='BASE TABLE'" 2>/dev/null)"
    [[ -n "$sql" && "$sql" != NULL ]] || return 1
    mysql_root -N -B "$db" <<<"$sql;" | sort
}

# Move every base table of database FROM into database TO with one atomic RENAME TABLE.
move_tables() { # from to
    local sql
    sql="$(mysql_root -N -B -e "SET SESSION group_concat_max_len = 1048576; SELECT CONCAT('RENAME TABLE ',
            GROUP_CONCAT(CONCAT('\`$1\`.\`', table_name, '\` TO \`$2\`.\`', table_name, '\`') ORDER BY table_name
            SEPARATOR ', ')) FROM information_schema.tables WHERE table_schema='$1' AND table_type='BASE TABLE'")"
    [[ -n "$sql" && "$sql" != NULL ]] || die "no tables in $1"
    mysql_root <<<"$sql;"
}

# Objects RENAME TABLE cannot move between databases (EspoCRM creates none of them).
db_extra_objects() { # db
    mysql_root -N -B -e "SELECT (SELECT COUNT(*) FROM information_schema.views WHERE table_schema='$1')
        + (SELECT COUNT(*) FROM information_schema.triggers WHERE trigger_schema='$1')
        + (SELECT COUNT(*) FROM information_schema.routines WHERE routine_schema='$1')
        + (SELECT COUNT(*) FROM information_schema.events WHERE event_schema='$1')"
}

manifest_get() { sed -n "s/^$2=//p" "$1/MANIFEST"; } # bundle key

# The dump and the archive of a bundle: gzip (default, the stand format) or plain (nightly, restic deduplicates it).
bundle_db()    { if [[ -f "$1/db.sql.gz" ]]; then echo "$1/db.sql.gz"; else echo "$1/db.sql"; fi; }
bundle_files() { if [[ -f "$1/files.tar.gz" ]]; then echo "$1/files.tar.gz"; else echo "$1/files.tar"; fi; }
bundle_cat_db() { local f; f="$(bundle_db "$1")"; if [[ "$f" == *.gz ]]; then gunzip -c "$f"; else cat "$f"; fi; }

# Verify SHA256SUMS of a bundle and that it was made by the pinned EspoCRM version.
bundle_verify() { # dir
    [[ -f "$1/MANIFEST" && -f "$1/SHA256SUMS" ]] || die "no bundle at $1 (MANIFEST, SHA256SUMS)"
    ( cd "$1" && sha256sum -c --quiet SHA256SUMS ) || die "checksum mismatch: the bundle $1 is damaged"
    local v
    v="$(manifest_get "$1" espocrm_version)"
    [[ "$v" == "$ESPO_VERSION" ]] || die "the bundle is from EspoCRM $v, the core is $ESPO_VERSION (same version only)"
    [[ "$(manifest_get "$1" db_charset)" =~ ^[a-z0-9_]+$ && "$(manifest_get "$1" db_collation)" =~ ^[a-z0-9_]+$ ]] \
        || die "bad charset in MANIFEST"
}

# Stop every writer of the EspoCRM database and files: the telephony listener, the cron entry (cron ignores file
# names with a dot), PHP-FPM; then wait until no process of the EspoCRM user is left (cron.php, parallel jobs).
# resume_writers restores exactly what pause_writers stopped.
pause_writers() {
    WRITERS_CRON=0 WRITERS_FPM=0 WRITERS_TELEPHONY=0
    if unit_active "$TELEPHONY_UNIT"; then systemctl stop "$TELEPHONY_UNIT"; WRITERS_TELEPHONY=1; fi
    if [[ -f "$CRON_FILE" ]]; then mv "$CRON_FILE" "$CRON_FILE.paused"; WRITERS_CRON=1; fi
    if unit_active "$FPM_UNIT"; then systemctl stop "$FPM_UNIT"; WRITERS_FPM=1; fi
    local i
    for i in $(seq 120); do
        pgrep -u "$ESPO_USER" >/dev/null 2>&1 || return 0
        [[ $i == 1 ]] && log "waiting for processes of $ESPO_USER (cron.php, job processes) to finish"
        sleep 1
    done
    die "processes of $ESPO_USER are still running after 120 s"
}

resume_writers() {
    if [[ "${WRITERS_FPM:-0}" == 1 ]]; then systemctl start "$FPM_UNIT"; fi
    if [[ "${WRITERS_CRON:-0}" == 1 && -f "$CRON_FILE.paused" ]]; then mv "$CRON_FILE.paused" "$CRON_FILE"; fi
    if [[ "${WRITERS_TELEPHONY:-0}" == 1 ]]; then systemctl start "$TELEPHONY_UNIT"; fi
    WRITERS_CRON=0 WRITERS_FPM=0 WRITERS_TELEPHONY=0
}

# Wait (up to 150 s) until cron.php has run at or after the epoch SINCE (default: now).
wait_cron_run() { # [since]
    local since="${1:-$(date +%s)}" f="$ESPO_ROOT/data/cache/application/cronLastRunTime.php" m
    for _ in $(seq 150); do
        m="$(stat -c %Y "$f" 2>/dev/null || echo 0)"
        if [[ $m -ge $since ]]; then sleep 10; return 0; fi
        [[ $_ == 1 ]] && log "waiting for cron.php (up to 150 s)"
        sleep 1
    done
    warn "cron.php did not run within 150 s"
    return 1
}

# Server-owned configuration: what makes this installation this server, not data. A restore keeps these values
# of the live configuration and takes everything else (cryptKey, passwordSalt, settings of the users) from the
# bundle — ContactAccess passwords are encrypted with the bundle's cryptKey (D-184). The fallback extension belongs
# to the PBX of this server (the stand's test PBX uses 119, production 108).
SERVER_CONFIG_KEYS=(database itvolgaTelephonyEnabled itvolgaTelephonyAmi itvolgaTelephonyRules
                    itvolgaTelephonyRecordings itvolgaTelephonyFallbackExtension)
