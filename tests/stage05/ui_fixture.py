#!/usr/bin/env python3
"""Synthetic fixture for the stage-05 print forms (PDF checks and the browser check with Playwriter, evidence.md).

  python3 tests/stage05/ui_fixture.py create   → users, records, synthetic requisites; passwords → <private>/ui-users.env
  python3 tests/stage05/ui_fixture.py render   → the five PDFs of the fixture → <private>/pdf/*.pdf (600)
  python3 tests/stage05/ui_fixture.py delete   → removes the records and users, restores the legal entity

Users: synth-print-director (Директор), synth-print-fdeputy (Заместитель директора: no finance). The single legal entity
gets synthetic requisites and a synthetic logo for the time of the fixture (the stand has a placeholder until the import,
D-55); the previous values are kept in the state file and restored by `delete`. Records: an account with requisites and
an address, a contact, three products, a quote, a sales order, an invoice and an act like the synthetic reference render
of the SalesPlatform templates (two lines, 19 500,00), an invoice with line discounts, an incoming cash payment of the
invoice and an outgoing payment (no PKO). Phone numbers are generated per run (no literal phone numbers in Git).
"""
import base64
import io
import json
import os
import secrets
import string
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "stage03"))
from espo import Client, admin_credentials, espo_console  # noqa: E402

PRIVATE = Path(os.environ.get("UI_FIXTURE_DIR", "/data/itvolga/espo-private/stand/evidence/stage05"))
STATE = PRIVATE / "ui-fixture.json"
USERS_ENV = PRIVATE / "ui-users.env"
# The logo is not saved and restored: replacing an image field makes the core delete the previous attachment, so an
# existing logo is kept and a synthetic one is added only when there is none (and cleared, with its file, by delete).
LEGAL_ENTITY_FIELDS = ["name", "inn", "kpp", "okpo", "bankAccount", "bankName", "bic", "corrAccount", "director",
                       "bookkeeper", "phoneNumber", "website", "addressStreet", "addressCity", "addressState",
                       "addressPostalCode", "addressCountry"]
# Synthetic requisites: letters inside every number, so no value looks like a real INN, account or phone.
SELLER = {
    "name": "ООО «Тестовая Организация»", "inn": "50-SYNTH-02", "kpp": "500-SYNTH", "okpo": "SYNTH-OKPO",
    "bankAccount": "40702-810-SYNTH-0001", "bankName": "АО «ТЕСТ-БАНК», г. Тестовск", "bic": "04-SYNTH",
    "corrAccount": "30101-810-SYNTH-0002", "director": "Тестов Т. Т.", "bookkeeper": "Счетова С. С.",
    "website": "https://example.com", "addressStreet": "ул. Синтетическая, д. 1, оф. 2", "addressCity": "Тестовск",
    "addressState": "Московская обл.", "addressPostalCode": "101000",
}


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


def phone():
    return "+7 900 " + "".join(secrets.choice(string.digits) for _ in range(7))


