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

pause_writers
# Only files rendered by the stand are removed (every template carries this marker), so an
# overridden name in stand.conf can never delete a foreign unit, site or cron file.
remove_rendered() { # file
    if as_root test -e "$1"; then
        if as_root grep -qF "$STAND_MARKER" "$1"; then as_root rm -f "$1"; else warn "skip $1: not rendered by the stand"; fi
    fi
}

remove_rendered "$CRON_FILE"
remove_rendered "$CRON_FILE.paused"
if as_root grep -qsF "$STAND_MARKER" "$APACHE_SITE_FILE"; then
    if [[ -e "/etc/apache2/sites-enabled/$APACHE_SITE.conf" ]]; then as_root a2dissite -q "$APACHE_SITE" >/dev/null; fi
fi
remove_rendered "$APACHE_SITE_FILE"
as_root apache2ctl -t >/dev/null 2>&1 && as_root systemctl reload apache2
for unit in "$FPM_UNIT" "$MYSQL_UNIT"; do
    if as_root grep -qsF "$STAND_MARKER" "/etc/systemd/system/$unit.service"; then
        as_root systemctl disable --now --quiet "$unit" 2>/dev/null || true
    fi
    remove_rendered "/etc/systemd/system/$unit.service"
done
as_root systemctl daemon-reload
remove_rendered "$ETC_DIR/my.cnf"
remove_rendered "$ETC_DIR/php-fpm.conf"
as_root rmdir --ignore-fail-on-non-empty "$ETC_DIR" 2>/dev/null || true
log "services, vhost, cron and configs removed"

if [[ $purge == 1 ]]; then
    # MySQL data: only a data directory initialised by the stand (marker written by install.sh).
    if as_root test -f "$MYSQL_DATADIR/.itvolga-espo-stand"; then
        as_root rm -rf "$MYSQL_DATADIR"
    elif as_root test -e "$MYSQL_DATADIR"; then
        warn "skip $MYSQL_DATADIR: no .itvolga-espo-stand marker"
    fi
    # MySQL binaries and the php shim: only the entries the stand created, then empty parents.
    removed_opt=0
    if as_root test -x "$MYSQL_OPT/mysql-$MYSQL_VERSION/bin/mysqld"; then
        as_root rm -rf "$MYSQL_OPT/mysql-$MYSQL_VERSION"; removed_opt=1
    fi
    if as_root test -L "$MYSQL_HOME"; then as_root rm -f "$MYSQL_HOME"; fi
    if [[ "$(readlink "$STAND_BIN_DIR/php" 2>/dev/null)" == "$PHP_BIN" ]]; then
        as_root rm -f "$STAND_BIN_DIR/php"
        as_root rmdir --ignore-fail-on-non-empty "$STAND_BIN_DIR" 2>/dev/null || true
    fi
    if [[ $removed_opt == 1 ]]; then as_root rmdir --ignore-fail-on-non-empty "$MYSQL_OPT" 2>/dev/null || true; fi
    # EspoCRM core and data/: only in a directory that holds a stand install (.espocrm-core).
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
        as_root rm -rf "${ESPO_ROOT:?}/data"
        rm -f "$stamp"
    else
        warn "skip EspoCRM core and data/: no $stamp"
    fi
    for dir in custom/Espo/Custom custom/Espo/Modules client/custom; do
        if [[ -d "$ESPO_ROOT/$dir" ]]; then as_root setfacl -R -b "$ESPO_ROOT/$dir"; fi
    done
    if id -u "$ESPO_USER" >/dev/null 2>&1; then as_root userdel "$ESPO_USER"; fi
    log "purge finished (paths without the stand markers were skipped, see warnings above)"
fi
