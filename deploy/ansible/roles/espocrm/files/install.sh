#!/usr/bin/env bash
# First installation of EspoCRM from the CLI (role espocrm, stage 09) — the sequence of the stand
# (scripts/stand/install.sh, step_espo) and of the official espocrm-docker entrypoint. JSON on stdin:
#   {"database": {…}, "admin": {"username": …, "password": …}, "settings": {…}}
# Secrets reach only the PHP processes, through stdin; the output names steps, never values. Safe to repeat after
# a failure: isInstalled is set last, an existing administrator is not created again.
# shellcheck source=/dev/null
source /usr/local/lib/espocrm/lib.sh
require_root

input="$(cat)"
part() { # key -> JSON of that part of the input
    python3 -c 'import json, sys; print(json.dumps(json.loads(sys.stdin.read())[sys.argv[1]], ensure_ascii=False))' \
        "$1" <<<"$input"
}
admin_user="$(python3 -c 'import json, sys; print(json.loads(sys.stdin.read())["admin"]["username"])' <<<"$input")"
[[ "$admin_user" =~ ^[A-Za-z0-9_.-]{1,50}$ ]] || die "bad administrator user name"

if [[ "$(espo_cmd config:get isInstalled 2>/dev/null || true)" == true ]]; then
    log "EspoCRM is already installed: nothing to do"
    exit 0
fi

log "installing EspoCRM $ESPO_VERSION into $ESPO_ROOT"
rm -rf "$ESPO_ROOT/data/cache"
espo_cmd config:populate >/dev/null
espo_cmd config:set defaultPermissions.user "$ESPO_USER" >/dev/null
espo_cmd config:set defaultPermissions.group "$ESPO_USER" >/dev/null
python3 -c 'import json, sys; print(json.dumps({"database": json.loads(sys.stdin.read())["database"]}))' <<<"$input" \
    | espo_config set >/dev/null
[[ "$(espo_cmd db:check 2>&1)" == OK ]] || die "EspoCRM cannot connect to its database"
espo_cmd rebuild >/dev/null

exists="$(mysql_root -N -B "$DB_NAME" -e "SELECT COUNT(*) FROM user WHERE user_name = '$admin_user' AND deleted = 0")"
if [[ "$exists" == 0 ]]; then
    espo_cmd create-admin-user "$admin_user" >/dev/null
fi
python3 -c 'import json, sys; print(json.loads(sys.stdin.read())["admin"]["password"])' <<<"$input" \
    | espo_cmd set-password "$admin_user" >/dev/null 2>&1
part settings | espo_config set >/dev/null
espo_cmd populate-scheduled-jobs >/dev/null
espo_cmd app-check >/dev/null || { espo_cmd app-check >&2 || true; die "app-check failed"; }
espo_cmd config:set isInstalled true --type=bool >/dev/null
log "EspoCRM $(espo_cmd version) installed; administrator: $admin_user"
