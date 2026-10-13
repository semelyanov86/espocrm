#!/usr/bin/env python3
"""Synthetic fixture for the stage 07.1 browser check (Playwriter; the telephony must be up: task telephony:up).

  python3 tests/stage07_1/ui_fixture.py create    → user synth-tel-ui-agent (Директор, extension 118, a synthetic team),
                                                    a synthetic account and contact with a synthetic number; the
                                                    password → <private>/ui-users.env (600, UI_AGENT_USERNAME/PASSWORD)
  python3 tests/stage07_1/ui_fixture.py call      → the test PBX calls 118 from the contact's number (rings 3 s, talk 8 s)
  python3 tests/stage07_1/ui_fixture.py delete    → removes the calls of the fixture's number with their cards, Action
                                                    History rows and recordings, then the records and the user

<private> is /data/itvolga/espo-private/stand/evidence/stage07.1 (UI_FIXTURE_DIR overrides it), mode 700. Only ids and
counts are printed.
"""
import json
import os
import secrets
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import (MONITOR, SAFE_RECORDING, Client, admin_credentials, drop_phone_numbers, inbound,  # noqa: E402
                     must, phone, sql)

DIR = Path(os.environ.get("UI_FIXTURE_DIR", "/data/itvolga/espo-private/stand/evidence/stage07.1"))
STATE = DIR / "ui-fixture.json"
USERS_ENV = DIR / "ui-users.env"


def private_write(path, text):
    DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as out:
        out.write(text)


def create(admin):
    if STATE.exists():
        raise SystemExit(f"{STATE} exists: run delete first")
    busy = sql("SELECT COUNT(*) FROM user WHERE deleted = 0 AND is_active = 1 AND c_phone_extension = '118'")[0][0]
    if busy != "0":
        raise SystemExit("an active user already has extension 118")
    number = f"7999{secrets.randbelow(10000):04d}{secrets.randbelow(1000):03d}"
    if sql(f"SELECT COUNT(*) FROM phone_number WHERE `numeric` LIKE '%{number[1:]}%'")[0][0] != "0":
        raise SystemExit("synthetic number in use: run create again")
    state = {"number": number, "t0": sql("SELECT UTC_TIMESTAMP()")[0][0], "records": []}
    private_write(STATE, json.dumps(state))
    roles = {r["name"]: r["id"] for r in must(admin.get("Role", maxSize=200), "roles")["list"]}

    def keep(entity, payload):
        state["records"].append([entity, payload["id"]])
        private_write(STATE, json.dumps(state))
        return payload["id"]

    team = keep("Team", must(admin.post("Team", {"name": "SYNTH-TEL-UI"}), "team"))
    password = secrets.token_urlsafe(14) + "Aa1!"
    keep("User", must(admin.post("User", {
        "userName": "synth-tel-ui-agent", "firstName": "Телефония", "lastName": "SYNTH-TEL-UI", "type": "regular",
        "isActive": True, "password": password, "passwordConfirm": password, "rolesIds": [roles["Директор"]],
        "teamsIds": [team], "defaultTeamId": team, "cPhoneExtension": "118", "sendAccessInfo": False}), "user"))
    account = keep("Account", must(admin.post("Account", {"name": "SYNTH-TEL-UI Клиент", "teamsIds": [team]}), "account"))
    keep("Contact", must(admin.post("Contact", {"firstName": "Клиент", "lastName": "SYNTH-TEL-UI", "accountId": account,
                                                "phoneNumber": "+" + number, "teamsIds": [team]}), "contact"))
    private_write(USERS_ENV, f"UI_AGENT_USERNAME=synth-tel-ui-agent\nUI_AGENT_PASSWORD={password}\n")
    print("created:", len(state["records"]), "records ->", USERS_ENV)


def call():
    state = json.loads(STATE.read_text(encoding="utf-8"))
    phone("118", "answer,3,8")
    inbound(state["number"], 30)
    print("calling 118")


def delete(admin):
    if not STATE.exists():
        print("nothing to delete")
        return
    state = json.loads(STATE.read_text(encoding="utf-8"))
    number = state["number"]
    rows = sql(f"SELECT id, IFNULL(c_asterisk_linked_id, ''), IFNULL(c_recording_path, '') FROM `call` "
               f"WHERE c_phone_number = '+{number}' AND created_at >= '{state['t0']}'")
    users = [rid for entity, rid in state["records"] if entity == "User"]
    for _, _, path in rows:
        if path and SAFE_RECORDING.match(path):
            subprocess.run(["sudo", "-n", "rm", "-f", str(MONITOR / path)], check=False)
    q = lambda items: ",".join(f"'{i}'" for i in items)  # noqa: E731 — ids of this fixture only
    ids = [r[0] for r in rows]
    linked = [r[1] for r in rows if r[1]]
    if ids:
        for table, column in (("call_user", "call_id"), ("call_contact", "call_id"), ("call_lead", "call_id")):
            sql(f"DELETE FROM {table} WHERE {column} IN ({q(ids)})")
        sql(f"DELETE FROM entity_team WHERE entity_type = 'Call' AND entity_id IN ({q(ids)})")
        sql(f"DELETE FROM action_history_record WHERE target_type = 'Call' AND target_id IN ({q(ids)})")
        sql(f"DELETE FROM `call` WHERE id IN ({q(ids)})")
    if linked:
        sql(f"DELETE FROM telephony_card WHERE linked_id IN ({q(linked)})")
    if users:
        sql(f"DELETE FROM telephony_card WHERE user_id IN ({q(users)})")
        sql(f"DELETE FROM telephony_call_intent WHERE user_id IN ({q(users)})")
    records = [rid for entity, rid in state["records"] if entity in ("Contact", "Account")]
    phone_ids = [r[0] for r in sql(f"SELECT DISTINCT phone_number_id FROM entity_phone_number "
                                   f"WHERE entity_id IN ({q(records)})")] if records else []
    left = [rec for rec in reversed(state["records"]) if admin.delete(f"{rec[0]}/{rec[1]}")[0] not in (200, 404)]
    if drop_phone_numbers(records, phone_ids):
        raise SystemExit("phone numbers not removed")
    if left:
        state["records"] = list(reversed(left))
        private_write(STATE, json.dumps(state))
        raise SystemExit(f"records not deleted: {len(left)}")
    STATE.unlink()
    USERS_ENV.unlink(missing_ok=True)
    print("deleted calls:", len(ids), "records:", len(state["records"]))


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else ""
    if action == "call":
        call()
    elif action in ("create", "delete"):
        globals()[action](Client(*admin_credentials()))
    else:
        raise SystemExit("usage: ui_fixture.py create|call|delete")
