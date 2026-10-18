#!/usr/bin/env bash
# Overlay of the server Ansible (stage 09, D-180). /data/server stays read-only until stage 10 (AGENTS.md), so the
# deployment is prepared here: the role espocrm and the playbooks of deploy/ansible/ plus a patch of the shared files of
# /data/server (vars, roles apache/vtiger/backup, vault.yml.example, Taskfile) — on a clean clone of /data/server.
#
#   overlay.sh build [DIR]         clone /data/server at deploy/ansible/SERVER_BASE into DIR (build/ansible-overlay),
#                                  copy the role and the playbooks, apply deploy/ansible/server-ansible.patch; a clone
#                                  has no vault.yml and no .vault_pass (both ignored by Git there): a random
#                                  .vault_pass keeps ansible.cfg working, nothing is decrypted
#   overlay.sh patch [DIR]         regenerate the patch from the shared files of DIR (after editing them in DIR)
#   overlay.sh status              the recorded base vs the HEAD of /data/server
#   overlay.sh install --stage10   stage 10 only, with the owner's permission: copy the role and the playbooks into
#                                  /data/server and apply the patch there (clean tree at the recorded base required)
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SERVER_REPO="${SERVER_REPO:-/data/server}"
OVERLAY_SRC="$REPO/deploy/ansible"
BASE="$(tr -d '[:space:]' <"$OVERLAY_SRC/SERVER_BASE")"
PATCH="$OVERLAY_SRC/server-ansible.patch"
OWN=(ansible/roles/espocrm ansible/playbooks/11-espocrm.yml ansible/playbooks/12-crm-switch.yml)

log() { printf '[overlay] %s\n' "$*" >&2; }
die() { printf '[overlay] ERROR: %s\n' "$*" >&2; exit 1; }

copy_own() { # dest-root
    rm -rf "$1/ansible/roles/espocrm"
    cp -a "$OVERLAY_SRC/roles/espocrm" "$1/ansible/roles/espocrm"
    # bytecode left by local runs of the tools (health_http.py) is not part of the role
    find "$1/ansible/roles/espocrm" -name __pycache__ -type d -prune -exec rm -rf {} +
    cp "$OVERLAY_SRC/playbooks/11-espocrm.yml" "$OVERLAY_SRC/playbooks/12-crm-switch.yml" "$1/ansible/playbooks/"
}

build() {
    local dir="${1:-$REPO/build/ansible-overlay}"
    if [[ -e "$dir" ]]; then
        [[ -f "$dir/.git/itvolga-overlay" ]] || die "$dir exists and is not an overlay"
        rm -rf "$dir"
    fi
    mkdir -p "$(dirname "$dir")"
    git clone --quiet --no-hardlinks "$SERVER_REPO" "$dir"
    git -C "$dir" checkout --quiet --detach "$BASE"
    touch "$dir/.git/itvolga-overlay"
    copy_own "$dir"
    if [[ -s "$PATCH" ]]; then git -C "$dir" apply --index "$PATCH"; fi
    ( umask 077; head -c 48 /dev/urandom | base64 >"$dir/ansible/.vault_pass" )
    local head
    head="$(git -C "$SERVER_REPO" rev-parse HEAD)"
    [[ "$head" == "$BASE" ]] || log "WARNING: /data/server HEAD $head differs from the base $BASE of the patch"
    log "overlay ready: $dir (base ${BASE:0:12})"
    printf '%s\n' "$dir"
}

patch() {
    local dir="${1:-$REPO/build/ansible-overlay}"
    [[ -f "$dir/.git/itvolga-overlay" ]] || die "$dir is not an overlay (overlay.sh build)"
    local excludes=() p
    for p in "${OWN[@]}"; do excludes+=(":(exclude)$p"); done
    git -C "$dir" add -A
    git -C "$dir" diff --cached "$BASE" -- . "${excludes[@]}" >"$PATCH"
    log "patch: $(grep -c '^diff --git' "$PATCH") files → $PATCH"
}

status() {
    local head
    head="$(git -C "$SERVER_REPO" rev-parse HEAD)"
    echo "base:   $BASE"
    echo "server: $head ($([[ "$head" == "$BASE" ]] && echo same || echo DIFFERENT))"
    echo "patch:  $(grep -c '^diff --git' "$PATCH") shared files; own: ${OWN[*]}"
}

install() {
    [[ "${1:-}" == --stage10 ]] || die "install changes /data/server: only at stage 10, with --stage10"
    [[ -z "$(git -C "$SERVER_REPO" status --porcelain)" ]] || die "$SERVER_REPO has uncommitted changes"
    [[ "$(git -C "$SERVER_REPO" rev-parse HEAD)" == "$BASE" ]] || die "$SERVER_REPO is not at the base $BASE"
    git -C "$SERVER_REPO" apply --check "$PATCH"
    copy_own "$SERVER_REPO"
    git -C "$SERVER_REPO" apply "$PATCH"
    log "installed into $SERVER_REPO: review, then commit there"
}

cmd="${1:-}"
shift || true
case "$cmd" in
    build) build "$@" ;;
    patch) patch "$@" ;;
    status) status ;;
    install) install "$@" ;;
    *) die "usage: overlay.sh build [DIR] | patch [DIR] | status | install --stage10" ;;
esac
