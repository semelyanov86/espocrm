#!/usr/bin/env bash
# Remove the local stand from the workstation (for a from-scratch reinstall or cleanup).
#
#   scripts/stand/uninstall.sh --yes           # services, vhost, cron, rendered configs
#   scripts/stand/uninstall.sh --yes --purge   # + MySQL data directory and binaries, EspoCRM data/
#                                              #   and core files, ACLs, the $ESPO_USER system user
#
# Never touches Git-tracked files, the private settings ($STAND_PRIVATE_ENV) or backups.
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

yes=0 purge=0
for arg in "$@"; do
    case "$arg" in --yes) yes=1 ;; --purge) purge=1 ;; *) die "usage: uninstall.sh --yes [--purge]" ;; esac
done
[[ $yes == 1 ]] || die "refusing to run without --yes"
[[ $EUID -ne 0 ]] || die "run as the developer user, not root"

as_root rm -f "$CRON_FILE" "$CRON_FILE.backup-paused"
if [[ -e "/etc/apache2/sites-enabled/$APACHE_SITE.conf" ]]; then as_root a2dissite -q "$APACHE_SITE" >/dev/null; fi
as_root rm -f "$APACHE_SITE_FILE"
as_root apache2ctl -t >/dev/null 2>&1 && as_root systemctl reload apache2
for unit in "$FPM_UNIT" "$MYSQL_UNIT"; do
    as_root systemctl disable --now --quiet "$unit" 2>/dev/null || true
    as_root rm -f "/etc/systemd/system/$unit.service"
done
as_root systemctl daemon-reload
as_root rm -rf "$ETC_DIR"
log "services, vhost, cron and configs removed"

if [[ $purge == 1 ]]; then
    as_root rm -rf "$MYSQL_DATADIR" "$MYSQL_OPT"
    stamp="$ESPO_ROOT/.espocrm-core"
    if [[ -f "$stamp" ]]; then
        while IFS= read -r entry; do
            case "$entry" in ""|custom|data|*/*|.|..) continue ;; esac
            if [[ "$entry" == client ]]; then
                find "$ESPO_ROOT/client" -mindepth 1 -maxdepth 1 ! -name custom -exec rm -rf {} +
            elif git -C "$REPO_ROOT" ls-files --error-unmatch -- "$entry" >/dev/null 2>&1; then
                warn "skip tracked entry $entry"
            else
                rm -rf "${ESPO_ROOT:?}/$entry"
            fi
        done < <(tail -n +2 "$stamp")
        rm -f "$stamp"
    fi
    as_root rm -rf "${ESPO_ROOT:?}/data"
    for dir in custom/Espo/Custom custom/Espo/Modules client/custom; do
        [[ -d "$ESPO_ROOT/$dir" ]] && as_root setfacl -R -b "$ESPO_ROOT/$dir"
    done
    if id -u "$ESPO_USER" >/dev/null 2>&1; then as_root userdel "$ESPO_USER"; fi
    log "purged: MySQL data and binaries, EspoCRM core and data/, ACLs, user $ESPO_USER"
fi
