#!/usr/bin/env bash
# Local backup of the stand into $BACKUP_DIR/<timestamp>[-label]/ (private directory, mode 700):
#   db.sql.gz        mysqldump of $DB_NAME (InnoDB snapshot, --single-transaction)
#   files.tar.gz     data/ (without cache/ and tmp/), custom/Espo/{Custom,Modules}, client/custom
#   table-counts.tsv exact row count of every table (restore verification)
#   MANIFEST         versions, git HEAD, schema charset; SHA256SUMS over all of the above
#
#   scripts/stand/backup.sh [--label NAME] [--online]
# By default cron and PHP-FPM are paused for the (sub-second) duration, so the dump, the row counts
# and the files describe one state. --online keeps them running: the dump is still a consistent
# snapshot, but row counts may differ from it (recorded as counts_exact=0; restore then only warns).
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

label="" quiesce=1
while [[ $# -gt 0 ]]; do
    case "$1" in
        --label) label="${2:?}"; shift 2 ;;
        --online) quiesce=0; shift ;;
        --quiesce) quiesce=1; shift ;;  # the default; kept for compatibility
        *) die "usage: backup.sh [--label NAME] [--online]" ;;
    esac
done
[[ $EUID -ne 0 ]] || die "run as the developer user, not root"
[[ -z "$label" || "$label" =~ ^[a-z0-9-]+$ ]] || die "label: lowercase letters, digits and '-' only"
unit_active "$MYSQL_UNIT" || die "$MYSQL_UNIT is not running"

umask 077
install -d -m 0700 "$BACKUP_DIR"
name="$(date +%Y%m%dT%H%M%S)${label:+-$label}"
dir="$BACKUP_DIR/$name"
mkdir -m 0700 "$dir"

on_exit() {
    local rc=$?
    resume_writers
    if [[ $rc -ne 0 ]]; then rm -rf "$dir"; warn "backup failed; incomplete $dir removed"; fi
}
trap on_exit EXIT
if [[ $quiesce == 1 ]]; then
    log "pausing writers (cron, $FPM_UNIT)"
    pause_writers
fi

log "dumping database $DB_NAME"
as_root "$MYSQL_HOME/bin/mysqldump" --defaults-file="$ETC_DIR/my.cnf" -uroot \
    --single-transaction --quick --routines --triggers --events --hex-blob --no-tablespaces \
    --set-gtid-purged=OFF --default-character-set=utf8mb4 "$DB_NAME" | gzip -6 >"$dir/db.sql.gz"
table_counts >"$dir/table-counts.tsv"

log "archiving data/ and customizations"
as_root tar -C "$ESPO_ROOT" --exclude=data/cache --exclude=data/tmp -czf - \
    data custom/Espo/Custom custom/Espo/Modules client/custom >"$dir/files.tar.gz"

resume_writers

IFS=$'\t' read -r db_cs db_coll < <(mysql_root -N -B -e "SELECT default_character_set_name,
    default_collation_name FROM information_schema.schemata WHERE schema_name='$DB_NAME'")
{
    echo "name=$name"
    echo "created=$(date -Is)"
    echo "quiesced=$quiesce"
    echo "counts_exact=$quiesce"
    echo "espocrm_version=$(espo_cmd version)"
    echo "mysql_version=$(mysql_root -N -B -e 'SELECT @@version')"
    echo "db_name=$DB_NAME"
    echo "db_charset=$db_cs"
    echo "db_collation=$db_coll"
    echo "tables=$(wc -l <"$dir/table-counts.tsv")"
    echo "rows_total=$(awk '{s+=$2} END{print s+0}' "$dir/table-counts.tsv")"
    echo "files_in_archive=$(tar -tzf "$dir/files.tar.gz" | grep -vc '/$')"
    echo "git_head=$(git -C "$REPO_ROOT" rev-parse HEAD)"
    echo "git_custom_dirty=$(git -C "$REPO_ROOT" status --porcelain -- custom client/custom | wc -l)"
} >"$dir/MANIFEST"
gzip -t "$dir/db.sql.gz"
tar -tzf "$dir/files.tar.gz" >/dev/null
( cd "$dir" && sha256sum db.sql.gz files.tar.gz table-counts.tsv MANIFEST >SHA256SUMS )
trap - EXIT

log "backup ready: $dir ($(du -sh "$dir" | cut -f1))"
printf '%s\n' "$dir"
