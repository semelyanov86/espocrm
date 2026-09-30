#!/usr/bin/env bash
# Read-only local copy of the Vtiger/SalesPlatform CODE for analysis (no data, no secrets, no closed extensions).
#
#   scripts/audit/sync-vtiger-src.sh          # refresh /data/itvolga/espo-private/vtiger-src/vtiger7/
#
# The server is only read (rsync sender side, sudo for www-data files). Excluded: storage/, test/, cache/, logs/,
# user_privileges/, packages/, config*.php with credentials, dumps/media/archives and the VTE/ITS4You and other
# ionCube-encoded modules (vtiger-src.exclude); encoded files left after the copy are deleted locally.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "$HERE/lib.sh"
SRC_ROOT="${VTIGER_SRC_ROOT:-/data/itvolga/espo-private/vtiger-src}"
REMOTE_DIR="${VTIGER_REMOTE_DIR:-/var/www/serv_itvolga/vtiger7}"
umask 077
mkdir -p "$SRC_ROOT"
chmod 700 "$SRC_ROOT"
rsync -a --delete --delete-excluded --chmod=D700,F600 --rsync-path="sudo -n rsync" -e "ssh ${AUDIT_SSH_OPTS[*]}" \
    --exclude-from="$HERE/vtiger-src.exclude" "$AUDIT_HOST:$REMOTE_DIR/" "$SRC_ROOT/vtiger7/"
encoded=0
while IFS= read -r -d '' f; do rm -f "$f"; encoded=$((encoded + 1)); done \
    < <(grep -rlZE 'ionCube Loader|<\?php //00' --include='*.php' "$SRC_ROOT/vtiger7" || true)
{
    date -Is
    ssh "${AUDIT_SSH_OPTS[@]}" "$AUDIT_HOST" "cat $REMOTE_DIR/spServicePackVersion.txt; grep -o \"vtiger_current_version = .*\" $REMOTE_DIR/vtigerversion.php" < /dev/null
} > "$SRC_ROOT/COPIED_AT.txt"
echo "copied to $SRC_ROOT/vtiger7 ($(find "$SRC_ROOT/vtiger7" -type f | wc -l) files, encoded files removed: $encoded)"
