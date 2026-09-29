#!/usr/bin/env bash
# Health check of the local EspoCRM stand: services, MySQL, EspoCRM CLI checks, HTTP/API login,
# cron, permissions and config drift. Prints one line per check; exit 1 if any check FAILs.
#
#   scripts/stand/health.sh            # full check
#   CRON_MAX_AGE=150 scripts/stand/health.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

: "${CRON_MAX_AGE:=150}"   # seconds since the last cron.php run
FAILS=0
WARNS=0

report() { # status name detail
    printf '%-5s %-36s %s\n' "$1" "$2" "${3:-}"
    case "$1" in FAIL) FAILS=$((FAILS + 1)) ;; WARN) WARNS=$((WARNS + 1)) ;; esac
}
check() { # name detail cmd...
    local name="$1" detail="$2"; shift 2
    if "$@" >/dev/null 2>&1; then report OK "$name" "$detail"; else report FAIL "$name" "$detail"; fi
}
strip_ansi() { sed -E 's/\x1b\[[0-9;]*m//g'; }

load_private_env

# --- services -------------------------------------------------------------------------------
for unit in "$MYSQL_UNIT" "$FPM_UNIT" apache2 cron; do
    state="$(systemctl is-active "$unit" 2>/dev/null || true)"
    enabled="$(systemctl is-enabled "$unit" 2>/dev/null || true)"
    [[ "$state" == active && "$enabled" == enabled ]] && s=OK || s=FAIL
    report "$s" "service: $unit" "$state, $enabled"
done

# --- MySQL ------------------------------------------------------------------------------------
if row="$(mysql_root -N -B -e "SELECT @@version, @@port, @@sql_mode, @@character_set_server,
        (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='$DB_NAME')" 2>/dev/null)"; then
    IFS=$'\t' read -r v port mode cs tables <<<"$row"
    [[ "$v" == "$MYSQL_VERSION" && "$port" == "$MYSQL_PORT" ]] && s=OK || s=FAIL
    report "$s" "mysql: server" "$v on 127.0.0.1:$port, $cs"
    [[ "$mode" == "$MYSQL_SQL_MODE" ]] && s=OK || s=FAIL
    report "$s" "mysql: sql_mode" "$mode"
    [[ "$tables" -gt 50 ]] && s=OK || s=FAIL
    report "$s" "mysql: schema $DB_NAME" "$tables tables"
else
    report FAIL "mysql: server" "no connection via $MYSQL_SOCKET"
fi

# --- EspoCRM CLI --------------------------------------------------------------------------------
v="$(espo_cmd version 2>/dev/null || true)"
[[ "$v" == "$ESPO_VERSION" ]] && s=OK || s=FAIL
report "$s" "espo: version" "${v:-?} (pinned $ESPO_VERSION)"
check "espo: db:check" "$DB_USER@$MYSQL_HOST:$MYSQL_PORT/$DB_NAME" test "$(espo_cmd db:check 2>&1)" == OK
if out="$(espo_cmd app-check 2>&1 | strip_ansi)"; then
    report OK "espo: app-check" "$(tr '\n' ';' <<<"$out" | sed 's/;$//; s/;/; /g')"
else
    report FAIL "espo: app-check" "$(tr '\n' ';' <<<"$out")"
fi
if out="$(espo_cmd check-file-permissions 2>&1 | strip_ansi)"; then
    report OK "espo: writable dirs" "$(grep -c ' OK : ' <<<"$out") OK as $ESPO_USER"
else
    report FAIL "espo: writable dirs" "$(grep 'FAIL' <<<"$out" | tr '\n' ' ')"
fi

# --- HTTP and API login ------------------------------------------------------------------------
if getent hosts "$ESPO_SITE_HOST" | grep -q '^127\.0\.0\.1'; then
    report OK "dns: $ESPO_SITE_HOST" "127.0.0.1 (/etc/hosts)"
else
    report FAIL "dns: $ESPO_SITE_HOST" "not resolved to 127.0.0.1"
fi
http_rc=0
http_out="$(ESPO_ADMIN_USERNAME="$ESPO_ADMIN_USERNAME" ESPO_ADMIN_PASSWORD="$ESPO_ADMIN_PASSWORD" \
    python3 "$STAND_DIR/health_http.py" 2>/dev/null)" || http_rc=$?
grep -v '^# http checks completed$' <<<"$http_out" || true
FAILS=$((FAILS + $(grep -c '^FAIL' <<<"$http_out" || true)))
WARNS=$((WARNS + $(grep -c '^WARN' <<<"$http_out" || true)))
if ! grep -q '^# http checks completed$' <<<"$http_out"; then
    report FAIL "http: checks" "health_http.py did not complete (rc=$http_rc)"
fi

# --- cron / background jobs -------------------------------------------------------------------
if [[ -f "$CRON_FILE" ]]; then
    report OK "cron: $CRON_FILE" "present"
else
    report FAIL "cron: $CRON_FILE" "missing"
fi
cron_php="$(as_user "$ESPO_USER" env PATH="$STAND_PATH" php -r 'echo PHP_VERSION;' 2>/dev/null || true)"
[[ "$cron_php" == "$PHP_VERSION".* ]] && s=OK || s=FAIL
report "$s" "cron: php in PATH" "${cron_php:-?} (parallel job processes)"
last_file="$ESPO_ROOT/data/cache/application/cronLastRunTime.php"
if mtime="$(as_root stat -c %Y "$last_file" 2>/dev/null)"; then
    age=$(( $(date +%s) - mtime ))
    [[ $age -le $CRON_MAX_AGE ]] && s=OK || s=FAIL
    report "$s" "cron: last cron.php run" "${age}s ago (limit ${CRON_MAX_AGE}s)"
