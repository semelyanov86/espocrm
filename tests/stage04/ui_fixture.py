#!/usr/bin/env python3
"""Synthetic fixture for the stage-04.2 UI scenarios (checked in the browser with Playwriter, see evidence.md).

  python3 tests/stage04/ui_fixture.py create   → users/records; passwords → <private>/ui-users.env (600)
  python3 tests/stage04/ui_fixture.py delete   → removes everything created by `create`

Users: synth-ui-director (Директор), synth-ui-fdeputy (Заместитель директора: no finance). Records carry the prefix
«SYNTH-UI»: an account, two products, a quote calculated in EspoCRM and an "imported" quote (source values written
by SQL as the importer would, historical 18 % lines; classified by itvolga-finance-verify).
"""
import json
import os
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "stage03"))
from espo import Client, admin_credentials, espo_console, sql  # noqa: E402

PRIVATE = Path(os.environ.get("UI_FIXTURE_DIR", "/data/itvolga/espo-private/stand/evidence/stage04.2"))
STATE = PRIVATE / "ui-fixture.json"
USERS_ENV = PRIVATE / "ui-users.env"


def must(result):
    status, payload, _ = result
    if status != 200:
        raise SystemExit(f"HTTP {status}: {json.dumps(payload, ensure_ascii=False)[:300]}")
    return payload


def save_state(state):
    PRIVATE.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    STATE.chmod(0o600)


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
    state, env = {"users": {}, "records": []}, []
    for key, role in (("director", "Директор"), ("fdeputy", "Заместитель директора")):
        password = secrets.token_urlsafe(14) + "Aa1!"
        user = must(admin.post("User", {
            "userName": f"synth-ui-{key}", "lastName": f"SYNTH-UI {key}", "type": "regular", "isActive": True,
            "password": password, "passwordConfirm": password, "rolesIds": [roles[role]]}))
        state["users"][key] = user["id"]
        save_state(state)
        env.append(f"UI_{key.upper()}_USERNAME=synth-ui-{key}\nUI_{key.upper()}_PASSWORD={password}\n")
    PRIVATE.mkdir(parents=True, exist_ok=True)
    USERS_ENV.write_text("".join(env), encoding="utf-8")
    USERS_ENV.chmod(0o600)
    espo_console("itvolga-setup-acl")

    def rec(entity, data):
        payload = must(admin.post(entity, data))
        state["records"].append([entity, payload["id"]])
        save_state(state)
        return payload["id"]

    acc = rec("Account", {"name": "SYNTH-UI ООО Пример"})
    svc = rec("Product", {"name": "SYNTH-UI Сопровождение 1С", "type": "service", "unitPrice": "1500.00",
                          "unitPriceCurrency": "RUB", "unit": "Hours", "description": "Абонентское обслуживание"})
    prd = rec("Product", {"name": "SYNTH-UI Лицензия", "type": "product", "unitPrice": "12345.67",
                          "unitPriceCurrency": "RUB"})
    quote = rec("Quote", {"name": "SYNTH-UI Предложение", "accountId": acc, "assignedUserId": state["users"]["director"],
                          "itemList": [
                              {"productId": svc, "quantity": "2.5", "unitPrice": "1500.00", "description": "Часы"},
                              {"productId": prd, "quantity": "1", "unitPrice": "12345.67", "discountPercent": "10"}]})
    imported = rec("Quote", {"name": "SYNTH-UI Импортированное предложение", "accountId": acc,
                             "itemList": [{"productId": svc, "quantity": "2", "unitPrice": "1000"},
                                          {"productId": prd, "quantity": "1", "unitPrice": "500"}]})
    vt = 970_000_000 + secrets.randbelow(9_000_000)
    sql(f"UPDATE quote SET vtiger_id={vt}, number='SYNTH-UI-{vt}', status='Accepted', subtotal=2500, pre_tax_total=2500, "
        f"grand_total=2500, vtiger_data='{{\"region_id\":null}}' WHERE id='{imported}'")
    sql(f"UPDATE quote_item SET tax_rate=18, margin=0 WHERE quote_id='{imported}'")
    print(espo_console("itvolga-finance-verify", "--entity=Quote", f"--id={imported}").strip())
    state.update({"account": acc, "service": svc, "product": prd, "quote": quote, "importedQuote": imported})
    save_state(state)
    print(json.dumps({k: v for k, v in state.items() if k != "records"}, indent=2))


def delete():
    admin = Client(*admin_credentials())
    state = json.loads(STATE.read_text(encoding="utf-8"))
    # Sales orders created in the browser from the fixture quote go with it.
    for entity, rid in reversed(state["records"]):
        if entity == "Quote":
            orders = admin.get(f"Quote/{rid}/salesOrders")[1] or {"list": []}
            for order in orders["list"]:
                admin.delete(f"SalesOrder/{order['id']}")
        admin.delete(f"{entity}/{rid}")
    for rid in state["users"].values():
        admin.delete(f"User/{rid}")
    STATE.unlink()
    USERS_ENV.unlink(missing_ok=True)
    print("deleted")


if __name__ == "__main__":
    {"create": create, "delete": delete}[sys.argv[1]]()
