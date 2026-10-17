#!/usr/bin/env python3
"""Synthetic users and the record choice for the stage 08 browser check of the rehearsal (docs/migration/rehearsal.md).
The stand holds the real imported data: the check reads only DOM flags and response codes, never record values.

  python3 tests/stage08/ui_fixture.py create   → synth-s08-director (Директор: reads every call, so the recording
                                               plays) and synth-s08-manager (Менеджер по продажам in a synthetic team
                                               of its own: calls of others are closed — no recording); passwords →
                                               <private>/ui-users.env (600, UI_DIRECTOR_*/UI_MANAGER_*); ids of the
                                               imported records to open → <private>/ui-records.json (ids only)
  python3 tests/stage08/ui_fixture.py delete   → removes the users, their team and their Action History rows (by the
                                               ids `create` recorded)

<private> is /data/itvolga/espo-private/stand/evidence/stage08 (UI_FIXTURE_DIR overrides it), mode 700. Only ids and
counts are printed.
"""
import json
import os
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "stage03"))
from espo import Client, admin_credentials, sql  # noqa: E402

DIR = Path(os.environ.get("UI_FIXTURE_DIR", "/data/itvolga/espo-private/stand/evidence/stage08"))
STATE = DIR / "ui-fixture.json"
USERS_ENV = DIR / "ui-users.env"
RECORDS = DIR / "ui-records.json"

# Imported records with everything the scenarios open (ids only; the real key range of the import).
CHOICE = {
    "invoice": "SELECT i.id FROM invoice i JOIN act a ON a.id = i.act_id AND a.deleted = 0 "
               "JOIN payment_allocation pa ON pa.invoice_id = i.id AND pa.deleted = 0 "
               "JOIN payment p ON p.id = pa.payment_id AND p.deleted = 0 AND p.direction = 'incoming' "
               "WHERE i.deleted = 0 AND i.vtiger_id < 900000000 AND i.account_id IS NOT NULL "
               "AND EXISTS (SELECT 1 FROM invoice_item ii WHERE ii.invoice_id = i.id AND ii.deleted = 0) "
               "ORDER BY i.vtiger_id DESC LIMIT 1",
    "case": "SELECT c.id FROM `case` c JOIN account a ON a.id = c.account_id AND a.deleted = 0 "
            "WHERE c.deleted = 0 AND c.vtiger_id < 900000000 ORDER BY c.vtiger_id DESC LIMIT 1",
    "document": "SELECT d.id FROM document d JOIN attachment t ON t.id = d.file_id AND t.deleted = 0 "
                "WHERE d.deleted = 0 AND d.vtiger_id < 900000000 ORDER BY d.vtiger_id DESC LIMIT 1",
    "call": "SELECT c.id FROM `call` c WHERE c.deleted = 0 AND c.c_cdr_source IS NOT NULL AND c.c_recording = 1 "
            "AND c.assigned_user_id IS NOT NULL ORDER BY c.date_start DESC LIMIT 1",
}


def must(result, what):
    status, payload, _ = result
    if status != 200:
        raise SystemExit(f"{what}: HTTP {status}")
    return payload


def private_write(path, text):
    DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as out:
        out.write(text)


def create(admin):
    if STATE.exists():
        raise SystemExit(f"{STATE} exists: run delete first")
    records = {}
    for key, query in CHOICE.items():
        rows = sql(query)
        if not rows:
            raise SystemExit(f"no imported {key} for the scenario")
        records[key] = rows[0][0]
    records["account"] = sql(f"SELECT account_id FROM invoice WHERE id = '{records['invoice']}'")[0][0]
    records["act"] = sql(f"SELECT act_id FROM invoice WHERE id = '{records['invoice']}'")[0][0]
    records["allocation"], records["payment"] = sql(
        f"SELECT pa.id, pa.payment_id FROM payment_allocation pa JOIN payment p ON p.id = pa.payment_id "
        f"WHERE pa.invoice_id = '{records['invoice']}' AND pa.deleted = 0 AND p.deleted = 0 "
        f"AND p.direction = 'incoming' ORDER BY pa.vtiger_id LIMIT 1")[0]
    records["caseAccount"] = sql(f"SELECT account_id FROM `case` WHERE id = '{records['case']}'")[0][0]
    state = {"records": []}
    private_write(STATE, json.dumps(state))
    roles = {r["name"]: r["id"] for r in must(admin.get("Role", maxSize=200), "roles")["list"]}

    def keep(entity, payload):
        state["records"].append([entity, payload["id"]])
        private_write(STATE, json.dumps(state))
        return payload["id"]

    team = keep("Team", must(admin.post("Team", {"name": "SYNTH-S08-UI"}), "team"))
    env = []
    for key, role in (("director", "Директор"), ("manager", "Менеджер по продажам")):
        password = secrets.token_urlsafe(14) + "Aa1!"
        keep("User", must(admin.post("User", {
            "userName": f"synth-s08-{key}", "firstName": "Репетиция", "lastName": f"SYNTH-S08 {key}",
            "type": "regular", "isActive": True, "password": password, "passwordConfirm": password,
            "rolesIds": [roles[role]], "teamsIds": [team], "defaultTeamId": team, "sendAccessInfo": False}), key))
        env.append(f"UI_{key.upper()}_USERNAME=synth-s08-{key}\nUI_{key.upper()}_PASSWORD={password}\n")
    if sql(f"SELECT COUNT(*) FROM `call` WHERE id = '{records['call']}' AND assigned_user_id IN "
           f"(SELECT id FROM user WHERE user_name LIKE 'synth-s08-%')")[0][0] != "0":
        raise SystemExit("the chosen call belongs to a fixture user")
    private_write(USERS_ENV, "".join(env))
    private_write(RECORDS, json.dumps(records))
    print("created:", len(state["records"]), "records; scenario records:", len(records), "->", RECORDS)


def delete(admin):
    if not STATE.exists():
        print("nothing to delete")
        return
    state = json.loads(STATE.read_text(encoding="utf-8"))
    users = [rid for entity, rid in state["records"] if entity == "User"]
    if users:
        listed = ",".join(f"'{rid}'" for rid in users)  # ids of this fixture only
        sql(f"DELETE FROM action_history_record WHERE user_id IN ({listed})")
    left = [rec for rec in reversed(state["records"]) if admin.delete(f"{rec[0]}/{rec[1]}")[0] not in (200, 404)]
    if left:
        state["records"] = list(reversed(left))
        private_write(STATE, json.dumps(state))
        raise SystemExit(f"records not deleted: {len(left)}")
    STATE.unlink()
    USERS_ENV.unlink(missing_ok=True)
    RECORDS.unlink(missing_ok=True)
    print("deleted records:", len(state["records"]))


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else ""
    if action not in ("create", "delete"):
        raise SystemExit("usage: ui_fixture.py create|delete")
    globals()[action](Client(*admin_credentials()))
