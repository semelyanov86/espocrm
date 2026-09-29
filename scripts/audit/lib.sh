#!/usr/bin/env bash
# Shared helpers for the read-only source audit (stage 01).
# Every remote call is read-only: SQL runs in a READ ONLY session and shell
# commands only list/stat/count. Output goes to a private directory outside Git.
set -euo pipefail

AUDIT_HOST="${AUDIT_HOST:-sergey@serv.sergeyem.ru}"
AUDIT_DB="${AUDIT_DB:-vtiger7}"
AUDIT_PRIVATE_ROOT="${AUDIT_PRIVATE_ROOT:-/data/itvolga/espo-private/audit}"
AUDIT_SSH_OPTS=(-o BatchMode=yes -o ConnectTimeout=15)

# Run SQL from stdin against the source DB in a read-only session; prints TSV.
remote_sql() {
    local db="${1:-$AUDIT_DB}"
    { echo "SET SESSION TRANSACTION READ ONLY;"; cat; } \
        | ssh "${AUDIT_SSH_OPTS[@]}" "$AUDIT_HOST" "sudo -n mysql --batch --raw --default-character-set=utf8mb4 $db"
}

# Run a read-only shell snippet on the source host (listing/stat/count only).
remote_sh() {
    ssh "${AUDIT_SSH_OPTS[@]}" "$AUDIT_HOST" "bash -s" <<<"$1"
}

audit_outdir() {
    local ts="${AUDIT_TS:-$(date +%Y%m%dT%H%M%S)}"
    local dir="$AUDIT_PRIVATE_ROOT/$ts"
    mkdir -p "$dir"
    chmod 700 "$AUDIT_PRIVATE_ROOT" "$dir"
    echo "$dir"
}
