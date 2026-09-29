#!/usr/bin/env bash
# Restore the stand from a local backup made by backup.sh.
#
#   scripts/stand/restore.sh <backup-dir|name|latest> [--yes] [--no-safety-backup] [--skip-custom]
#
# Order: verify checksums -> safety backup of the current state -> stop cron and PHP-FPM ->
# recreate the database from the dump -> verify exact row counts -> replace data/ (and, unless
# --skip-custom, custom/Espo/{Custom,Modules}, client/custom) -> permissions, DB credentials,
# rebuild, cron -> health check. The replaced directories are kept aside until the restore succeeds.
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

target="" yes=0 safety=1 custom=1
while [[ $# -gt 0 ]]; do
    case "$1" in
        --yes) yes=1 ;;
        --no-safety-backup) safety=0 ;;
        --skip-custom) custom=0 ;;
        -*) die "unknown option $1" ;;
        *) target="$1" ;;
    esac
    shift
done
[[ -n "$target" ]] || die "usage: restore.sh <backup-dir|name|latest> [--yes] [--no-safety-backup] [--skip-custom]"
[[ $EUID -ne 0 ]] || die "run as the developer user, not root"

if [[ "$target" == latest ]]; then
    dir="$(newest_backup)"
elif [[ -d "$target" ]]; then
    dir="$(cd "$target" && pwd)"
else
    dir="$BACKUP_DIR/$target"
fi
[[ -n "$dir" && -f "$dir/MANIFEST" && -f "$dir/SHA256SUMS" ]] || die "no backup at '${dir:-$target}'"

log "verifying checksums of $dir"
( cd "$dir" && sha256sum -c --quiet SHA256SUMS ) || die "checksum mismatch — backup is damaged"
manifest() { sed -n "s/^$1=//p" "$dir/MANIFEST"; }
backup_version="$(manifest espocrm_version)"
[[ "$backup_version" == "$ESPO_VERSION" ]] \
    || die "backup is from EspoCRM $backup_version, core is $ESPO_VERSION (restore into the same version)"
db_cs="$(manifest db_charset)"; db_coll="$(manifest db_collation)"
[[ "$db_cs" =~ ^[a-z0-9_]+$ && "$db_coll" =~ ^[a-z0-9_]+$ ]] || die "bad charset in MANIFEST"

custom_dirs=(custom/Espo/Custom custom/Espo/Modules client/custom)
if [[ $custom == 1 && -n "$(git -C "$REPO_ROOT" status --porcelain -- "${custom_dirs[@]}")" ]]; then
    die "uncommitted changes in ${custom_dirs[*]}: commit them or use --skip-custom"
fi

if [[ $yes != 1 ]]; then
    read -r -p "Restore $(manifest name) over the current stand (DB $DB_NAME and data/)? [y/N] " answer
    [[ "$answer" =~ ^[yY]$ ]] || die "aborted"
fi

if [[ $safety == 1 ]] && unit_active "$MYSQL_UNIT" && as_root test -f "$ESPO_ROOT/data/config.php"; then
    log "safety backup of the current state"
    "$STAND_DIR/backup.sh" --label pre-restore >/dev/null
fi

ts="$(date +%Y%m%dT%H%M%S)"
aside="$STAND_PRIVATE_DIR/.restore-aside-$ts"
on_error() {
    warn "restore FAILED. Previous directories are kept in $aside; cron stays disabled."
    warn "Re-run the restore (e.g. with the pre-restore backup) or move the directories back manually."
}
trap on_error ERR

log "stopping writers (cron, $FPM_UNIT)"
as_root rm -f "$CRON_FILE"
for _ in $(seq 60); do pgrep -u "$ESPO_USER" -f "$ESPO_ROOT/cron.php" >/dev/null || break; sleep 1; done
as_root systemctl stop "$FPM_UNIT"
unit_active "$MYSQL_UNIT" || as_root systemctl start "$MYSQL_UNIT"

log "recreating database $DB_NAME ($db_cs / $db_coll)"
mysql_root -e "DROP DATABASE IF EXISTS \`$DB_NAME\`; CREATE DATABASE \`$DB_NAME\` CHARACTER SET $db_cs COLLATE $db_coll;"
gunzip -c "$dir/db.sql.gz" | mysql_root "$DB_NAME"
if ! diff -q <(table_counts) "$dir/table-counts.tsv" >/dev/null; then
    diff <(table_counts) "$dir/table-counts.tsv" | head -20 >&2
    false  # -> on_error
fi
log "database restored: $(wc -l <"$dir/table-counts.tsv") tables, row counts identical to the backup"

log "restoring files"
as_root install -d -m 0700 "$aside"
paths=(data)
[[ $custom == 1 ]] && paths+=("${custom_dirs[@]}")
for p in "${paths[@]}"; do
    if as_root test -e "$ESPO_ROOT/$p"; then
        as_root mkdir -p "$aside/$(dirname "$p")"
        as_root mv "$ESPO_ROOT/$p" "$aside/$p"
    fi
done
as_root tar -C "$ESPO_ROOT" -xzf "$dir/files.tar.gz" "${paths[@]}"
[[ $custom == 1 ]] && as_root chown -R "$DEV_USER:$DEV_USER" "${custom_dirs[@]/#/$ESPO_ROOT/}"

log "re-applying permissions, DB credentials and cron"
"$STAND_DIR/install.sh" perms fpm espo cron
trap - ERR
as_root rm -rf "$aside"

log "restore of $(manifest name) completed"
wait_cron_run || true
"$STAND_DIR/health.sh"
