#!/usr/bin/env bash
# Build the private sha256 list of real personal/secret CRM values for scripts/check_secrets.py.
# Values are read and hashed ON the source host; only hashes are transferred.
#   scripts/audit/build-pii-hashes.sh   -> $AUDIT_PRIVATE_ROOT/../pii-hashes.txt (mode 600)
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "$HERE/lib.sh"
DEST="${PII_HASHES:-$(dirname "$AUDIT_PRIVATE_ROOT")/pii-hashes.txt}"
remote_sql_py "$AUDIT_DB" pii_hashes.py < "$HERE/sql/50_pii_hash_input.sql" > "$DEST.tmp"
mv "$DEST.tmp" "$DEST"
chmod 600 "$DEST"
echo "hashes: $(wc -l < "$DEST") -> $DEST"
