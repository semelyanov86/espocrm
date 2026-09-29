#!/usr/bin/env bash
# Shared helpers for the read-only source audit (stage 01).
# Every remote call is read-only: SQL runs in a READ ONLY session and shell
# commands only list/stat/count. Output goes to a private directory outside Git.
set -euo pipefail

AUDIT_HOST="${AUDIT_HOST:-sergey@serv.sergeyem.ru}"
AUDIT_DB="${AUDIT_DB:-vtiger7}"
AUDIT_PRIVATE_ROOT="${AUDIT_PRIVATE_ROOT:-/data/itvolga/espo-private/audit}"
AUDIT_SSH_OPTS=(-o BatchMode=yes -o ConnectTimeout=15)
AUDIT_REMOTE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/remote"

# Run SQL from stdin against the source DB in a read-only session; prints TSV.
remote_sql() {
    local db="${1:-$AUDIT_DB}"
    { echo "SET SESSION TRANSACTION READ ONLY;"; cat; } \
        | ssh "${AUDIT_SSH_OPTS[@]}" "$AUDIT_HOST" "sudo -n mysql --batch --raw --default-character-set=utf8mb4 $db"
}

# Remote command that runs a local Python script from scripts/audit/remote/ without creating any
# file on the host: the source travels base64-encoded inside `python3 -c`.
_remote_py_cmd() { # script [args...]
    local script="$1"; shift
    local b64
    b64="$(base64 -w0 "$AUDIT_REMOTE_DIR/$script")"
    printf "sudo -n python3 -c \"import base64;exec(compile(base64.b64decode('%s'),'%s','exec'))\" %s" \
        "$b64" "$script" "$*"
}

# Pipe read-only SQL (stdin) through mysql on the host into a host-side Python script; prints its output.
remote_sql_py() { # db script [args...]  (SQL on stdin)
    local db="$1"; shift
    { echo "SET SESSION TRANSACTION READ ONLY;"; cat; } \
        | ssh "${AUDIT_SSH_OPTS[@]}" "$AUDIT_HOST" \
            "sudo -n mysql --batch --default-character-set=utf8mb4 $db | $(_remote_py_cmd "$@")"
}

# Run a host-side Python script that needs no stdin.
remote_py() { # script [args...]
    ssh "${AUDIT_SSH_OPTS[@]}" "$AUDIT_HOST" "$(_remote_py_cmd "$@")" < /dev/null
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
