#!/usr/bin/env python3
"""Synthetic fixture for the stage-05.1 browser check of the reports module (Playwriter, evidence.md).

  python3 tests/stage05_1/ui_fixture.py create   → users, a team, records; passwords → <private>/ui-users.env (600)
  python3 tests/stage05_1/ui_fixture.py delete   → removes the records, the reports and folders of the fixture users,
                                                   the team and the users

<private> is /data/itvolga/espo-private/stand/evidence/stage05.1 (UI_FIXTURE_DIR overrides it), mode 700; the state is
<private>/ui-fixture.json (600). Users: synth-rep-manager and synth-rep-manager2 (Директор; manager2 is in the team
«SYNTH-REP команда», to share a report with a team), synth-rep-access («Доступы» only: reads public reports and those
shared with him), synth-rep-deputy (Заместитель директора: no finance). Records «SYNTH-REP …»: three accounts with a
contact each, three products, six invoices (three of this month, three of the last one, several lines each, statuses
Created/Sent/Approved) and five opportunities in different stages. Only counts and ids are printed, never passwords.
"""
import json
import os
import secrets
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fixture import Client, admin_credentials, month_start, stand_today  # noqa: E402

PRIVATE = Path(os.environ.get("UI_FIXTURE_DIR", "/data/itvolga/espo-private/stand/evidence/stage05.1"))
STATE = PRIVATE / "ui-fixture.json"
USERS_ENV = PRIVATE / "ui-users.env"
TAG = "SYNTH-REP"
USERS = (("manager", ["Директор"]), ("manager2", ["Директор"]), ("access", ["Доступы"]),
         ("deputy", ["Заместитель директора"]))


def must(result):
    status, payload, _ = result
    if status != 200:
        raise SystemExit(f"HTTP {status}: {json.dumps(payload, ensure_ascii=False)[:300]}")
    return payload


def save_state(state):
    PRIVATE.mkdir(parents=True, exist_ok=True)
    PRIVATE.chmod(0o700)
    STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    STATE.chmod(0o600)


def create():
    if STATE.exists():
        raise SystemExit(f"{STATE} exists: run `delete` first")
    try:
        _create()
    except BaseException:
        if STATE.exists():
            delete()
        raise


