#!/usr/bin/env bash
# Local backup of the stand into $BACKUP_DIR/<timestamp>[-label]/ (private directory, mode 700):
#   db.sql.gz        mysqldump of $DB_NAME (InnoDB snapshot, --single-transaction)
#   files.tar.gz     data/ (without cache/ and tmp/), custom/Espo/{Custom,Modules}, client/custom
#   table-counts.tsv exact row count of every table at dump time (restore verification)
#   MANIFEST         versions, git HEAD, schema charset; SHA256SUMS over all of the above
#
#   scripts/stand/backup.sh [--label NAME] [--quiesce]
# --quiesce stops cron and PHP-FPM for the duration, so DB and files are taken with no writers.
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

label="" quiesce=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --label) label="${2:?}"; shift 2 ;;
        --quiesce) quiesce=1; shift ;;
        *) die "usage: backup.sh [--label NAME] [--quiesce]" ;;
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

resume() {
    if [[ -f "$CRON_FILE.backup-paused" ]]; then as_root mv "$CRON_FILE.backup-paused" "$CRON_FILE"; fi
    unit_active "$FPM_UNIT" || as_root systemctl start "$FPM_UNIT"
}
if [[ $quiesce == 1 ]]; then
    log "quiesce: pausing cron and $FPM_UNIT"
    [[ -f "$CRON_FILE" ]] && as_root mv "$CRON_FILE" "$CRON_FILE.backup-paused"
    trap resume EXIT
    for _ in $(seq 60); do pgrep -u "$ESPO_USER" -f "$ESPO_ROOT/cron.php" >/dev/null || break; sleep 1; done
    as_root systemctl stop "$FPM_UNIT"
fi

log "dumping database $DB_NAME"
as_root "$MYSQL_HOME/bin/mysqldump" --defaults-file="$ETC_DIR/my.cnf" -uroot \
    --single-transaction --quick --routines --triggers --events --hex-blob --no-tablespaces \
    --set-gtid-purged=OFF --default-character-set=utf8mb4 "$DB_NAME" | gzip -6 >"$dir/db.sql.gz"
table_counts >"$dir/table-counts.tsv"

log "archiving data/ and customizations"
as_root tar -C "$ESPO_ROOT" --exclude=data/cache --exclude=data/tmp -czf - \
    data custom/Espo/Custom custom/Espo/Modules client/custom >"$dir/files.tar.gz"

[[ $quiesce == 1 ]] && { resume; trap - EXIT; }

IFS=$'\t' read -r db_cs db_coll < <(mysql_root -N -B -e "SELECT default_character_set_name,
    default_collation_name FROM information_schema.schemata WHERE schema_name='$DB_NAME'")
{
    echo "name=$name"
    echo "created=$(date -Is)"
    echo "quiesced=$quiesce"
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

log "backup ready: $dir ($(du -sh "$dir" | cut -f1))"
printf '%s\n' "$dir"
