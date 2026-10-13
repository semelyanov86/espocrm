"""Stage 07.1 acceptance harness: the isolated test PBX of the stand (deploy/telephony, `task telephony:up`) and the
synthetic CRM side of the tests.

- The PBX is driven through `docker exec … asterisk -rx`: AstDB keys tell the simulated desk phones and providers how
  to behave, Local channels place inbound calls (provider → PBX) and desk calls (phone → PBX).
- Users, teams, roles and clients are synthetic (tag SYNTH-TEL-<run>); extensions 111/116/118/119/218 of the test PBX
  must be free among the active users of the stand (the real ones hold 100–110, 205–208); external numbers are a
  random block +7 999 <4 digits> <3 digits> checked to be unknown to the stand first.
- Cleanup removes exactly what the run made: its users, teams, roles and clients through the API (registered ids), and
  the calls of its numbers with their relations, cards, click-to-call requests, Action History rows and recording
  files by id (the listener creates the calls, so their ids are found by the run's own numbers).
"""
import fcntl
import json
import re
import secrets
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "stage03"))

from espo import REPO, Client, admin_credentials, espo_console, sql  # noqa: E402

PROJECT = "itvolga-espo-telephony"
MONITOR = Path("/var/lib/itvolga-espo/telephony/monitor")
LINE = "290001"
EXTENSIONS = ("111", "116", "118", "119", "218")
LOCK = Path("/tmp/itvolga-stage07_1.lock")
SAFE_RECORDING = re.compile(r"^[0-9]{4}/[0-9]{2}/[0-9]{2}/[^/.\\][^/\\]*\.wav$")


def must(result, what):
    status, payload, _ = result
    if status != 200:
        raise AssertionError(f"{what}: HTTP {status}")
    return payload


# --- test PBX ---------------------------------------------------------------------------------------------------

def ast(container, command):
    return subprocess.run(["docker", "exec", f"{PROJECT}-{container}-1", "asterisk", "-rx", command],
                          check=True, capture_output=True, text=True).stdout


def phone(ext, behaviour):
    """answer,<ring s>,<talk s> | busy | noanswer"""
    ast("phones", f"database put phone {ext} {behaviour}")


def provider(number, behaviour):
    ast("pstn", f"database put pstn {number.lstrip('+')} {behaviour}")


def inbound(caller, hold):
    """A provider call from <caller> to the office line; the caller hangs up <hold> s after the PBX answers."""
    ast("pstn", f"channel originate Local/{caller}*{LINE}@call-pbx application Wait {hold}")


def desk(ext, number, hold):
    """Desk phone <ext> dials <number>; it hangs up <hold> s after the far end answers."""
    ast("phones", f"channel originate Local/{ext}*{number}@desk application Wait {hold}")


def last_provider_call():
    """(route, called) of the last outbound call the providers got: the PBX trunk's from_user and the number."""
    out = ast("pstn", "database show last")
    values = dict(re.findall(r"/last/(\w+)\s*:\s*(\S+)", out))
    return values.get("route"), values.get("called")


def reset_pbx():
    for container, family in (("phones", "phone"), ("pstn", "pstn"), ("pstn", "last")):
        ast(container, f"database deltree {family}")


def active_channels():
    out = ast("pbx", "core show channels count")
    m = re.search(r"(\d+) active channel", out)
    return int(m.group(1)) if m else -1


def wait_idle(timeout=90):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if active_channels() == 0:
            return
        time.sleep(1)
    raise AssertionError("the test PBX still has channels")


def listener_state():
    out = subprocess.run(["sudo", "-n", "cat", str(REPO / "data/itvolga-telephony-status.json")],
                         capture_output=True, text=True)
    try:
        return json.loads(out.stdout).get("state")
    except ValueError:
        return None


def wait(predicate, timeout, what):
    deadline = time.time() + timeout
    while time.time() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(0.5)
    raise AssertionError(f"timeout: {what}")


# --- CRM side ---------------------------------------------------------------------------------------------------

