#!/usr/bin/env bash
# Disposable test target of the server Ansible with the role espocrm (stage 09, D-180): a container of Ubuntu 26.04
# (the release of production) with systemd, reached over the Docker connection. Production is never contacted.
#
#   test-target.sh all          up → prepare → converge → idempotent → check → verify → telephony → switch
#   test-target.sh up | prepare | converge | idempotent | check | verify | telephony | switch | down | shell
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

step "restore of t1"
espocrm-restore "$bundle" --yes
fp_b="$(espocrm-fingerprint take after-restore)"
[[ "$fp_a" == "$fp_b" ]] && echo "fingerprint after the restore equals the bundle: ${fp_a:0:16}" \
    || { espocrm-fingerprint diff "$(ls -t /var/backups/espocrm/fingerprints/*-t1.json | head -1)" \
            "$(ls -t /var/backups/espocrm/fingerprints/*-after-restore.json | head -1)" || true; exit 1; }

step "changes against the bundle (links and hard deletes included)"
api POST Account "{\"name\": \"Synthetic test account C $run\"}" | id_of
espocrm-changes-since --against "$bundle"

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

step "leftovers"
mysql -N -B -e "SHOW DATABASES LIKE 'espocrm\_\_%'" | wc -l
SCENARIO
    then
        tail -60 "$LOGS/verify.log" >&2
        die "scenario failed, log $LOGS/verify.log"
    fi
    grep -E '^(=== |FAIL|WARN|health:|restore check:|fingerprint|bundle:|rollback:|rename|Lines:|changes against)' \
        "$LOGS/verify.log" | sed 's/^/    /' >&2
}

# Live telephony against the Asterisk of the target: AMI users (manager reload), listener, rights self-test.
telephony() {
    inventory
    playbook 11-espocrm.yml telephony-on -e espocrm_telephony_enabled=true
    playbook 11-espocrm.yml telephony-idempotent -e espocrm_telephony_enabled=true
    assert_unchanged telephony-idempotent
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
    playbook 11-espocrm.yml telephony-off
    in_target "$CONTAINER" bash -c 'test ! -e /etc/asterisk/manager.d/itvolga-espo.conf && ! systemctl is-active --quiet espocrm-telephony' \
        || die "telephony off: the AMI users or the listener remain"
    log "telephony off: AMI users removed, listener stopped"
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

down() {
    docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
    rm -rf "$RUN"
    log "target removed (image $IMAGE kept)"
}

cmd="${1:-all}"
case "$cmd" in
    all) up; prepare; converge; idempotent; check; verify; telephony; switch ;;
    up|prepare|converge|idempotent|check|verify|telephony|switch|down) "$cmd" ;;
    shell) docker exec -it "$CONTAINER" bash ;;
    *) die "usage: test-target.sh all|up|prepare|converge|idempotent|check|verify|telephony|switch|down|shell" ;;
esac
