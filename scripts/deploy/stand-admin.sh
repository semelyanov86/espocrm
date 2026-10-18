#!/usr/bin/env bash
# The administrator of a production bundle on the stand (stage 11 round trip, D-187). A bundle pulled from production
# (scripts/deploy/bundle.sh pull) brings the production administrator: its password and its 2FA (TOTP, security keys).
# The stand logs in as the administrator of local.env — the import downloads every file through the stand. So:
#
#   stand-admin.sh park-mail  (scripts/stand/restore.sh runs it for a production bundle, before PHP-FPM and cron
#                             start): keep use_smtp and status of every EmailAccount and InboundEmail in a private file
#                             (600) and switch their sending and fetching off — the stand never sends or fetches
#                             real mail (the SMTP of the system is cleared by restore.sh itself, D-189)
#   stand-admin.sh park       after `task stand:restore` of the production bundle: keep the administrator's password
#                             hash and 2FA fields in a private file (600), give the stand its local.env password, 2FA off
#   stand-admin.sh unpark     before `task stand:backup` of the bundle going back: pause the writers of the stand
#                             (listener, cron, PHP-FPM) and leave them paused — the mail accounts of production are
#                             active again —, put the kept values back exactly (password, its version, 2FA, modified_at
#                             of the user row, the mail accounts) and drop the stand's tokens; a backup taken now is
#                             marked production_data=1 (restore.sh parks its mail like a bundle of production)
#   stand-admin.sh repark     after that backup and the fingerprint: park the mail and the administrator again, then
#                             start the writers paused by unpark (a restore of the stand starts them as well)
#   stand-admin.sh check      fails while anything is parked (restore.sh refuses a new production bundle then)
#
# Values never reach argv or the console: SQL goes to the stand MySQL through stdin, the kept file is private.
source "$(dirname "${BASH_SOURCE[0]}")/../stand/lib.sh"

PARKED="$STAND_PRIVATE_DIR/admin-parked.json"
MAIL_PARKED="$STAND_PRIVATE_DIR/mail-parked.json"
# Present while the stand holds the unparked data of production with its writers paused: what unpark paused
# (WRITERS_* of pause_writers), read back by repark; scripts/stand/backup.sh marks its bundle, restore.sh removes it.
UNPARKED="$STAND_PRIVATE_DIR/production-unparked.env"

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

park_mail() {
    [[ ! -e "$MAIL_PARKED" ]] || die "mail already parked ($MAIL_PARKED): unpark first"
    ( umask 077
      mysql_root -N -B -r "$DB_NAME" >"$MAIL_PARKED" <<'SQL' || { rm -f "$MAIL_PARKED"; exit 1; }
SELECT JSON_OBJECT('accounts', COALESCE((SELECT JSON_ARRAYAGG(JSON_OBJECT('table', 'email_account', 'id', id,
        'use_smtp', use_smtp, 'status', status)) FROM email_account), JSON_ARRAY()),
    'inbound', COALESCE((SELECT JSON_ARRAYAGG(JSON_OBJECT('table', 'inbound_email', 'id', id,
        'use_smtp', use_smtp, 'status', status)) FROM inbound_email), JSON_ARRAY()));
SQL
    )
    python3 -c 'import json, sys; json.load(open(sys.argv[1]))' "$MAIL_PARKED" || { rm -f "$MAIL_PARKED"; die "cannot keep the mail accounts"; }
    mysql_root "$DB_NAME" <<<"UPDATE email_account SET use_smtp = 0, status = 'Inactive'; UPDATE inbound_email SET use_smtp = 0, status = 'Inactive';"
    log "mail accounts of the bundle parked: sending and fetching off on the stand, the values kept in $MAIL_PARKED"
}

check() {
    [[ ! -e "$PARKED" && ! -e "$MAIL_PARKED" ]] || die "parked values of a production bundle remain ($STAND_PRIVATE_DIR): unpark first"
}
unparked() { [[ -f "$UNPARKED" ]]; }  # for scripts/stand/backup.sh

unpark() {
    [[ -f "$PARKED" || -f "$MAIL_PARKED" ]] || die "nothing parked ($PARKED, $MAIL_PARKED)"
    [[ ! -e "$UNPARKED" ]] || die "already unparked ($UNPARKED): repark or restore the stand"
    # The mail accounts of production become active again: cron (fetching, sending) must not run from here until they
    # are parked again (repark) or the database is replaced (restore.sh).
    log "pausing the writers of the stand (listener, cron, $FPM_UNIT); they stay paused until repark or a restore"
    pause_writers
    ( umask 077; printf 'WRITERS_CRON=%s\nWRITERS_FPM=%s\nWRITERS_TELEPHONY=%s\n' \
        "$WRITERS_CRON" "$WRITERS_FPM" "$WRITERS_TELEPHONY" >"$UNPARKED" )
    if [[ -f "$MAIL_PARKED" ]]; then
        python3 - "$MAIL_PARKED" <<'PY' | mysql_root "$DB_NAME"
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
for row in d["accounts"] + d["inbound"]:
    assert row["table"] in ("email_account", "inbound_email") and str(row["id"]).isalnum()
    print(f"UPDATE {row['table']} SET use_smtp = {q(row['use_smtp'])}, status = {q(row['status'])} WHERE id = '{row['id']}';")
PY
        rm -f "$MAIL_PARKED"
        log "mail accounts unparked: use_smtp and status of production are back"
    fi
    [[ -f "$PARKED" ]] || return 0
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
repark() {
    [[ -f "$UNPARKED" ]] || die "nothing unparked ($UNPARKED)"
    [[ "$(cat "$UNPARKED")" =~ ^WRITERS_CRON=[01]$'\n'WRITERS_FPM=[01]$'\n'WRITERS_TELEPHONY=[01]$ ]] \
        || die "bad $UNPARKED"
    # shellcheck source=/dev/null
    source "$UNPARKED"
    [[ -f "$MAIL_PARKED" ]] || park_mail
    [[ -f "$PARKED" ]] || park
    rm -f "$UNPARKED"
    resume_writers
    log "parked again; the writers of the stand run"
}

case "${1:-}" in
    park) park ;;
    park-mail) park_mail ;;
    unpark) unpark ;;
    repark) repark ;;
    check) check ;;
    unparked) unparked ;;
    *) die "usage: stand-admin.sh park | park-mail | unpark | repark | check | unparked" ;;
esac
