#!/usr/bin/env python3
"""Synthetic fixture for the stage-04.2–04.6 UI scenarios (checked in the browser with Playwriter, evidence.md).

  python3 tests/stage04/ui_fixture.py create   → users/records; passwords → <private>/ui-users.env (600)
  python3 tests/stage04/ui_fixture.py delete   → removes everything created by `create`

Users: synth-ui-director (Директор), synth-ui-fdeputy (Заместитель директора: no finance). Records carry the prefix
«SYNTH-UI»: an account, a contact, two products, a quote calculated in EspoCRM and a sales order made from it, an
"imported" quote, a new invoice and three "imported" invoices (source values written by SQL as the importer would;
classified by itvolga-finance-verify): «По умолчанию» with historical 18 % lines and no due date, a rounded and a
mismatching one; payments (stage 04.4): a partial payment of the invoice, a payment of the sales order and of the
rounded invoice with a rest, a planned payment and an outgoing payment to a vendor; acts (stage 04.5): an "imported"
act with a mismatching total that two imported invoices point to (the new invoice has no act: «Создать акт» in the
browser); the end-to-end chain (stage 04.6): the quote has a team, a contact and a deal, so «Создать заказ» → «Создать
счёт» → «Создать акт» → «Добавить платёж» in the browser shows what each step carries. Documents created in the browser
from the fixture quote and sales order, acts created from the fixture invoices or account, and payments allocated in the
browser to the fixture documents or paid by the fixture account or vendor, are removed with them.
"""
import json
import os
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "stage03"))
from espo import Client, admin_credentials, espo_console, sql  # noqa: E402

