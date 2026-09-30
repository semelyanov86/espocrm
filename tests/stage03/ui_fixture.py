#!/usr/bin/env python3
"""Synthetic fixture for the stage-03 UI scenarios (checked in the browser, see docs/migration/evidence.md).

  python3 tests/stage03/ui_fixture.py create   → users/records; passwords → <private>/ui-users.env (600)
  python3 tests/stage03/ui_fixture.py delete   → removes everything created by `create`

Users: synth-ui-admin-view is not needed (the stand admin is used); synth-ui-deputy (Заместитель директора),
synth-ui-access (Заместитель директора + Доступы). Records carry the prefix «SYNTH-UI».
"""
import json
import os
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from espo import Client, admin_credentials, sql  # noqa: E402

PRIVATE = Path(os.environ.get("UI_FIXTURE_DIR", "/data/itvolga/espo-private/stand/evidence/stage03"))
STATE = PRIVATE / "ui-fixture.json"
USERS_ENV = PRIVATE / "ui-users.env"


def must(result):
    status, payload, _ = result
    if status != 200:
        raise SystemExit(f"HTTP {status}: {json.dumps(payload, ensure_ascii=False)[:300]}")
    return payload


def create():
    try:
        _create()
    except BaseException:
        if STATE.exists():
            delete()
        raise


def _create():
    admin = Client(*admin_credentials())
    roles = {r["name"]: r["id"] for r in must(admin.get("Role", maxSize=50))["list"]}
    teams = {t["name"]: t["id"] for t in must(admin.get("Team", maxSize=50))["list"]}
    state, env, passwords = {"users": {}, "records": []}, [], {}
    for key, role_names, team_names in (("deputy", ["Заместитель директора"], ["Отдел Поддержки"]),
                                        ("access", ["Заместитель директора", "Доступы"], ["Отдел Поддержки"])):
        password = secrets.token_urlsafe(14) + "Aa1!"
        user = must(admin.post("User", {
            "userName": f"synth-ui-{key}", "lastName": f"SYNTH-UI {key}", "type": "regular", "isActive": True,
            "password": password, "passwordConfirm": password, "rolesIds": [roles[r] for r in role_names],
            "teamsIds": [teams[t] for t in team_names]}))
        state["users"][key] = user["id"]
        passwords[key] = password
        save_state(state)
        env.append(f"UI_{key.upper()}_USERNAME=synth-ui-{key}\nUI_{key.upper()}_PASSWORD={password}\n")

    def rec(entity, data):
        payload = must(admin.post(entity, data))
        state["records"].append([entity, payload["id"]])
        save_state(state)
        return payload["id"]

    acc = rec("Account", {"name": "SYNTH-UI ООО Пример", "cShortName": "Пример", "cInn": "77-SYNTH-01",
                          "cKpp": "770-SYNTH", "cBankAccount": "40702-810-SYNTH-0001", "cBic": "04-SYNTH",
                          "cRating": "Active", "industry": "Retail", "type": "Customer",
                          "assignedUserId": state["users"]["deputy"]})
    # soft-deleted records keep their vtigerId (unique, D-41): every run takes a fresh synthetic key
    sql(f"UPDATE account SET vtiger_id={990_000_000 + secrets.randbelow(9_000_000)}, vtiger_no='КОНТР_SYNTH', "
        f"vtiger_data='{{\"ownership\": \"synthetic\", \"isconvertedfromlead\": \"0\"}}' WHERE id='{acc}'")
    con = rec("Contact", {"lastName": "SYNTH-UI Контакт", "accountId": acc, "cDepartment": "ИТ",
                          "cSupportStartDate": "2024-01-01", "cSupportEndDate": "2024-12-31",
                          "cNeedOriginalDocs": True, "assignedUserId": state["users"]["access"],
                          "teamsIds": [teams["Отдел Поддержки"]]})
    client_access = Client("synth-ui-access", passwords["access"])
    status, ca, _ = client_access.post("ContactAccess", {"contactId": con, "anydeskId": "111 222 333",
                                                         "anydeskPassword": "exampleUiValue", "hostname": "synth-pc",
                                                         "ipAddress": "ip-synthetic"})
    if status != 200:
        raise SystemExit(f"ContactAccess create failed: HTTP {status}")
    state["records"].append(["ContactAccess", ca["id"]])
    rec("Lead", {"lastName": "SYNTH-UI Обращение", "status": "Hot", "source": "Web Site", "cPriority": "VIP"})
    PRIVATE.mkdir(parents=True, exist_ok=True)
    USERS_ENV.write_text("".join(env), encoding="utf-8")
    USERS_ENV.chmod(0o600)
    state.update({"account": acc, "contact": con, "contactAccess": ca["id"]})
    STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    STATE.chmod(0o600)
    print(json.dumps({k: v for k, v in state.items() if k != "records"}, indent=2))


def save_state(state):
    PRIVATE.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    STATE.chmod(0o600)


def delete():
    admin = Client(*admin_credentials())
    state = json.loads(STATE.read_text(encoding="utf-8"))
    for entity, rid in reversed(state["records"]):
        admin.delete(f"{entity}/{rid}")
    for rid in state["users"].values():
        admin.delete(f"User/{rid}")
    STATE.unlink()
    USERS_ENV.unlink(missing_ok=True)
    print("deleted")


if __name__ == "__main__":
    {"create": create, "delete": delete}[sys.argv[1]]()
