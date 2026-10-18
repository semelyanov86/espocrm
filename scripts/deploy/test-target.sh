#!/usr/bin/env bash
# Disposable test target of the server Ansible with the role espocrm (stage 09, D-180): a container of Ubuntu 26.04
# (the release of production) with systemd, reached over the Docker connection. Production is never contacted.
#
#   test-target.sh all          up → prepare → converge → idempotent → check → drift → verify → telephony → switch → cd
#   test-target.sh up | prepare | converge | idempotent | check | drift | verify | telephony | switch | cd | down | shell
#
# The overlay (scripts/deploy/overlay.sh) is the code under test: the role espocrm, the playbooks 11/12 and the
# patched server roles. The vault of the test is generated from vault.yml.example with random values
# (build/ansible-test, 600, never committed); the data are synthetic. Logs: build/ansible-test/logs/.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TESTS="$REPO/deploy/ansible/tests"
OVERLAY="$REPO/build/ansible-overlay"
RUN="$REPO/build/ansible-test"
CONTAINER=itvolga-espo-ansible-target
IMAGE=itvolga-espo-ansible-target:26.04
LOGS="$RUN/logs"

log() { printf '[test-target] %s\n' "$*" >&2; }
die() { printf '[test-target] ERROR: %s\n' "$*" >&2; exit 1; }
in_target() { docker exec -i "$@"; }

vault_value() { # key -> value from the synthetic vault (never printed by the callers)
    python3 -c 'import sys, yaml; print(yaml.safe_load(open(sys.argv[1]))[sys.argv[2]])' \
        "$RUN/inventory/group_vars/all/vault.yml" "$1"
}

up() {
    log "building $IMAGE"
    docker build -q -t "$IMAGE" "$TESTS" >/dev/null
    if docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER"; then
        log "$CONTAINER exists: reusing it (test-target.sh down to start from scratch)"
        docker start "$CONTAINER" >/dev/null
    else
        docker run -d --name "$CONTAINER" --hostname serv-test --privileged --cgroupns=private \
            --tmpfs /run --tmpfs /run/lock --tmpfs /tmp "$IMAGE" >/dev/null
    fi
    local state="" i
    for i in $(seq 60); do
        state="$(docker exec "$CONTAINER" systemctl is-system-running 2>/dev/null || true)"
        [[ "$state" == running || "$state" == degraded ]] && break
        sleep 1
    done
    [[ "$state" == running || "$state" == degraded ]] || die "systemd of the target: ${state:-no answer}"
    log "target up (systemd: $state)"
}

inventory() {
    "$REPO/scripts/deploy/overlay.sh" build "$OVERLAY" >/dev/null
    rm -rf "$RUN/inventory"
    mkdir -p "$RUN/inventory/group_vars/all" "$LOGS"
    chmod 700 "$RUN"
    cp "$TESTS/inventory/hosts.yml" "$RUN/inventory/hosts.yml"
    cp "$OVERLAY/ansible/inventory/group_vars/all/vars.yml" "$RUN/inventory/group_vars/all/vars.yml"
    cp "$TESTS/inventory/group_vars/all/zz-test.yml" "$RUN/inventory/group_vars/all/zz-test.yml"
    # The vault of the test: every key of vault.yml.example and every vault_* name the roles reference (some live
    # only in the real vault, e.g. vault_opencloud_smtp_password) with a random value (kept for one target).
    if [[ ! -f "$RUN/vault.yml" ]]; then
        ( umask 077; python3 - "$OVERLAY/ansible" >"$RUN/vault.yml" <<'PY'
import pathlib, re, secrets, string, sys, yaml
root = pathlib.Path(sys.argv[1])
alphabet = string.ascii_letters + string.digits
def fill(value):
    if isinstance(value, dict):
        return {k: fill(v) for k, v in value.items()}
    if isinstance(value, list):
        return [fill(v) for v in value]
    return "".join(secrets.choice(alphabet) for _ in range(32))
vault = {k: fill(v) for k, v in yaml.safe_load(open(root / "inventory/group_vars/all/vault.yml.example")).items()}
for path in (root / "roles").rglob("*"):
    if path.is_file() and path.suffix in (".yml", ".j2"):
        for name in re.findall(r"\b(vault_[a-z0-9_]+)\b", path.read_text(errors="replace")):
            vault.setdefault(name, fill(""))
print(yaml.safe_dump(vault, sort_keys=True))
PY
        )
    fi
    install -m 0600 "$RUN/vault.yml" "$RUN/inventory/group_vars/all/vault.yml"
    cat >"$RUN/ansible.cfg" <<EOF
[defaults]
inventory = $RUN/inventory/hosts.yml
roles_path = $OVERLAY/ansible/roles
host_key_checking = False
retry_files_enabled = False
interpreter_python = auto_silent
gathering = smart
stdout_callback = yaml
callbacks_enabled = timer, profile_tasks
deprecation_warnings = False

[privilege_escalation]
become = True
become_method = sudo
become_user = root

[ssh_connection]
pipelining = True
EOF
}

