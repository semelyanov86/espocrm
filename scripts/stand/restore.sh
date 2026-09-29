#!/usr/bin/env bash
# Restore the stand from a local backup made by backup.sh.
#
#   scripts/stand/restore.sh <backup-dir|name|latest> [--yes] [--no-safety-backup] [--skip-custom]
#
# 1. verify SHA256SUMS and the EspoCRM version; take a safety backup of the current state;
# 2. pause cron and PHP-FPM and wait for job processes;
# 3. import the dump into a staging database and verify exact row counts there (strict for backups
#    taken without writers, a warning for --online ones) — a bad backup never touches the live DB;
# 4. swap: live tables -> <db>__prev_<ts>, staging tables -> <db> (atomic RENAME TABLE);
# 5. replace data/ (and, unless --skip-custom, custom/Espo/{Custom,Modules}, client/custom),
#    keeping the previous directories aside; permissions, DB credentials, rebuild, cron;
# 6. health check. Only after it passes are the previous tables and directories dropped. On any
#    failure after step 4 cron and PHP-FPM stay stopped and the rollback command is printed.
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
counts_exact="$(manifest counts_exact)"; counts_exact="${counts_exact:-$(manifest quiesced)}"
[[ "$db_cs" =~ ^[a-z0-9_]+$ && "$db_coll" =~ ^[a-z0-9_]+$ ]] || die "bad charset in MANIFEST"

custom_dirs=(custom/Espo/Custom custom/Espo/Modules client/custom)
if [[ $custom == 1 && -n "$(git -C "$REPO_ROOT" status --porcelain -- "${custom_dirs[@]}")" ]]; then
    die "uncommitted changes in ${custom_dirs[*]}: commit them or use --skip-custom"
fi

if [[ $yes != 1 ]]; then
    read -r -p "Restore $(manifest name) over the current stand (DB $DB_NAME and data/)? [y/N] " answer
    [[ "$answer" =~ ^[yY]$ ]] || die "aborted"
fi

safety_name=""
if [[ $safety == 1 ]] && unit_active "$MYSQL_UNIT" && as_root test -f "$ESPO_ROOT/data/config.php"; then
    log "safety backup of the current state"
    safety_name="$(basename "$("$STAND_DIR/backup.sh" --label pre-restore)")"
fi

ts="$(date +%Y%m%dT%H%M%S)"
aside="$STAND_PRIVATE_DIR/.restore-aside-$ts"
stage_db="${DB_NAME}__restore_$ts"
prev_db="${DB_NAME}__prev_$ts"
phase=verify finished=0

on_exit() {
    local rc=$?
    [[ $finished == 1 ]] && return 0
    if [[ $phase == verify ]]; then
        mysql_root -e "DROP DATABASE IF EXISTS \`$stage_db\`" || true
        resume_writers
        warn "restore aborted before any change (rc=$rc): the stand is unchanged and running"
        return
    fi
    pause_writers || true
    warn "restore FAILED in phase '$phase' (rc=$rc): cron and $FPM_UNIT are stopped."
    warn "Previous tables: database $prev_db; previous directories: $aside."
    if [[ -n "$safety_name" ]]; then
        warn "Roll back with: scripts/stand/restore.sh $safety_name --yes --no-safety-backup"
    else
        warn "No safety backup was taken: move the tables of $prev_db and the directories in $aside back manually."
    fi
}
trap on_exit EXIT

log "pausing writers (cron, $FPM_UNIT)"
pause_writers
unit_active "$MYSQL_UNIT" || as_root systemctl start "$MYSQL_UNIT"

log "importing the dump into staging database $stage_db ($db_cs / $db_coll)"
mysql_root -e "CREATE DATABASE \`$stage_db\` CHARACTER SET $db_cs COLLATE $db_coll"
gunzip -c "$dir/db.sql.gz" | mysql_root "$stage_db"
[[ "$(db_extra_objects "$stage_db")" == 0 ]] || die "the dump contains views/triggers/routines/events; not supported"
if diff -q <(table_counts "$stage_db") "$dir/table-counts.tsv" >/dev/null; then
    log "staging database verified: $(wc -l <"$dir/table-counts.tsv") tables, row counts identical to the backup"
elif [[ "$counts_exact" == 1 ]]; then
    diff <(table_counts "$stage_db") "$dir/table-counts.tsv" | head -20 >&2 || true
    die "row counts of the dump differ from the backup record"
else
    warn "online backup: row counts differ from the ones taken next to the dump (expected under load):"
    diff <(table_counts "$stage_db") "$dir/table-counts.tsv" | head -20 >&2 || true
fi

phase=swap
log "swapping databases (previous tables -> $prev_db)"
mysql_root -e "CREATE DATABASE \`$prev_db\`"
if [[ "$(mysql_root -N -B -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='$DB_NAME'")" != 0 ]]; then
    [[ "$(db_extra_objects "$DB_NAME")" == 0 ]] || die "$DB_NAME contains views/triggers/routines/events; not supported"
    move_tables "$DB_NAME" "$prev_db"
fi
# Recreate the (now empty) live database with the charset of the backup; grants on it are kept.
mysql_root -e "DROP DATABASE IF EXISTS \`$DB_NAME\`; CREATE DATABASE \`$DB_NAME\` CHARACTER SET $db_cs COLLATE $db_coll"
move_tables "$stage_db" "$DB_NAME"
mysql_root -e "DROP DATABASE \`$stage_db\`"

phase=files
log "restoring files (previous directories -> $aside)"
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
if [[ $custom == 1 ]]; then as_root chown -R "$DEV_USER:$DEV_USER" "${custom_dirs[@]/#/$ESPO_ROOT/}"; fi

phase=configure
log "re-applying permissions, DB credentials and cron"
"$STAND_DIR/install.sh" perms fpm espo cron   # starts PHP-FPM, writes a fresh cron entry
as_root rm -f "$CRON_FILE.paused"

phase=health
wait_cron_run || true
RESTORE_TS="$ts" "$STAND_DIR/health.sh" || die "health check failed after the restore"

finished=1
mysql_root -e "DROP DATABASE \`$prev_db\`"
as_root rm -rf "$aside"
log "restore of $(manifest name) completed; previous tables and directories removed"