def logo_png():
    """A synthetic logo (a blue square with «SP»), made at run time."""
    from PIL import Image, ImageDraw
    image = Image.new("RGB", (240, 120), (31, 58, 95))
    draw = ImageDraw.Draw(image)
    draw.rectangle((8, 8, 231, 111), outline=(255, 255, 255), width=4)
    draw.text((92, 50), "SYNTH", fill=(255, 255, 255))
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


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
            "userName": f"synth-print-{key}", "lastName": f"SYNTH-PRINT {key}", "firstName": "Менеджер",
            "type": "regular", "isActive": True, "password": password, "passwordConfirm": password,
            "rolesIds": [roles[role]], "emailAddress": f"synth-print-{key}@example.com", "phoneNumber": phone()}))
        state["users"][key] = user["id"]
        save_state(state)
        env.append(f"UI_{key.upper()}_USERNAME=synth-print-{key}\nUI_{key.upper()}_PASSWORD={password}\n")
    USERS_ENV.write_text("".join(env), encoding="utf-8")
    USERS_ENV.chmod(0o600)
    espo_console("itvolga-setup-acl")

    legal = must(admin.get("LegalEntity", maxSize=5))["list"][0]["id"]
    original = must(admin.get(f"LegalEntity/{legal}"))
    state["legalEntity"] = {"id": legal, "original": {f: original.get(f) for f in LEGAL_ENTITY_FIELDS}}
    save_state(state)
    logo = {}
    if not original.get("logoId"):
        logo = {"logoId": must(admin.post("Attachment", {
            "name": "synth-logo.png", "type": "image/png", "role": "Attachment", "relatedType": "LegalEntity",
            "field": "logo", "file": logo_png()}))["id"]}
        state["legalEntity"]["logoId"] = logo["logoId"]
        save_state(state)
    must(admin.put(f"LegalEntity/{legal}", {**SELLER, "phoneNumber": phone(), **logo}))

    def rec(entity, data):
        payload = must(admin.post(entity, data))
        state["records"].append([entity, payload["id"]])
        save_state(state)
        return payload["id"]

    director = state["users"]["director"]
    address = {"billingAddressPostalCode": "620000", "billingAddressState": "Свердловская обл.",
               "billingAddressCity": "Примерград", "billingAddressStreet": "пр. Образцов, 10"}
    acc = rec("Account", {"name": "ООО «Покупатель-Синтетика»", "cInn": "77-SYNTH-01", "cKpp": "770-SYNTH",
                          "phoneNumber": phone(), **address})
    contact = rec("Contact", {"firstName": "Иван", "lastName": "Синтетиков", "accountId": acc})
    monthly = rec("Product", {"name": "Абонентское обслуживание серверов", "type": "service", "unit": "мес.",
                              "unitPrice": "15000", "unitPriceCurrency": "RUB"})
    hours = rec("Product", {"name": "Работы по настройке сети", "type": "service", "unit": "Hours",
                            "unitPrice": "1800", "unitPriceCurrency": "RUB"})
    licence = rec("Product", {"name": "Лицензия на программу (синтетическая)", "type": "product", "unit": "Each",
                              "unitPrice": "12345.67", "unitPriceCurrency": "RUB"})
    reference_lines = [
        {"productId": monthly, "quantity": "1", "unitPrice": "15000", "description": "за октябрь 2026"},
        {"productId": hours, "quantity": "2.5", "unitPrice": "1800"},
    ]
    discount_lines = [*reference_lines,
                      {"productId": licence, "quantity": "2", "unitPrice": "12345.67", "discountPercent": "10"},
                      {"productId": hours, "quantity": "1", "unitPrice": "1800", "discountAmount": "300",
                       "description": "выезд специалиста\nв выходной день"}]
    common = {"accountId": acc, "assignedUserId": director, **address}
    terms = ("Предложение действительно 14 календарных дней. Оплата — 100 % предоплата по счёту.\n"
             "Сроки выполнения работ согласуются после оплаты.")
    state["quote"] = rec("Quote", {**common, "name": "Обслуживание и настройка (синтетика)", "contactId": contact,
                                   "dateValidUntil": "2026-10-17", "termsAndConditions": terms,
                                   "itemList": discount_lines})
    state["salesOrder"] = rec("SalesOrder", {**common, "name": "Обслуживание и настройка (синтетика)",
                                             "contactId": contact, "dateDue": "2026-10-31",
                                             "termsAndConditions": terms, "itemList": reference_lines})
    dates = {"dateInvoiced": "2026-10-03", "dateDue": "2026-10-17"}
    state["invoice"] = rec("Invoice", {**common, **dates, "name": "Обслуживание (синтетика)",
                                       "itemList": reference_lines})
    state["discountInvoice"] = rec("Invoice", {**common, **dates, "name": "Со скидками (синтетика)",
                                               "discountAmount": "1000", "shippingAmount": "500",
                                               "itemList": discount_lines})
    state["act"] = rec("Act", {**common, "name": "Обслуживание (синтетика)", "dateAct": "2026-10-03",
                               "itemList": reference_lines})
    number = must(admin.get(f"Invoice/{state['invoice']}"))["number"]
    payment = {"datePaid": "2026-10-03", "assignedUserId": director, "payerType": "Account", "payerId": acc}
    state["payment"] = rec("Payment", {**payment, "amount": "19500", "method": "cash", "documentNumber": "77",
                                       "purpose": f"Оплата по счёту № {number} от 03.10.2026",
                                       "allocationList": [{"invoiceId": state["invoice"], "amount": "19500"}]})
    state["outgoingPayment"] = rec("Payment", {**payment, "amount": "1200", "direction": "outgoing",
                                               "purpose": "Возврат (синтетика)"})
    save_state(state)
    print(json.dumps({k: v for k, v in state.items() if k not in ("records", "legalEntity")}, indent=2))


FORMS = {"invoice": "Invoice", "discountInvoice": "Invoice", "act": "Act", "payment": "Payment", "quote": "Quote",
         "salesOrder": "SalesOrder"}


def render():
    """Downloads the PDFs of the fixture as the director (the browser does the same through «Печать»)."""
    state = json.loads(STATE.read_text(encoding="utf-8"))
    env = dict(line.split("=", 1) for line in USERS_ENV.read_text(encoding="utf-8").split())
    director = Client(env["UI_DIRECTOR_USERNAME"], env["UI_DIRECTOR_PASSWORD"])
    out = PRIVATE / "pdf"
    out.mkdir(parents=True, exist_ok=True)
    out.chmod(0o700)
    for key, entity in FORMS.items():
        status, body, headers = director.entry_point("itvolgaPrint", entityType=entity, id=state[key])
        if status != 200:
            raise SystemExit(f"{key}: HTTP {status} {body!r:.300}")
        path = out / f"{key}.pdf"
        path.write_bytes(body)
        path.chmod(0o600)
        print(f"{key}: {len(body)} bytes, {headers.get('Content-Disposition', '')}")


def delete():
    admin = Client(*admin_credentials())
    state = json.loads(STATE.read_text(encoding="utf-8"))
    for entity, rid in reversed(state["records"]):
        admin.delete(f"{entity}/{rid}")
    if legal := state.get("legalEntity"):
        # Only the logo the fixture added is cleared (with its file), and only if it is still the current one.
        current = (must(admin.get(f"LegalEntity/{legal['id']}")) or {}).get("logoId")
        logo = {"logoId": None} if legal.get("logoId") and current == legal["logoId"] else {}
        must(admin.put(f"LegalEntity/{legal['id']}", {**legal["original"], **logo}))
    for rid in state["users"].values():
        admin.delete(f"User/{rid}")
    STATE.unlink()
    USERS_ENV.unlink(missing_ok=True)
    print("deleted")


if __name__ == "__main__":
    {"create": create, "render": render, "delete": delete}[sys.argv[1]]()