class Run:
    """Synthetic users, records and numbers of one test run."""

    def __init__(self):
        self._lock = open(LOCK, "w")
        fcntl.flock(self._lock, fcntl.LOCK_EX)
        if listener_state() != "connected":
            raise AssertionError("the telephony is not up: task telephony:up")
        self.run_id = secrets.token_hex(3)
        self.tag = f"SYNTH-TEL-{self.run_id}"
        self.admin = Client(*admin_credentials())
        self.created = []
        self.uid, self.clients, self.passwords = {}, {}, {}
        self.t0 = sql("SELECT UTC_TIMESTAMP()")[0][0]
        self.block = self._free_block()
        busy = sql("SELECT COUNT(*) FROM user WHERE deleted = 0 AND is_active = 1 AND c_phone_extension IN ("
                   + ",".join(f"'{e}'" for e in EXTENSIONS) + ")")[0][0]
        if busy != "0":
            raise AssertionError("an active user of the stand already has an extension of the test PBX")
        self.roles = {r["name"]: r["id"] for r in must(self.admin.get("Role", maxSize=200), "roles")["list"]}
        self.settings_before = must(self.admin.get("Settings"), "settings").get("itvolgaTelephonyFallbackExtension")
        must(self.admin.put("Settings", {"itvolgaTelephonyFallbackExtension": "119"}), "fallback extension")

    @staticmethod
    def _free_block():
        for _ in range(20):
            block = f"7999{secrets.randbelow(10000):04d}"
            used = sql(f"SELECT COUNT(*) FROM phone_number WHERE `numeric` LIKE '%{block[1:]}%'")[0][0]
            if used == "0":
                return block
        raise AssertionError("no free synthetic number block")

    def number(self, n):
        """Caller-id form (11 digits, as trunk-russia delivers it)."""
        return f"{self.block}{n:03d}"

    def canonical(self, n):
        return "+" + self.number(n)

    # registry
    def register(self, entity, rid):
        self.created.append((entity, rid))
        return rid

    def create(self, entity, data, by=None):
        payload = must((by or self.admin).post(entity, data), f"create {entity}")
        return self.register(entity, payload["id"])

    def team(self, key):
        return self.create("Team", {"name": f"{self.tag} {key}"})

    def role(self, key, data, field_data=None):
        return self.create("Role", {"name": f"{self.tag} {key}", "data": data, "fieldData": field_data or {}})

    def user(self, key, roles=(), role_ids=(), teams=(), extension=None):
        password = secrets.token_urlsafe(18) + "Aa1!"
        data = {"userName": f"synth-tel-{self.run_id}-{key}", "firstName": "Телефония", "lastName": f"{self.tag} {key}",
                "type": "regular", "isActive": True, "password": password, "passwordConfirm": password,
                "rolesIds": [self.roles[r] for r in roles] + list(role_ids), "teamsIds": list(teams),
                "sendAccessInfo": False}
        if teams:
            data["defaultTeamId"] = teams[0]
        if extension:
            data["cPhoneExtension"] = extension
        uid = self.create("User", data)
        self.uid[key] = uid
        self.passwords[key] = password
        self.clients[key] = Client(data["userName"], password)
        return self.clients[key]

    # calls of the run
    def call_rows(self, where=""):
        cols = ["id", "c_asterisk_linked_id", "direction", "status", "c_live_state", "c_call_status_raw",
                "c_bill_duration", "c_extension", "assigned_user_id", "parent_type", "parent_id", "c_recording",
                "c_recording_path", "c_phone_number", "c_incoming_line", "c_click_to_call", "deleted",
                "TIMESTAMPDIFF(SECOND, date_start, date_end)"]
        rows = sql(f"SELECT {', '.join(cols)} FROM `call` WHERE c_phone_number LIKE '+{self.block}%' "
                   f"AND created_at >= '{self.t0}' {where} ORDER BY created_at")
        keys = [c if " " not in c and "(" not in c else "length" for c in cols]
        return [dict(zip(keys, row)) for row in rows]

    def final_call(self, n, timeout=90):
        """The finished Call of number n (exactly one)."""
        number = self.canonical(n)

        def done():
            rows = [r for r in self.call_rows() if r["c_phone_number"] == number]
            return rows if rows and all(r["c_live_state"] in ("ended", "lost") for r in rows) else None

        rows = wait(done, timeout, f"finished call of number {n}")
        if len(rows) != 1:
            raise AssertionError(f"{len(rows)} calls for one number")
        return rows[0]

    def related(self, table, call_id, column):
        return sorted(r[0] for r in sql(f"SELECT {column} FROM {table} WHERE call_id = '{call_id}' AND deleted = 0"))

    def cards(self, key):
        return must(self.clients[key].get("Telephony/cards"), f"cards of {key}")

    # cleanup
    def cleanup(self):
        failures = []
        try:
            wait_idle(60)
        except AssertionError:
            failures.append("PBX not idle")
        rows = sql(f"SELECT id, IFNULL(c_asterisk_linked_id, ''), IFNULL(c_recording_path, '') FROM `call` "
                   f"WHERE c_phone_number LIKE '+{self.block}%' AND created_at >= '{self.t0}'")
        ids = [r[0] for r in rows]
        linked = [r[1] for r in rows if r[1]]
        for _, _, path in rows:
            if path and SAFE_RECORDING.match(path):
                subprocess.run(["sudo", "-n", "rm", "-f", str(MONITOR / path)], check=False)
        user_ids = list(self.uid.values())
        q = lambda items: ",".join(f"'{i}'" for i in items)  # noqa: E731 — ids of this run only
        statements = []
        if ids:
            statements += [f"DELETE FROM call_user WHERE call_id IN ({q(ids)})",
                           f"DELETE FROM call_contact WHERE call_id IN ({q(ids)})",
                           f"DELETE FROM call_lead WHERE call_id IN ({q(ids)})",
                           f"DELETE FROM entity_team WHERE entity_type = 'Call' AND entity_id IN ({q(ids)})",
                           f"DELETE FROM reminder WHERE entity_type = 'Call' AND entity_id IN ({q(ids)})",
                           f"DELETE FROM action_history_record WHERE target_type = 'Call' AND target_id IN ({q(ids)})",
                           f"DELETE FROM `call` WHERE id IN ({q(ids)})"]
        if linked:
            statements.append(f"DELETE FROM telephony_card WHERE linked_id IN ({q(linked)})")
        if user_ids:
            statements += [f"DELETE FROM telephony_card WHERE user_id IN ({q(user_ids)})",
                           f"DELETE FROM telephony_call_intent WHERE user_id IN ({q(user_ids)})"]
        for statement in statements:
            try:
                sql(statement)
            except subprocess.CalledProcessError:
                failures.append(statement.split(" WHERE")[0])
        # Phone numbers of the run's records, by id: collected before the records go away.
        record_ids = [rid for entity, rid in self.created if entity in ("Contact", "Account", "Lead")]
        phone_ids = [r[0] for r in sql(f"SELECT DISTINCT phone_number_id FROM entity_phone_number "
                                       f"WHERE entity_id IN ({q(record_ids)})")] if record_ids else []
        for entity, rid in reversed(self.created):
            status = None
            for _ in range(3):
                status = self.admin.delete(f"{entity}/{rid}")[0]
                if status in (200, 404):
                    break
                time.sleep(1)
            if status not in (200, 404):
                failures.append(f"{entity}/{rid}: HTTP {status}")
        failures += drop_phone_numbers(record_ids, phone_ids)
        self.admin.put("Settings", {"itvolgaTelephonyFallbackExtension": self.settings_before or "119"})
        reset_pbx()
        fcntl.flock(self._lock, fcntl.LOCK_UN)
        if failures:
            raise AssertionError("cleanup failed: " + "; ".join(failures))


