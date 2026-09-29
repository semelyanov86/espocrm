#!/usr/bin/env bash
# Service control of the local stand (all names and paths come from deploy/local/stand.conf).
#   scripts/stand/ctl.sh status|start|stop|restart|logs|backups|db-shell
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

case "${1:-}" in
    status)
        systemctl --no-pager status "$MYSQL_UNIT" "$FPM_UNIT" apache2 cron 2>/dev/null \
            | grep -E '^(●|○|×)|Active:' || true
        if [[ -f "$CRON_FILE" ]]; then echo "cron entry: $CRON_FILE"; else echo "cron entry: absent (stand stopped)"; fi
        ;;
    start)
        as_root systemctl start "$MYSQL_UNIT" "$FPM_UNIT"
        "$STAND_DIR/install.sh" cron
        ;;
    stop)
        # Scheduler first, so no cron.php runs against a stopping database.
        as_root rm -f "$CRON_FILE"
        for _ in $(seq 60); do pgrep -u "$ESPO_USER" -f "$ESPO_ROOT/cron.php" >/dev/null || break; sleep 1; done
        as_root systemctl stop "$FPM_UNIT" "$MYSQL_UNIT"
        log "stopped (cron entry removed; start with: task stand:start)"
        ;;
    restart)
        as_root systemctl restart "$MYSQL_UNIT"
        as_root systemctl restart "$FPM_UNIT"
        as_root systemctl reload apache2
        log "restarted $MYSQL_UNIT, $FPM_UNIT; reloaded apache2"
        ;;
    logs)
        as_root journalctl --no-pager -n "${LINES:-30}" -u "$MYSQL_UNIT" -u "$FPM_UNIT" -t "$CRON_TAG" -t "$FPM_UNIT"
        echo "--- apache: /var/log/apache2/$ESPO_SITE_HOST-error.log"
        as_root tail -n "${LINES:-30}" "/var/log/apache2/$ESPO_SITE_HOST-error.log" 2>/dev/null || true
        latest="$(as_root find "$ESPO_ROOT/data/logs" -name '*.log' -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -n1 | cut -d' ' -f2-)"
        if [[ -n "$latest" ]]; then echo "--- espocrm: $latest"; as_root tail -n "${LINES:-30}" "$latest"; fi
        ;;
    backups)
        find "$BACKUP_DIR" -mindepth 2 -maxdepth 2 -name MANIFEST -printf '%h\n' 2>/dev/null | sort | while read -r d; do
            printf '%s  %s  %s\n' "$(basename "$d")" "$(du -sh "$d" | cut -f1)" "$(sed -n 's/^rows_total=/rows=/p' "$d/MANIFEST")"
        done
        ;;
    db-shell)
        exec sudo -n "$MYSQL_HOME/bin/mysql" --defaults-file="$ETC_DIR/my.cnf" -uroot "$DB_NAME"
        ;;
    *)
        die "usage: ctl.sh status|start|stop|restart|logs|backups|db-shell"
        ;;
esac