def _create():
    admin = Client(*admin_credentials())
    roles = {r["name"]: r["id"] for r in must(admin.get("Role", maxSize=200))["list"]}
    state, env = {"users": {}, "records": []}, []

    def rec(entity, data):
        payload = must(admin.post(entity, data))
        state["records"].append([entity, payload["id"]])
        save_state(state)
        return payload["id"]

    state["team"] = rec("Team", {"name": f"{TAG} команда"})
    for key, role_names in USERS:
        password = secrets.token_urlsafe(14) + "Aa1!"
        user = must(admin.post("User", {
            "userName": f"synth-rep-{key}", "firstName": "Отчёты", "lastName": f"{TAG} {key}", "type": "regular",
            "isActive": True, "password": password, "passwordConfirm": password,
            "rolesIds": [roles[name] for name in role_names],
            "teamsIds": [state["team"]] if key == "manager2" else [], "sendAccessInfo": False}))
        state["users"][key] = user["id"]
        save_state(state)
        env.append(f"UI_{key.upper()}_USERNAME=synth-rep-{key}\nUI_{key.upper()}_PASSWORD={password}\n")
    USERS_ENV.write_text("".join(env), encoding="utf-8")
    USERS_ENV.chmod(0o600)

    manager, manager2 = state["users"]["manager"], state["users"]["manager2"]
    accounts = [rec("Account", {"name": f"{TAG} {name}", "assignedUserId": manager, "industry": industry})
                for name, industry in (("Альфа", "Banking"), ("Бета", "Construction"), ("Гамма", "Banking"))]
    for i, account in enumerate(accounts):
        rec("Contact", {"firstName": "Иван", "lastName": f"{TAG} контакт {i + 1}", "accountId": account,
                        "assignedUserId": manager if i < 2 else manager2})
    products = [rec("Product", {"name": f"{TAG} {name}", "type": kind, "unitPrice": price, "unitPriceCurrency": "RUB"})
                for name, kind, price in (("Обслуживание", "service", "15000"), ("Настройка", "service", "1800"),
                                          ("Лицензия", "product", "12345.67"))]
    today = stand_today()
    m0, m1 = month_start(today), month_start(today, -1)
    invoices = (
        (0, m0, 1, "Created", manager, [(0, "1", "15000"), (1, "2.5", "1800")]),
        (1, m0, 2, "Sent", manager, [(1, "4", "1800"), (2, "1", "12345.67")]),
        (2, m0, 3, "Approved", manager2, [(0, "1", "15000")]),
        (0, m1, 10, "Sent", manager, [(0, "1", "15000"), (2, "2", "12345.67")]),
        (1, m1, 15, "Created", manager2, [(1, "1.5", "1800")]),
        (2, m1, 20, "Created", manager, [(0, "1", "1000.50"), (1, "1", "0.01")]),
    )
    state["invoices"] = []
    for n, (account, month, day, status, owner, lines) in enumerate(invoices, start=1):
        dated = month + timedelta(days=day - 1)
        state["invoices"].append(rec("Invoice", {
            "name": f"{TAG} счёт {n}", "accountId": accounts[account], "status": status,
            "dateInvoiced": dated.isoformat(), "dateDue": (dated + timedelta(days=14)).isoformat(),
            "assignedUserId": owner,
            "itemList": [{"productId": products[p], "quantity": q, "unitPrice": price} for p, q, price in lines]}))
    opportunities = (
        (0, "Qualification", "50000", 0), (0, "Proposal or Price Quote", "120000", 10),
        (1, "Negotiation or Review", "75000.50", 20), (1, "Closed Won", "30000", -5),
        (2, "Closed Lost", "9999.99", -20))
    state["opportunities"] = []
    for n, (account, stage, amount, shift) in enumerate(opportunities, start=1):
        state["opportunities"].append(rec("Opportunity", {
            "name": f"{TAG} сделка {n}", "accountId": accounts[account], "stage": stage, "amount": amount,
            "amountCurrency": "RUB", "closeDate": (today + timedelta(days=shift)).isoformat(),
            "assignedUserId": manager if n % 2 else manager2}))
    state.update(accounts=accounts, products=products)
    save_state(state)
    counts = {}
    for entity, _ in state["records"]:
        counts[entity] = counts.get(entity, 0) + 1
    print(json.dumps({"users": state["users"], "team": state["team"], "counts": counts,
                      "invoices": state["invoices"], "opportunities": state["opportunities"]}, indent=2))


def owned(admin, entity, user_ids):
    """Ids of records of `entity` assigned to the fixture users (reports and folders made in the browser)."""
    if not user_ids:
        return []
    params = {"where[0][type]": "in", "where[0][attribute]": "assignedUserId", "select": "id", "maxSize": 200}
    params.update({f"where[0][value][{i}]": uid for i, uid in enumerate(user_ids)})
    return [r["id"] for r in must(admin.get(entity, **params))["list"]]


def delete():
    admin = Client(*admin_credentials())
    state = json.loads(STATE.read_text(encoding="utf-8"))
    user_ids = list(state.get("users", {}).values())
    for entity in ("Report", "ReportFolder"):
        for rid in owned(admin, entity, user_ids):
            admin.delete(f"{entity}/{rid}")
    team = [["Team", state["team"]]] if state.get("team") else []
    for entity, rid in reversed([r for r in state["records"] if r not in team]):
        admin.delete(f"{entity}/{rid}")
    for rid in user_ids:
        admin.delete(f"User/{rid}")
    for entity, rid in team:
        admin.delete(f"{entity}/{rid}")
    STATE.unlink()
    USERS_ENV.unlink(missing_ok=True)
    print("deleted")


if __name__ == "__main__":
    {"create": create, "delete": delete}[sys.argv[1]]()
