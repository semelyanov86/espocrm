#!/usr/bin/env bash
# The administrator of a production bundle on the stand (stage 11 round trip, D-187). A bundle pulled from production
# (scripts/deploy/bundle.sh pull) brings the production administrator: its password and its 2FA (TOTP, security keys).
# The stand logs in as the administrator of local.env — the import downloads every file through the stand. So:
#
#   stand-admin.sh park     after `task stand:restore` of the production bundle: keep the administrator's password
#                           hash and 2FA fields in a private file (600), give the stand its local.env password, 2FA off
#   stand-admin.sh unpark   before `task stand:backup` of the bundle going back: put the kept values back exactly
#                           (password, its version, 2FA, modified_at of the user row) and drop the stand's tokens
#
# Values never reach argv or the console: SQL goes to the stand MySQL through stdin, the kept file is private.
source "$(dirname "${BASH_SOURCE[0]}")/../stand/lib.sh"

PARKED="$STAND_PRIVATE_DIR/admin-parked.json"

admin_id() {
    local id
    id="$(mysql_root -N -B "$DB_NAME" <<<"SELECT id FROM user WHERE user_name = '$ESPO_ADMIN_USERNAME' AND deleted = 0;")"
    [[ "$id" =~ ^[A-Za-z0-9]+$ ]] || die "no active user $ESPO_ADMIN_USERNAME in $DB_NAME"
    printf '%s' "$id"
}

park() {
    load_private_env
    [[ "$ESPO_ADMIN_USERNAME" =~ ^[A-Za-z0-9_.-]+$ ]] || die "bad administrator name in local.env"
    [[ ! -e "$PARKED" ]] || die "already parked ($PARKED): unpark first"
    local id
    id="$(admin_id)"
    ( umask 077
      mysql_root -N -B -r "$DB_NAME" >"$PARKED" <<SQL || { rm -f "$PARKED"; exit 1; }
SELECT JSON_OBJECT('id', u.id, 'password', u.password, 'password_version', u.password_version,
    'modified_at', u.modified_at,
    'data', (SELECT JSON_OBJECT('auth2_f_a', d.auth2_f_a, 'auth2_f_a_method', d.auth2_f_a_method,
                                'auth2_f_a_totp_secret', d.auth2_f_a_totp_secret,
                                'auth2_f_a_email_address', d.auth2_f_a_email_address,
                                'c_security_keys', d.c_security_keys)
             FROM user_data d WHERE d.user_id = u.id AND d.deleted = 0 LIMIT 1),
    'parked_at', UTC_TIMESTAMP())
FROM user u WHERE u.id = '$id';
SQL
    )
    python3 -c 'import json, sys; json.load(open(sys.argv[1]))' "$PARKED" || { rm -f "$PARKED"; die "cannot keep the administrator"; }
    printf '%s\n' "$ESPO_ADMIN_PASSWORD" | espo_cmd set-password "$ESPO_ADMIN_USERNAME" >/dev/null 2>&1 \
        || die "set-password failed (the kept values are in $PARKED)"
    # Plain SQL, not the ORM: the hook ClearSecurityKeys would wipe the keys of a 2FA switched off through the ORM.
    mysql_root "$DB_NAME" <<<"UPDATE user_data SET auth2_f_a = 0 WHERE user_id = '$id';"
    log "administrator parked: the stand logs in with local.env, the values of production kept in $PARKED"
}

unpark() {
    [[ -f "$PARKED" ]] || die "nothing parked ($PARKED)"
    python3 - "$PARKED" <<'PY' | mysql_root "$DB_NAME"
import json, sys
d = json.load(open(sys.argv[1]))
def q(v):
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, (int, float)):
        return str(v)
    return "UNHEX('" + str(v).encode("utf-8").hex() + "')"
uid = d["id"]
assert uid.isalnum()
print(f"UPDATE user SET password = {q(d['password'])}, password_version = {q(d['password_version'])}, "
      f"modified_at = {q(d['modified_at'])} WHERE id = '{uid}';")
if d.get("data") is not None:
    sets = ", ".join(f"{k} = {q(v)}" for k, v in d["data"].items())
    print(f"UPDATE user_data SET {sets} WHERE user_id = '{uid}' AND deleted = 0;")
print(f"DELETE FROM auth_token WHERE user_id = '{uid}' AND created_at >= {q(d['parked_at'])};")
PY
    rm -f "$PARKED"
    log "administrator unparked: password, 2FA and the user row of production are back, stand tokens dropped"
}

case "${1:-}" in
    park) park ;;
    unpark) unpark ;;
    *) die "usage: stand-admin.sh park | unpark" ;;
esac