else
    report FAIL "cron: last cron.php run" "never ($last_file missing)"
fi
if row="$(mysql_root -N -B "$DB_NAME" -e "SELECT
        SUM(status='Success' AND executed_at > UTC_TIMESTAMP() - INTERVAL 15 MINUTE),
        SUM(status='Failed' AND modified_at > UTC_TIMESTAMP() - INTERVAL 1 DAY),
        (SELECT COUNT(*) FROM scheduled_job WHERE deleted=0 AND status='Active')
        FROM job WHERE deleted=0" 2>/dev/null)"; then
    IFS=$'\t' read -r ok_jobs failed_jobs scheduled <<<"$row"
    ok_jobs="${ok_jobs/NULL/0}"; failed_jobs="${failed_jobs/NULL/0}"
    [[ "$ok_jobs" -gt 0 ]] && s=OK || s=FAIL
    report "$s" "cron: jobs done (15 min)" "$ok_jobs successful; $scheduled active scheduled jobs"
    [[ "$failed_jobs" -eq 0 ]] && s=OK || s=WARN
    report "$s" "cron: failed jobs (24 h)" "$failed_jobs"
else
    report FAIL "cron: jobs" "cannot query job table"
fi

# --- permissions -----------------------------------------------------------------------------
stat_data="$(as_root stat -c '%U:%G %a' "$ESPO_ROOT/data")"
[[ "$stat_data" == "$ESPO_USER:$ESPO_USER 770" ]] && s=OK || s=FAIL
report "$s" "perms: data/" "$stat_data"
if as_user www-data test -r "$ESPO_ROOT/data/config-internal.php" 2>/dev/null; then
    report FAIL "perms: config-internal.php" "readable by www-data"
else
    report OK "perms: config-internal.php" "not readable by www-data"
fi
if as_root grep -q "'password'" "$ESPO_ROOT/data/config.php"; then
    report FAIL "perms: secrets placement" "a password is stored in data/config.php"
else
    report OK "perms: secrets placement" "DB credentials only in config-internal.php"
fi
if as_user "$ESPO_USER" test -w "$ESPO_ROOT/application/Espo/Core/Application.php" 2>/dev/null \
   || as_user "$ESPO_USER" test -w "$ESPO_ROOT/public" 2>/dev/null; then
    report FAIL "perms: core read-only" "$ESPO_USER can modify core files"
else
    report OK "perms: core read-only" "$ESPO_USER cannot modify application/ and public/"
fi
p_env="$(stat -c %a "$STAND_PRIVATE_ENV")"; p_dir="$(stat -c %a "$STAND_PRIVATE_DIR")"
[[ "$p_env" == 600 && "$p_dir" == 700 ]] && s=OK || s=FAIL
report "$s" "perms: private settings" "local.env $p_env, dir $p_dir"

# --- rendered configs are unchanged (no manual drift) ---------------------------------------
drift=()
for pair in "my.cnf.tmpl:$ETC_DIR/my.cnf" "itvolga-espo-mysql.service.tmpl:/etc/systemd/system/$MYSQL_UNIT.service" \
            "php-fpm.conf.tmpl:$ETC_DIR/php-fpm.conf" "itvolga-espo-php-fpm.service.tmpl:/etc/systemd/system/$FPM_UNIT.service" \
            "apache-vhost.conf.tmpl:$APACHE_SITE_FILE" "cron.tmpl:$CRON_FILE"; do
    tmpl="${pair%%:*}" dest="${pair#*:}"
    if ! python3 "$STAND_DIR/render.py" "$TEMPLATE_DIR/$tmpl" | as_root cmp -s - "$dest"; then
        drift+=("$dest")
    fi
done
if [[ ${#drift[@]} -eq 0 ]]; then
    report OK "config: templates" "6 rendered files match Git templates"
else
    report WARN "config: templates" "differs: ${drift[*]} (re-run task stand:install)"
fi

# --- leftovers of failed restores (kept on purpose for a manual rollback) --------------------
# restore.sh runs this check before it drops its own leftovers; it passes their timestamp here.
own="${RESTORE_TS:-none}"
left_db="$(mysql_root -N -B -e "SELECT COUNT(*) FROM information_schema.schemata WHERE (schema_name
    LIKE '${DB_NAME}\\_\\_prev\\_%' OR schema_name LIKE '${DB_NAME}\\_\\_restore\\_%')
    AND schema_name NOT LIKE '%\\_$own'" 2>/dev/null || echo '?')"
left_dir="$(find "$STAND_PRIVATE_DIR" -mindepth 1 -maxdepth 1 -name '.restore-aside-*' ! -name ".restore-aside-$own" | wc -l)"
if [[ "$left_db" == 0 && "$left_dir" == 0 ]]; then
    report OK "restore: leftovers" "none"
else
    report WARN "restore: leftovers" "$left_db databases, $left_dir directories (task stand:restore-cleanup)"
fi

# --- backups (informational) ------------------------------------------------------------------
last_backup="$(find "$BACKUP_DIR" -mindepth 2 -maxdepth 2 -name MANIFEST -printf '%T@ %h\n' 2>/dev/null | sort -n | tail -n1 | cut -d' ' -f2-)"
if [[ -n "$last_backup" ]]; then
    report OK "backup: latest" "$(basename "$last_backup")"
else
    report WARN "backup: latest" "no backups in $BACKUP_DIR (task stand:backup)"
fi

echo "---"
echo "health: $FAILS failed, $WARNS warnings"
[[ $FAILS -eq 0 ]]