playbook() { # name logfile [args...] — run a playbook of the overlay (or tests/prepare.yml) against the target
    local book="$1" name="$2"; shift 2
    local path="$OVERLAY/ansible/playbooks/$book"
    [[ "$book" == prepare.yml ]] && path="$TESTS/prepare.yml"
    log "ansible-playbook $book $* → $LOGS/$name.log"
    local rc=0
    ANSIBLE_CONFIG="$RUN/ansible.cfg" ansible-playbook "$path" "$@" >"$LOGS/$name.log" 2>&1 || rc=$?
    grep -A2 '^PLAY RECAP' "$LOGS/$name.log" | grep -E 'ok=' | sed 's/^/    /' >&2 || true
    [[ $rc == 0 ]] || { tail -40 "$LOGS/$name.log" >&2; die "$book failed (rc=$rc), log $LOGS/$name.log"; }
}

assert_unchanged() { # logfile name
    local line
    line="$(grep -A2 '^PLAY RECAP' "$LOGS/$1.log" | grep -E 'ok=' | tail -1)"
    [[ "$line" =~ changed=0[[:space:]] ]] || {
        grep -B1 -E '^changed:' "$LOGS/$1.log" | grep -E '^TASK' | sed 's/^/    changed: /' >&2 || true
        die "$1: not idempotent ($line)"; }
    log "$1: changed=0"
}

prepare() { inventory; playbook prepare.yml prepare; }
converge() { inventory; playbook 11-espocrm.yml converge; }
idempotent() { inventory; playbook 11-espocrm.yml idempotent; assert_unchanged idempotent; }

playbook_fails() { # name logfile pattern [args...] — the run must fail, its log must hold the pattern
    local book="$1" name="$2" pattern="$3"; shift 3
    local rc=0
    log "ansible-playbook $book $* → $LOGS/$name.log (a refusal expected)"
    ANSIBLE_CONFIG="$RUN/ansible.cfg" ansible-playbook "$OVERLAY/ansible/playbooks/$book" "$@" >"$LOGS/$name.log" 2>&1 \
        || rc=$?
    [[ $rc != 0 ]] || die "$name: the run succeeded, a refusal was expected"
    grep -qF "$pattern" "$LOGS/$name.log" || { tail -30 "$LOGS/$name.log" >&2; die "$name: failed without '$pattern'"; }
    log "$name: refused ($pattern)"
}

assert_task_changed() { # logfile task-name
    grep -A2 -F "TASK [espocrm : $2]" "$LOGS/$1.log" | grep -qE '^changed:' \
        || die "$1: task '$2' did not run"
}

# Drift of the module code on the server: the pending mark is written before the files change, the module is applied.
drift() {
    inventory
    in_target "$CONTAINER" bash -c 'echo >>/var/www/espocrm/custom/Espo/Modules/Itvolga/Resources/module.json'
    playbook 11-espocrm.yml drift
    assert_task_changed drift "Mark the module apply as pending before the module changes"
    assert_task_changed drift "Apply the module (clear-cache, rebuild, roles, finance, reports, client timestamp)"
    log "drift: pending marked before the sync, the module applied"
    playbook 11-espocrm.yml drift-again
    assert_unchanged drift-again
}
check() { inventory; playbook 11-espocrm.yml check --check --diff; assert_unchanged check; }