def drop_phone_numbers(record_ids, phone_ids):
    """Removes the phone-number links of the given (deleted) records and those of the given phone numbers that no
    other record uses. Returns failure descriptions."""
    q = lambda items: ",".join(f"'{i}'" for i in items)  # noqa: E731
    try:
        if record_ids:
            sql(f"DELETE FROM entity_phone_number WHERE entity_id IN ({q(record_ids)})")
        if phone_ids:
            sql(f"DELETE FROM phone_number WHERE id IN ({q(phone_ids)}) AND id NOT IN "
                f"(SELECT phone_number_id FROM entity_phone_number WHERE phone_number_id IN ({q(phone_ids)}))")
    except subprocess.CalledProcessError:
        return ["phone numbers"]
    return []


def probe(payload):
    """tests/stage07_1/fixture.php as the stand user → its JSON answer."""
    php = subprocess.run(["bash", "-c", f"source {REPO}/scripts/stand/lib.sh >/dev/null && echo $PHP_BIN"],
                         capture_output=True, text=True, check=True).stdout.strip()
    out = subprocess.run(["sudo", "-n", "-u", "espocrm", "env", f"ESPO_ROOT={REPO}", php, "--", json.dumps(payload)],
                         input=(HERE / "fixture.php").read_text(encoding="utf-8"),
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out.strip().splitlines()[-1])


def setup_check():
    return subprocess.run([str(REPO / "scripts/stand/espo.sh"), "itvolga-setup-telephony", "--check"],
                          capture_output=True, text=True)


__all__ = ["REPO", "Client", "Run", "ast", "desk", "espo_console", "inbound", "last_provider_call", "must", "phone",
           "probe", "provider", "reset_pbx", "setup_check", "sql", "wait", "wait_idle", "listener_state", "MONITOR"]
