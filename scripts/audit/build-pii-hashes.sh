#!/usr/bin/env bash
# Build the private sha256 list of real personal/secret CRM values for scripts/check_secrets.py.
# Values are read and hashed ON the source host; only hashes are transferred.
#   scripts/audit/build-pii-hashes.sh   -> $AUDIT_PRIVATE_ROOT/../pii-hashes.txt (mode 600)
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "$HERE/lib.sh"
DEST="${PII_HASHES:-$(dirname "$AUDIT_PRIVATE_ROOT")/pii-hashes.txt}"
tmp="/tmp/espo_audit_$$_pii.py"
scp -q "${AUDIT_SSH_OPTS[@]}" "$HERE/remote/pii_hashes.py" "$AUDIT_HOST:$tmp"
{ echo "SET SESSION TRANSACTION READ ONLY;"; cat "$HERE/sql/50_pii_hash_input.sql"; } \
    | ssh "${AUDIT_SSH_OPTS[@]}" "$AUDIT_HOST" "sudo -n mysql --batch --default-character-set=utf8mb4 $AUDIT_DB | python3 $tmp; rm -f $tmp" > "$DEST.tmp"
mv "$DEST.tmp" "$DEST"
chmod 600 "$DEST"
echo "hashes: $(wc -l < "$DEST") -> $DEST"