PRIVATE = Path(os.environ.get("UI_FIXTURE_DIR", "/data/itvolga/espo-private/stand/evidence/stage04.6"))
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
    team = rec("Team", {"name": "SYNTH-UI Команда"})
    contact = rec("Contact", {"lastName": "SYNTH-UI Контакт", "accountId": acc})
    deal = rec("Opportunity", {"name": "SYNTH-UI Сделка", "accountId": acc, "closeDate": "2026-12-31"})
    quote = rec("Quote", {"name": "SYNTH-UI Предложение", "accountId": acc, "assignedUserId": state["users"]["director"],
                          "teamsIds": [team], "contactId": contact, "opportunityId": deal,
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

    order = rec("SalesOrder", {"name": "SYNTH-UI Заказ", "accountId": acc, "quoteId": quote, "itemList": [
        {"productId": svc, "quantity": "4", "unitPrice": "1500.00"}]})
    dates = {"dateInvoiced": "2026-10-02", "dateDue": "2026-10-16"}
    invoice = rec("Invoice", {"name": "SYNTH-UI Счёт", "accountId": acc, "contactId": contact, **dates,
                              "assignedUserId": state["users"]["director"], "itemList": [
                                  {"productId": svc, "quantity": "2.5", "unitPrice": "1500.00", "description": "Часы"},
                                  {"productId": prd, "quantity": "1", "unitPrice": "12345.67", "discountPercent": "10"},
                                  {"productId": svc, "quantity": "1", "unitPrice": "0.005"}]})
    invoices = {"invoice": invoice}
    # (key, lines, stored subtotal = pre-tax = total, region_id, spcompany, line tax, number prefix, due date)
    for key, lines, stored, region, company, tax, prefix, due in (
            ("importedInvoice", [("2", "1000"), ("1", "500")], "2500", None, "По умолчанию", 18, "СЧЕТ_", None),
            ("roundedInvoice", [("3", "33.335")], "100.01", 0, "Default", 0, "С-", "'2026-10-16'"),
            ("mismatchInvoice", [("1", "5000")], "5000.01", 0, "Default", 0, "С-", "'2026-10-16'")):
        iid = rec("Invoice", {"name": f"SYNTH-UI Импортированный счёт ({key})", "accountId": acc, **dates,
                              "itemList": [{"productId": svc, "quantity": q, "unitPrice": p} for q, p in lines]})
        vt = 970_000_000 + secrets.randbelow(9_000_000)
        data = json.dumps({"region_id": region, "spcompany": company}, ensure_ascii=False)
        sql(f"UPDATE invoice SET vtiger_id={vt}, number='{prefix}{vt}', status='Paid', subtotal={stored}, "
            f"pre_tax_total={stored}, grand_total={stored}, balance_source=0, date_due={due or 'NULL'}, "
            f"vtiger_data='{data}' WHERE id='{iid}'")
        sql(f"UPDATE invoice_item SET tax_rate={tax}, margin=0 WHERE invoice_id='{iid}'")
        print(espo_console("itvolga-finance-verify", "--entity=Invoice", f"--id={iid}").strip())
        invoices[key] = iid
    vendor = rec("Vendor", {"name": "SYNTH-UI Поставщик"})
    director = state["users"]["director"]
    payment = {"datePaid": "2026-10-02", "assignedUserId": director, "payerType": "Account", "payerId": acc}
    payments = {
        "partialPayment": rec("Payment", {**payment, "amount": "5000", "documentNumber": "17",
                                          "allocationList": [{"invoiceId": invoice, "amount": "5000"}]}),
        "splitPayment": rec("Payment", {**payment, "amount": "7000", "method": "cash", "allocationList": [
            {"salesOrderId": order, "amount": "6000"}, {"invoiceId": invoices["roundedInvoice"], "amount": "100.01"}]}),
        "plannedPayment": rec("Payment", {**payment, "amount": "5000.01", "status": "Запланирован", "allocationList": [
            {"invoiceId": invoices["mismatchInvoice"], "amount": "5000.01"}]}),
        "vendorPayment": rec("Payment", {**payment, "amount": "1200", "direction": "outgoing", "payerType": "Vendor",
                                         "payerId": vendor, "purpose": "SYNTH-UI оплата поставщику"}),
    }
    # An "imported" act (digits number, status Received, a total that mismatches its line) of two imported invoices.
    act = rec("Act", {"name": "SYNTH-UI Импортированный акт", "accountId": acc, "dateAct": "2019-05-20",
                      "assignedUserId": director, "itemList": [{"productId": svc, "quantity": "1", "unitPrice": "5000"}]})
    vt = 970_000_000 + secrets.randbelow(9_000_000)
    data = json.dumps({"region_id": 0, "spcompany": "Default"}, ensure_ascii=False)
    sql(f"UPDATE act SET vtiger_id={vt}, number='{vt}', status='Received', subtotal=5000.01, pre_tax_total=5000.01, "
        f"grand_total=5000.01, vtiger_data='{data}' WHERE id='{act}'")
    sql(f"UPDATE act_item SET margin=0 WHERE act_id='{act}'")
    print(espo_console("itvolga-finance-verify", "--entity=Act", f"--id={act}").strip())
    sql(f"UPDATE invoice SET act_id='{act}' WHERE id IN ('{invoices['importedInvoice']}', "
        f"'{invoices['roundedInvoice']}')")
    state.update({"account": acc, "contact": contact, "team": team, "deal": deal, "service": svc, "product": prd, "quote": quote,
                  "importedQuote": imported, "salesOrder": order, "vendor": vendor, "importedAct": act, **invoices,
                  **payments})
    save_state(state)
    print(json.dumps({k: v for k, v in state.items() if k != "records"}, indent=2))


# Documents the browser may create from a fixture document («Создать заказ», «Создать счёт») or account (an act from
# the «Акты» panel).
CHILDREN = {"Quote": (("invoices", "Invoice"), ("salesOrders", "SalesOrder")), "SalesOrder": (("invoices", "Invoice"),),
            "Account": (("cActs", "Act"),)}
# An act the browser may create from a fixture invoice («Создать акт»): the key is on the invoice.
PARENTS = {"Invoice": ("actId", "Act")}
# Payments the browser may create: allocated to a fixture document («Добавить платёж»), paid by the fixture account
# or vendor (the «Платежи» panel).
PAYMENT_LINKS = {"Invoice": "paymentAllocations", "SalesOrder": "paymentAllocations", "Account": "cPayments",
                 "Vendor": "payments"}


def delete_with_children(admin, entity, rid):
    if entity in PARENTS:
        key, parent = PARENTS[entity]
        if parent_id := (admin.get(f"{entity}/{rid}")[1] or {}).get(key):
            admin.delete(f"{parent}/{parent_id}")
    for link, child in CHILDREN.get(entity, ()):
        for record in (admin.get(f"{entity}/{rid}/{link}")[1] or {"list": []})["list"]:
            delete_with_children(admin, child, record["id"])
    if entity in PAYMENT_LINKS:
        for record in (admin.get(f"{entity}/{rid}/{PAYMENT_LINKS[entity]}", maxSize=200)[1] or {"list": []})["list"]:
            admin.delete(f"Payment/{record.get('paymentId') or record['id']}")
    admin.delete(f"{entity}/{rid}")


def delete():
    admin = Client(*admin_credentials())
    state = json.loads(STATE.read_text(encoding="utf-8"))
    for entity, rid in reversed(state["records"]):
        delete_with_children(admin, entity, rid)
    for rid in state["users"].values():
        admin.delete(f"User/{rid}")
    STATE.unlink()
    USERS_ENV.unlink(missing_ok=True)
    print("deleted")


if __name__ == "__main__":
    {"create": create, "delete": delete}[sys.argv[1]]()