# Scenario on the target: health, synthetic records through the API, bundle, change, restore, fingerprints, restore
# checks of the bundle and of the restic tiers db and recordings, changes since, restore of a stand-format bundle.
verify() {
    inventory
    local pw
    pw="$(vault_value vault_espocrm_admin_password)"
    log "scenario on the target → $LOGS/verify.log"
    if ! HEALTH_PASSWORD="$pw" in_target -e HEALTH_USER=admin -e HEALTH_PASSWORD "$CONTAINER" bash -s \
            >"$LOGS/verify.log" 2>&1 <<'SCENARIO'
set -euo pipefail
source /etc/espocrm/espocrm.env
step() { printf '\n=== %s\n' "$*"; }
api() { # method path [json]
    curl -sS --fail-with-body --resolve serv.itvolga.com:8443:127.0.0.1 --cacert /etc/espocrm-test/ca.pem \
        -H "Espo-Authorization: $(printf '%s:%s' "$HEALTH_USER" "$HEALTH_PASSWORD" | base64 -w0)" \
        -H 'Content-Type: application/json' -X "$1" "https://serv.itvolga.com:8443/api/v1/$2" ${3:+-d "$3"}
}
id_of() { python3 -c 'import json, sys; print(json.load(sys.stdin)["id"])'; }
run="$(date +%s)"   # unique names: a repeated scenario must not hit the duplicate check of EspoCRM (409)

step "health after the deployment"
espocrm-health

step "outgoing mail taken over from Vtiger (synthetic vtiger_systems)"
espocrm-config get smtpServer smtpPort smtpSecurity smtpAuth outboundEmailFromAddress outboundEmailIsShared \
    | python3 -c 'import json, sys; d = json.load(sys.stdin); print(d)
assert d == {"smtpServer": "smtp.example.org", "smtpPort": 465, "smtpSecurity": "SSL", "smtpAuth": True,
             "outboundEmailFromAddress": "crm@example.org", "outboundEmailIsShared": True}, "mail settings"'
if [[ "$(espocrm-config get smtpPassword | python3 -c 'import json, sys; print(json.load(sys.stdin)["smtpPassword"] == "synthetic-smtp-pass")')" == True ]]; then
    echo "smtpPassword: taken over (not printed)"
else
    echo "FAIL smtpPassword not taken over"; exit 1
fi

step "synthetic records: an account and a document with a file"
api POST Account "{\"name\": \"Synthetic test account A $run\"}" | id_of
att="$(api POST Attachment "{\"name\": \"synthetic.txt\", \"type\": \"text/plain\", \"role\": \"Attachment\",
      \"relatedType\": \"Document\", \"field\": \"file\",
      \"file\": \"data:text/plain;base64,$(printf 'synthetic test file\n' | base64 -w0)\"}" | id_of)"
api POST Document "{\"name\": \"Synthetic document $run\", \"fileId\": \"$att\"}" | id_of
ls /var/www/espocrm/data/upload | wc -l

step "bundle t1 and its fingerprint"
bundle="$(espocrm-backup --label t1)"
echo "bundle: $(basename "$bundle")"
fp_a="$(espocrm-fingerprint take t1)"

step "change after the bundle, changes since"
sleep 1
since="$(date -u '+%Y-%m-%d %H:%M:%S')"
sleep 1
api POST Account "{\"name\": \"Synthetic test account B $run\"}" | id_of
espocrm-changes-since "$since" --export
# The list holds ids, links and times only: names of records never get into it.
list="$(ls -t /var/backups/espocrm/changes-*.tsv | head -1)"
if grep -q "Synthetic" "$list"; then echo "FAIL the list of changes holds values"; exit 1; fi
echo "list of changes: $(($(wc -l <"$list") - 1)) rows, no values"

step "restore of t1"
espocrm-restore "$bundle" --yes
fp_b="$(espocrm-fingerprint take after-restore)"
[[ "$fp_a" == "$fp_b" ]] && echo "fingerprint after the restore equals the bundle: ${fp_a:0:16}" \
    || { espocrm-fingerprint diff "$(ls -t /var/backups/espocrm/fingerprints/*-t1.json | head -1)" \
            "$(ls -t /var/backups/espocrm/fingerprints/*-after-restore.json | head -1)" || true; exit 1; }

step "changes against the bundle (links, hard deletes and columns without a timestamp included)"
api POST Account "{\"name\": \"Synthetic test account C $run\"}" | id_of
# A change of a column that leaves modified_at as it was (like 2FA of user_data or optOut of email_address).
mysql "$DB_NAME" -e "UPDATE account SET description = 'synthetic change' WHERE name = 'Synthetic test account A $run'"
espocrm-changes-since --against "$bundle" --export | tee /tmp/against.txt
grep -E '^account +1 +0 +1$' /tmp/against.txt || { echo "FAIL account: 1 added and 1 changed expected"; exit 1; }
list="$(ls -t /var/backups/espocrm/changes-*.tsv | head -1)"
if grep -q "Synthetic\|synthetic change" "$list"; then echo "FAIL the list of changes holds values"; exit 1; fi
echo "changes against the bundle: account added 1, changed 1; list without values"

step "a restore failing inside the files phase, then the printed rollback"
fp_before="$(espocrm-fingerprint take before-failed-restore)"
bad="/var/backups/espocrm/bundles/$(basename "$bundle")-broken"
cp -a "$bundle" "$bad"
head -c 2000 "$bundle/files.tar.gz" >"$bad/files.tar.gz"
( cd "$bad" && sha256sum db.sql.gz files.tar.gz table-counts.tsv MANIFEST >SHA256SUMS )
if espocrm-restore "$bad" --yes >/tmp/failed-restore.log 2>&1; then echo "the broken bundle was restored"; exit 1; fi
grep -E "FAILED in phase" /tmp/failed-restore.log
systemctl is-active espocrm-php-fpm || true
ls /etc/cron.d/espocrm.paused
rollback="$(sed -n 's/.*Roll back with: //p' /tmp/failed-restore.log)"
echo "rollback: ${rollback%% --server-config*} --server-config …"
eval "$rollback"
if [[ "$(espocrm-fingerprint take after-rollback)" == "$fp_before" ]]; then
    echo "fingerprint after the rollback equals the state before the failed restore"
else
    echo "FAIL fingerprint after the rollback differs"; exit 1
fi
for f in custom/Espo/Modules/Itvolga/Resources/module.json client/custom/modules/itvolga/src; do
    [[ -e "/var/www/espocrm/$f" ]] || { echo "FAIL the module is gone after the rollback: $f"; exit 1; }
done
echo "module in place after the failed restore and the rollback"
rm -rf "$bad"
# The failed run keeps its previous tables and directories on purpose (manual rollback); drop them once rolled back.
for d in $(mysql -N -B -e "SHOW DATABASES LIKE 'espocrm\_\_prev\_%'"); do mysql -e "DROP DATABASE \`$d\`"; done
rm -rf /var/backups/espocrm/.restore-aside-*

step "the module cannot be renamed away by the EspoCRM user"
if runuser -u espocrm -- mv /var/www/espocrm/custom/Espo/Modules/Itvolga /var/www/espocrm/custom/Espo/Modules/X 2>/dev/null; then
    echo "renamed"; exit 1
fi
runuser -u espocrm -- touch /var/www/espocrm/custom/Espo/Modules/.probe && rm -f /var/www/espocrm/custom/Espo/Modules/.probe
echo "rename refused, writing the parent allowed"

step "fail2ban: the login journal and the filter"
curl -s -o /dev/null --resolve serv.itvolga.com:8443:127.0.0.1 --cacert /etc/espocrm-test/ca.pem \
    -H "Espo-Authorization: $(printf 'admin:wrong-%s' "$run" | base64 -w0)" https://serv.itvolga.com:8443/api/v1/App/user
tail -1 /var/log/apache2/espocrm_auth.log | sed -E 's/^[0-9.]+/<ip>/'
printf '%s\n' '127.0.0.1 [17/Oct/2026:18:00:00 +0000] "GET /api/v1/App/user HTTP/1.1" 401 "second-step-required"' \
    '127.0.0.1 [17/Oct/2026:18:00:01 +0000] "GET /api/v1/App/user HTTP/1.1" 401 "-"' >/tmp/auth-sample.log
tail -1 /var/log/apache2/espocrm_auth.log >>/tmp/auth-sample.log
f2b="$(fail2ban-regex /tmp/auth-sample.log /etc/fail2ban/filter.d/espocrm-auth.conf | grep -E '^Lines: ')"
echo "$f2b"
[[ "$f2b" == *" 2 matched, 1 missed"* ]] || { echo "FAIL the filter must count the wrong passwords only"; exit 1; }
fail2ban-client status espocrm-auth | grep -E 'Currently failed|File list'

step "restore check of the bundle"
espocrm-restore-check "$bundle"

step "restic tiers db (with the nightly EspoCRM bundle) and recordings, local remote"
/usr/local/sbin/backup-run db
/usr/local/sbin/backup-run recordings
ls /var/backups/espocrm/nightly

step "restore check from restic, with the recordings"
espocrm-restore-check --from-restic --recordings

step "restore of a stand-format bundle (origin stand: data/ only, the server-owned configuration kept)"
stand="/var/backups/espocrm/bundles/$(basename "$bundle")-standformat"
cp -a "$bundle" "$stand"
sed -i -e '/^origin=/d' -e '/^host=/d' "$stand/MANIFEST"
( cd "$stand" && sha256sum db.sql.gz files.tar.gz table-counts.tsv MANIFEST >SHA256SUMS )
espocrm-restore "$stand" --yes --no-safety-backup
fp_c="$(espocrm-fingerprint take after-stand-format)"
if [[ "$fp_c" == "$fp_a" ]]; then echo "fingerprint after the stand-format restore equals the bundle"
else echo "FAIL fingerprint after the stand-format restore differs"; exit 1; fi
espocrm-health

step "calls of the listener carried over a restore (cutover runbook, step 5)"
admin="$(mysql -N -B "$DB_NAME" -e "SELECT id FROM user WHERE user_name = 'admin' AND deleted = 0")"
now() { date -u '+%Y-%m-%d %H:%M:%S'; }
lid="synthetic-$run"
call_sql() { # id status linked-id [date_end]
    printf "INSERT INTO \`call\` (id, name, deleted, status, direction, date_start, date_end, created_at, modified_at,
        assigned_user_id, c_asterisk_linked_id) VALUES ('%s', 'Synthetic call', 0, '%s', 'Inbound', '%s', %s, '%s', '%s',
        '%s', '%s');" "$1" "$2" "$(now)" "${4:-NULL}" "$(now)" "$(now)" "$admin" "$3"
}
# Y: a live call unfinished when the pre-delta bundle is taken; W: a call the bundle holds from the CDR history.
mysql "$DB_NAME" -e "$(call_sql "synthy$run" Planned "$lid.1") $(call_sql "synthw$run" Held "$lid.3" "'$(now)'")"
predelta="$(espocrm-backup --label pre-delta)"
sleep 1
# After the bundle: Y ends (silently: modified_at stays), X starts and ends with a participant, and V is the live
# record of the Asterisk call W stands for (the bundle keeps W).
mysql "$DB_NAME" -e "UPDATE \`call\` SET status = 'Held', date_end = '$(now)' WHERE id = 'synthy$run';
    $(call_sql "synthx$run" Held "$lid.2" "'$(now)'")
    INSERT INTO call_user (call_id, user_id, status, deleted) VALUES ('synthx$run', '$admin', 'Accepted', 0);
    DELETE FROM \`call\` WHERE id = 'synthw$run'; $(call_sql "synthv$run" Held "$lid.3" "'$(now)'")"
espocrm-restore "$predelta" --yes --carry-calls-from "$(basename "$predelta")" 2>&1 | tee /tmp/carry-restore.log
grep -E 'put back: [0-9]+; skipped .*: 1$' /tmp/carry-restore.log >/dev/null \
    || { echo "FAIL the record of a call the bundle holds from the CDR history must be skipped"; exit 1; }
got="$(mysql -N -B "$DB_NAME" -e "SELECT
    (SELECT COUNT(*) FROM \`call\` WHERE c_asterisk_linked_id IN ('$lid.1', '$lid.2') AND date_end IS NOT NULL AND deleted = 0),
    (SELECT COUNT(*) FROM call_user WHERE call_id = 'synthx$run' AND deleted = 0),
    (SELECT GROUP_CONCAT(id) FROM \`call\` WHERE c_asterisk_linked_id = '$lid.3')")"
[[ "$got" == "2"$'\t'"1"$'\t'"synthw$run" ]] || { echo "FAIL calls after the restore: $got"; exit 1; }
echo "calls carried: the call started and ended after the bundle, the end of the unfinished one; the CDR record kept"
if ls /var/lib/espocrm/carry-calls-* >/dev/null 2>&1; then echo "FAIL the kept calls file remains"; exit 1; fi
mysql "$DB_NAME" -e "DELETE FROM call_user WHERE call_id LIKE 'synth_$run';
    DELETE FROM \`call\` WHERE id IN ('synthx$run', 'synthy$run', 'synthw$run', 'synthv$run')"
rm -rf "$predelta"

step "leftovers"
mysql -N -B -e "SHOW DATABASES LIKE 'espocrm\_\_%'" | wc -l
SCENARIO
    then
        tail -60 "$LOGS/verify.log" >&2
        die "scenario failed, log $LOGS/verify.log"
    fi
    grep -E '^(=== |FAIL|WARN|health:|restore check:|fingerprint|bundle:|rollback:|rename|Lines:|changes against|\{.smtp|smtpPassword|list of changes|module in place|calls carried)' \
        "$LOGS/verify.log" | sed 's/^/    /' >&2
}

# Live telephony against the Asterisk of the target: AMI users (manager reload), listener, rights self-test.
telephony() {
    inventory
    playbook 11-espocrm.yml telephony-on -e espocrm_telephony_enabled=true
    playbook 11-espocrm.yml telephony-idempotent -e espocrm_telephony_enabled=true
    assert_unchanged telephony-idempotent
    # A run interrupted after the settings and the AMI file changed but before the listener restarted: the applied
    # state still names the old ones, so the next run applies, reloads and restarts.
    in_target "$CONTAINER" sed -i -E 's/"(settings|ami)": "[0-9a-f]+"/"\1": "stale"/g' /var/lib/espocrm/telephony-applied.json
    playbook 11-espocrm.yml telephony-resume -e espocrm_telephony_enabled=true
    assert_task_changed telephony-resume "Apply the telephony settings of EspoCRM"
    assert_task_changed telephony-resume "Reload the Asterisk manager after a change of the AMI users"
    assert_task_changed telephony-resume "Set the state of the AMI listener"
    log "telephony: an unfinished apply resumed (settings, manager reload, listener restart)"
    playbook 11-espocrm.yml telephony-resume-again -e espocrm_telephony_enabled=true
    assert_unchanged telephony-resume-again
    in_target "$CONTAINER" bash -c 'espocrm itvolga-setup-telephony --check; asterisk -rx "manager show users";
        systemctl is-active espocrm-telephony; espocrm-health | grep -E "telephony|health:"' \
        >"$LOGS/telephony-check.log" 2>&1
    sed 's/^/    /' "$LOGS/telephony-check.log" >&2
    # The AMI users the role renders = the example the stand's test PBX was verified with (stage 07.1), secrets aside.
    local listener dialer ph_l=example_listener_secret ph_d=example_dialer_secret
    listener="$(vault_value vault_espocrm_ami_listener_secret)"
    dialer="$(vault_value vault_espocrm_ami_dialer_secret)"
    if docker exec "$CONTAINER" cat /etc/asterisk/manager.d/itvolga-espo.conf | tail -n +2 \
            | sed -e "s/^secret = $listener\$/secret = ${ph_l}/" -e "s/^secret = $dialer\$/secret = ${ph_d}/" \
            | diff -q - "$REPO/deploy/production/telephony/manager.d-itvolga-espo.conf.example" >/dev/null; then
        log "AMI users file = deploy/production/telephony/manager.d-itvolga-espo.conf.example (secrets aside)"
    else
        die "the AMI users file of the role differs from the example of stage 07.1"
    fi
    playbook 11-espocrm.yml telephony-off -e espocrm_telephony_enabled=false
    in_target "$CONTAINER" bash -c 'test ! -e /etc/asterisk/manager.d/itvolga-espo.conf && ! systemctl is-active --quiet espocrm-telephony' \
        || die "telephony off: the AMI users or the listener remain"
    log "telephony off: AMI users removed, listener stopped"
    playbook 11-espocrm.yml telephony-back   # the default: live telephony from stage 10 on (Q-56)
}

# The switch of serv.itvolga.com: maintenance → espocrm → rollback to vtiger, each with its checks and a repeat.
switch() {
    inventory
    local auth
    auth="$(vault_value vault_serv_itvolga_auth_user):$(vault_value vault_serv_itvolga_auth_password)"
    local mode
    for mode in maintenance espocrm vtiger; do
        playbook 12-crm-switch.yml "switch-$mode" -e "itvolga_crm_primary=$mode"
        playbook 12-crm-switch.yml "switch-$mode-again" -e "itvolga_crm_primary=$mode"
        assert_unchanged "switch-$mode-again"
        AUTH="$auth" in_target -e AUTH "$CONTAINER" bash -s "$mode" >"$LOGS/switch-$mode-check.log" 2>&1 <<'CHECK'
set -euo pipefail
mode="$1"
code() { curl -s -o /dev/null -w '%{http_code}' --resolve serv.itvolga.com:443:127.0.0.1 --cacert /etc/espocrm-test/ca.pem "$@"; }
body() { curl -s --resolve serv.itvolga.com:443:127.0.0.1 --cacert /etc/espocrm-test/ca.pem "$@"; }
vt="$(body -u "$AUTH" https://serv.itvolga.com/ | grep -c vtiger-fixture || true)"
espo="$(body https://serv.itvolga.com/ | grep -c loader-params || true)"
echo "public / without credentials: $(code https://serv.itvolga.com/); with Basic: $(code -u "$AUTH" https://serv.itvolga.com/)"
echo "Vtiger marker: $vt; EspoCRM page: $espo; preview: $(code https://serv.itvolga.com:8443/ --resolve serv.itvolga.com:8443:127.0.0.1)"
echo "vtiger cron: $(grep -c '^#.*vtiger-cron' /etc/cron.d/vtiger || true) commented"
case "$mode" in
    vtiger) [[ "$vt" == 1 && "$espo" == 0 && "$(code https://serv.itvolga.com/)" == 401 ]] ;;
    maintenance) [[ "$(code https://serv.itvolga.com/)" == 503 && "$vt" == 0 ]] ;;
    espocrm) [[ "$espo" == 1 && "$vt" == 0 ]] ;;
esac
espocrm-health | tail -1
CHECK
        sed 's/^/    /' "$LOGS/switch-$mode-check.log" >&2
    done
}

# Continuous deployment (D-194): the forced command of the CD key → sudo → espocrm-deploy against a bare repository in
# the target that plays GitHub (espocrm_cd_repo_url of zz-test.yml), and the guard of the role against going back.
cd_step() {
    inventory
    local head prev
    head="$(git -C "$REPO" rev-parse HEAD)"
    prev="$(git -C "$REPO" rev-parse HEAD~1)"
    playbook 11-espocrm.yml cd-start -e espocrm_module_allow_downgrade=true   # the module of HEAD (a repeated step)
    playbook_fails 11-espocrm.yml cd-guard-older "продолжение" -e espocrm_module_ref=HEAD~1
    playbook 11-espocrm.yml cd-downgrade -e espocrm_module_ref=HEAD~1 -e espocrm_module_allow_downgrade=true
    git -C "$REPO" bundle create "$RUN/cd.bundle" HEAD >/dev/null 2>&1
    docker cp "$RUN/cd.bundle" "$CONTAINER:/root/cd.bundle" >/dev/null
    log "CD scenario on the target (requests, main only, pause, deploy of the role's commit) → $LOGS/cd-1.log"
    in_target -e HEAD_COMMIT="$head" -e PREV_COMMIT="$prev" "$CONTAINER" bash -s >"$LOGS/cd-1.log" 2>&1 <<'SCENARIO' \
        || { tail -30 "$LOGS/cd-1.log" >&2; die "CD scenario 1 failed, log $LOGS/cd-1.log"; }
set -euo pipefail
source /etc/espocrm/espocrm.env
step() { printf '\n=== %s\n' "$*"; }
ssh_cmd() { runuser -u espocrm-deploy -- env SSH_ORIGINAL_COMMAND="$1" "$LIB_DIR/espocrm-deploy-ssh"; }
refused() { # expected-text request
    local out rc=0
    out="$(ssh_cmd "$2" 2>&1)" || rc=$?
    printf '%s\n' "$out"
    [[ $rc != 0 ]] || { echo "UNEXPECTED: '$2' succeeded"; exit 1; }
    grep -qF "$1" <<<"$out" || { echo "UNEXPECTED: '$2' failed without '$1'"; exit 1; }
}
commit_as_test() { git -C "$1" -c user.name=cd-test -c user.email=cd-test commit -q "${@:2}"; }

step "Status before the first deploy"
espocrm-deploy --resume >/dev/null   # no pause or hold left by an earlier interrupted run of this step
rm -rf "$STATE_DIR/deploy"
status="$(espocrm-deploy --status)"
printf '%s\n' "$status"
grep -q "^last CD log: none" <<<"$status"

step "GitHub of the test: $CD_REPO_URL, main = the commit of the role"
rm -rf "$CD_REPO_URL"
git init -q --bare --initial-branch=main "$CD_REPO_URL"
git -C "$CD_REPO_URL" fetch -q /root/cd.bundle "HEAD:refs/heads/main"

step "Requests the forced command refuses (nothing reaches sudo)"
refused "the only accepted command" ""
refused "the only accepted command" "id"
refused "the only accepted command" "deploy ${HEAD_COMMIT:0:12}"
refused "the only accepted command" "deploy $HEAD_COMMIT; id"
refused "the only accepted command" "deploy $HEAD_COMMIT --pause"
[[ "$(cat "$ESPO_ROOT/.itvolga-module")" == "$PREV_COMMIT" ]]

step "Commits outside main are refused"
work="$(mktemp -d)"
git clone -q "$CD_REPO_URL" "$work"
commit_as_test "$work" --allow-empty -m "side branch"
side="$(git -C "$work" rev-parse HEAD)"
git -C "$work" push -q origin HEAD:refs/heads/side
refused "is not on the branch main" "deploy $side"
refused "is not on the branch main" "deploy 0123456789abcdef0123456789abcdef01234567"

step "Paused deploys are refused; the reason stays on the server"
espocrm-deploy --pause "private-sentinel-7"
out="$(ssh_cmd "deploy $HEAD_COMMIT" 2>&1)" && { echo "UNEXPECTED: deployed while paused"; exit 1; }
printf '%s\n' "$out"
grep -q "deploys are paused" <<<"$out" && ! grep -q "private-sentinel-7" <<<"$out"
grep -q "private-sentinel-7" <<<"$(espocrm-deploy --status)"   # no early exit of grep -q into a pipe
espocrm-deploy --resume

step "A run of the role holds deploys; a hold older than 2 h is ignored"
date -u +%s >"$STATE_DIR/deploy-held-by-role"
refused "a run of the role espocrm holds deploys" "deploy $HEAD_COMMIT"
echo 1 >"$STATE_DIR/deploy-held-by-role"
espocrm-deploy --status

step "Deploy of the commit of the role through the forced command and sudo"
out="$(ssh_cmd "deploy $HEAD_COMMIT")"
printf '%s\n' "$out"
grep -q "applied yes" <<<"$out"
grep -q "^health: 0 failed" <<<"$out"
grep -q "a hold older than 2 h" <<<"$out"
[[ "$(wc -l <<<"$out")" -le 6 ]]   # summary lines only; the full log stays on the server
[[ "$(cat "$ESPO_ROOT/.itvolga-module")" == "$HEAD_COMMIT" ]]
grep -q " $HEAD_COMMIT\$" "$STATE_DIR/apply-applied"
test ! -e "$STATE_DIR/apply-pending"
test -s "$(find "$STATE_DIR/deploy/logs" -name '*.log' | LC_ALL=C sort | tail -1)"
SCENARIO
    sed -n 's/^=== /    /p' "$LOGS/cd-1.log" >&2
    # After a deploy by CD the role (same commit) changes nothing: same archive bytes, staging, stamp, applied state.
    playbook 11-espocrm.yml cd-role-after
    assert_unchanged cd-role-after
    log "CD scenario on the target (a module change, repeat, older commit, revert) → $LOGS/cd-2.log"
    in_target -e HEAD_COMMIT="$head" "$CONTAINER" bash -s >"$LOGS/cd-2.log" 2>&1 <<'SCENARIO' \
        || { tail -30 "$LOGS/cd-2.log" >&2; die "CD scenario 2 failed, log $LOGS/cd-2.log"; }
set -euo pipefail
source /etc/espocrm/espocrm.env
step() { printf '\n=== %s\n' "$*"; }
ssh_cmd() { runuser -u espocrm-deploy -- env SSH_ORIGINAL_COMMAND="$1" "$LIB_DIR/espocrm-deploy-ssh"; }
commit_as_test() { git -C "$1" -c user.name=cd-test -c user.email=cd-test commit -q "${@:2}"; }
marker=client/custom/modules/itvolga/cd-test.txt
refused() { # expected-text request
    local out rc=0
    out="$(ssh_cmd "$2" 2>&1)" || rc=$?
    printf '%s\n' "$out"
    [[ $rc != 0 ]] || { echo "UNEXPECTED: '$2' succeeded"; exit 1; }
    grep -qF "$1" <<<"$out" || { echo "UNEXPECTED: '$2' failed without '$1'"; exit 1; }
}

step "The role released its hold at its end"
test ! -e "$STATE_DIR/deploy-held-by-role"

step "A new commit of main that changes the module: backup, files, apply, health"
work="$(mktemp -d)"
git clone -q "$CD_REPO_URL" "$work"
printf 'cd test\n' >"$work/$marker"
git -C "$work" add "$marker"
commit_as_test "$work" -m "cd test: a module change"
new="$(git -C "$work" rev-parse HEAD)"
git -C "$work" push -q origin HEAD:refs/heads/main
out="$(ssh_cmd "deploy $new")"
printf '%s\n' "$out"
grep -q "files changed [1-9][0-9]*, applied yes, backup [0-9T]*-deploy-${new:0:12}\$" <<<"$out"
grep -q "^health: 0 failed" <<<"$out"
[[ "$(stat -c '%U:%G %a' "$ESPO_ROOT/$marker")" == "root:root 644" ]]
[[ "$(cat "$ESPO_ROOT/.itvolga-module")" == "$new" ]]
grep -q " $new\$" "$STATE_DIR/apply-applied"
test ! -e "$STATE_DIR/apply-pending"
[[ "$(find "$OPT_DIR/module" -mindepth 1 -maxdepth 1 | wc -l)" == 3 ]]   # the staging copy, its mark and the archive
bundle="$(find "$BACKUP_DIR/bundles" -mindepth 1 -maxdepth 1 -name "*-deploy-${new:0:12}" | tail -1)"
( cd "$bundle" && sha256sum -c --quiet SHA256SUMS )
grep -qx "git_head=$HEAD_COMMIT" "$bundle/MANIFEST"   # the state before the deploy

step "The same commit again: nothing to do"
out="$(ssh_cmd "deploy $new")"
printf '%s\n' "$out"
grep -q "files changed 0, applied no, backup none\$" <<<"$out"

step "An older commit of main is refused"
rc=0; out="$(ssh_cmd "deploy $HEAD_COMMIT" 2>&1)" || rc=$?
printf '%s\n' "$out"
[[ $rc != 0 ]] && grep -q "older than the deployed" <<<"$out"

step "Rollback the CD way: git revert on main"
git -C "$work" -c user.name=cd-test -c user.email=cd-test revert --no-edit HEAD >/dev/null
reverted="$(git -C "$work" rev-parse HEAD)"
git -C "$work" push -q origin HEAD:refs/heads/main
out="$(ssh_cmd "deploy $reverted")"
printf '%s\n' "$out"
grep -q "files changed [1-9][0-9]*, applied yes" <<<"$out"
test ! -e "$ESPO_ROOT/$marker"
[[ "$(cat "$ESPO_ROOT/.itvolga-module")" == "$reverted" ]]

step "Symbolic links in the module, and in place of a module directory, are refused"
ln -s /etc "$work/client/custom/modules/itvolga/etc-link"
git -C "$work" add client/custom/modules/itvolga/etc-link
commit_as_test "$work" -m "cd test: a symbolic link in the module"
git -C "$work" push -q origin HEAD:refs/heads/main
refused "symbolic links or submodules in the module" "deploy $(git -C "$work" rev-parse HEAD)"
git -C "$work" rm -q -r client/custom/modules/itvolga
ln -s /etc "$work/client/custom/modules/itvolga"
git -C "$work" add client/custom/modules/itvolga
commit_as_test "$work" -m "cd test: a symbolic link in place of the module"
git -C "$work" push -q origin HEAD:refs/heads/main
refused "client/custom/modules/itvolga is not a directory" "deploy $(git -C "$work" rev-parse HEAD)"
test ! -e "$ESPO_ROOT/client/custom/modules/itvolga/etc-link" && test ! -e "$ESPO_ROOT/client/custom/modules/itvolga/passwd"
[[ "$(cat "$ESPO_ROOT/.itvolga-module")" == "$reverted" ]]
SCENARIO
    sed -n 's/^=== /    /p' "$LOGS/cd-2.log" >&2
    # The deployed revert is unknown to the controller: the role refuses until git pull or an explicit rollback.
    playbook_fails 11-espocrm.yml cd-guard-unknown "неизвестен"
    playbook 11-espocrm.yml cd-back -e espocrm_module_allow_downgrade=true
    playbook 11-espocrm.yml cd-back-again
    assert_unchanged cd-back-again
    [[ "$(docker exec "$CONTAINER" cat /var/www/espocrm/.itvolga-module)" == "$head" ]] \
        || die "cd: the role did not bring the module back to $head"
    log "cd: forced command, main only, pause, role hold, symbolic links, deploys with backup, revert; the role guards and converges back"
}

down() {
    docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
    rm -rf "$RUN"
    log "target removed (image $IMAGE kept)"
}

cmd="${1:-all}"
case "$cmd" in
    all) up; prepare; converge; idempotent; check; drift; verify; telephony; switch; cd_step ;;
    up|prepare|converge|idempotent|check|drift|verify|telephony|switch|down) "$cmd" ;;
    cd) cd_step ;;
    shell) docker exec -it "$CONTAINER" bash ;;
    *) die "usage: test-target.sh all|up|prepare|converge|idempotent|check|drift|verify|telephony|switch|cd|down|shell" ;;
esac
