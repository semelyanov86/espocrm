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
# Second line of defence: nothing that looks like a secret or data may be left in the copy.
leftovers="$(find "$SRC_ROOT/vtiger7" \( -name .git -o -name '.env*' -o -name '*.key' -o -name '*.pem' -o -name '*.p12' \
    -o -name '*.pfx' -o -name '*.kdbx' -o -name 'id_rsa*' -o -name 'id_ed25519*' -o -name '.htpasswd*' -o -name '*.sql' \
    -o -name '*.csv' -o -name '*.wav' -o -name 'config.inc.php*' -o -path '*/storage/*' -o -path '*/user_privileges/*' \) -print | wc -l)"
if [ "$leftovers" != 0 ]; then
    echo "copy contains $leftovers secret-like or data files: check vtiger-src.exclude" >&2
    exit 1
fi
{
    date -Is
    ssh "${AUDIT_SSH_OPTS[@]}" "$AUDIT_HOST" "cat $REMOTE_DIR/spServicePackVersion.txt; grep -o \"vtiger_current_version = .*\" $REMOTE_DIR/vtigerversion.php" < /dev/null
} > "$SRC_ROOT/COPIED_AT.txt"
echo "copied to $SRC_ROOT/vtiger7 ($(find "$SRC_ROOT/vtiger7" -type f | wc -l) files, encoded files removed: $encoded)"
