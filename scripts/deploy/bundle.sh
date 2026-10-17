#!/usr/bin/env bash
# Move an EspoCRM bundle between the stand and production (D-187; stages 10–11 only, with the owner's permission —
# production is read-only before). The bundle format is the same on both sides (scripts/stand/backup.sh,
# espocrm-backup of the role espocrm): the verified import of the stand reaches production through espocrm-restore,
# and production comes back to the stand for the last delta through scripts/stand/restore.sh.
#
#   bundle.sh push <stand-bundle-dir|name>   → production $REMOTE_DIR/<name>/ (700/600), SHA256SUMS checked there
#   bundle.sh pull <production-bundle-name>  → /data/itvolga/espo-private/stand/backups/<name>/ (700/600), checked
#
# The bytes go through stdin of one SSH command each way (tar), nothing is written to argv or to /tmp. A bundle holds
# data/config-internal.php (database password, cryptKey) and personal data: private on both sides, never in Git.
# BUNDLE_REMOTE (default: ssh -o BatchMode=yes sergey@serv.sergeyem.ru) may be another transport for tests
# (e.g. "docker exec -i <container>").
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STAND_BACKUPS="${STAND_BACKUPS:-/data/itvolga/espo-private/stand/backups}"
REMOTE_DIR="${REMOTE_DIR:-/var/backups/espocrm/bundles}"
read -r -a REMOTE <<<"${BUNDLE_REMOTE:-ssh -o BatchMode=yes -o IdentitiesOnly=yes -i $HOME/.ssh/id_ed25519 sergey@serv.sergeyem.ru}"

log() { printf '[bundle] %s\n' "$*" >&2; }
die() { printf '[bundle] ERROR: %s\n' "$*" >&2; exit 1; }
# ssh joins its arguments into one command line for the remote shell: the script goes there quoted (%q); other
# transports (docker exec) pass argv as is.
remote_sudo() {
    if [[ "$(basename "${REMOTE[0]}")" == ssh ]]; then
        "${REMOTE[@]}" "sudo -n bash -c $(printf '%q' "$1")"
    else
        "${REMOTE[@]}" sudo -n bash -c "$1"
    fi
}

valid_name() { [[ "$1" =~ ^[0-9]{8}T[0-9]{6}(-[a-z0-9-]+)?$ ]] || die "bad bundle name '$1'"; }

push() {
    local src="${1:?usage: bundle.sh push <stand-bundle-dir|name>}"
    [[ -d "$src" ]] || src="$STAND_BACKUPS/$src"
    [[ -f "$src/MANIFEST" && -f "$src/SHA256SUMS" ]] || die "no bundle at $src"
    ( cd "$src" && sha256sum -c --quiet SHA256SUMS ) || die "the local bundle is damaged"
    local name
    name="$(basename "$src")"
    valid_name "$name"
    log "push $name → ${REMOTE[*]: -1}:$REMOTE_DIR/$name"
    tar -C "$src" -cf - MANIFEST SHA256SUMS table-counts.tsv db.sql.gz files.tar.gz \
        | remote_sudo "set -e; umask 077; d='$REMOTE_DIR/$name'; test ! -e \"\$d\"; install -d -m 0700 '$REMOTE_DIR' \"\$d\";
                       tar -C \"\$d\" --no-same-owner -xf -; chown -R root:root \"\$d\"; chmod 600 \"\$d\"/*;
                       cd \"\$d\" && sha256sum -c --quiet SHA256SUMS && echo verified"
    log "on production: sudo espocrm-restore $REMOTE_DIR/$name"
}

pull() {
    local name="${1:?usage: bundle.sh pull <production-bundle-name>}"
    valid_name "$name"
    local dst="$STAND_BACKUPS/$name"
    [[ ! -e "$dst" ]] || die "$dst exists"
    install -d -m 0700 "$STAND_BACKUPS"
    mkdir -m 0700 "$dst"
    log "pull $name → $dst"
    if ! remote_sudo "set -e; d='$REMOTE_DIR/$name'; cd \"\$d\" && sha256sum -c --quiet SHA256SUMS >&2
                      tar -C \"\$d\" -cf - MANIFEST SHA256SUMS table-counts.tsv db.sql.gz files.tar.gz" \
            | ( umask 077; tar -C "$dst" --no-same-owner -xf - ); then
        rm -rf "$dst"; die "pull failed"
    fi
    chmod 600 "$dst"/*
    ( cd "$dst" && sha256sum -c --quiet SHA256SUMS ) || { rm -rf "$dst"; die "the pulled bundle is damaged"; }
    log "on the stand: task stand:restore -- $name --yes --skip-custom"
}

cmd="${1:-}"
shift || true
case "$cmd" in
    push) push "$@" ;;
    pull) pull "$@" ;;
    *) die "usage: bundle.sh push <stand-bundle-dir|name> | pull <production-bundle-name>" ;;
esac
