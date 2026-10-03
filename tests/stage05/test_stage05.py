"""Stage 05 acceptance tests: print forms of the finance records (PDF) on the local stand, synthetic data only.

  task test:stage05

Each test downloads the PDF through the print entry point (?entryPoint=itvolgaPrint) as a user of a role and reads it
with poppler (pdftotext, pdfinfo, pdffonts, pdfimages): numbers, dates, requisites, lines, discounts, tax rows, totals,
amount in words, Cyrillic, A4, the embedded font; access of the roles; that printing writes nothing. The single legal
entity gets synthetic requisites for the run and its previous values back in the cleanup. Records carry «SYNTH-<run>»
and are removed by the module cleanup. Phone numbers are generated per run (no literal phone numbers in Git).
"""
import json
import re
import secrets
import string
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "stage03"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "stage04"))
from espo import Client, admin_credentials, espo_console, sql  # noqa: E402
from test_stage04_2 import must  # noqa: E402

RUN = secrets.token_hex(3)
TAG = f"SYNTH-{RUN}"
NBSP = " "
ENTRY = "itvolgaPrint"
SELLER = {
    "name": f"ООО «Синтетика {RUN}»", "inn": "50-SYNTH-02", "kpp": "500-SYNTH", "okpo": "SYNTH-OKPO",
    "bankAccount": "40702-810-SYNTH-0001", "bankName": "АО «ТЕСТ-БАНК», г. Тестовск", "bic": "04-SYNTH",
    "corrAccount": "30101-810-SYNTH-0002", "director": "Тестов Т. Т.", "bookkeeper": "Счетова С. С.",
    "addressStreet": "ул. Синтетическая, д. 1", "addressCity": "Тестовск", "addressState": "Московская обл.",
    "addressPostalCode": "101000", "website": "https://example.com",
}
# The logo is left as it is: replacing an image field makes the core delete the previous attachment, so a logo of
# the UI fixture could not be restored (the commercial offer test adds a temporary logo only when there is none).
LEGAL_FIELDS = [*SELLER, "phoneNumber", "addressCountry"]
ADDRESS = {"billingAddressPostalCode": "620000", "billingAddressState": "Свердловская обл.",
           "billingAddressCity": "Примерград", "billingAddressStreet": "пр. Образцов, 10"}
# Tables a print must not change (documents, lines, payments, allocations, numbering, files, history).
TABLES = ["invoice", "invoice_item", "act", "act_item", "quote", "quote_item", "sales_order", "sales_order_item",
          "payment", "payment_allocation", "legal_entity", "next_number", "attachment", "note", "action_history_record"]
S = {}


def setUpModule():
    S.update(created=[], users={}, clients={}, roles=[])
    unittest.addModuleCleanup(cleanup)
    admin = Client(*admin_credentials())
    S["admin"] = admin
    roles = {r["name"]: r["id"] for r in must(admin.get("Role", maxSize=50))["list"]}
    for key, role_ids in (("dir", [roles["Директор"]]), ("dep", [roles["Заместитель директора"]]),
                          ("sales", [roles["Менеджер по продажам"]]), ("norole", [])):
        password = secrets.token_urlsafe(18) + "Aa1!"
        user = must(admin.post("User", {
            "userName": f"synth-{RUN}-{key}", "firstName": "Менеджер", "lastName": f"{TAG} {key}",
            "type": "regular", "isActive": True, "password": password, "passwordConfirm": password,
            "rolesIds": role_ids, "sendAccessInfo": False, "emailAddress": f"synth-{RUN}-{key}@example.com",
            "phoneNumber": phone()}))
        S["users"][key] = user["id"]
        S["clients"][key] = Client(f"synth-{RUN}-{key}", password)
    espo_console("itvolga-setup-acl")

    legal = sql("SELECT id FROM legal_entity WHERE vtiger_company_key='Default' AND deleted=0")[0][0]
    original = must(admin.get(f"LegalEntity/{legal}"))
    S["legal"] = (legal, {f: original.get(f) for f in LEGAL_FIELDS})
    must(admin.put(f"LegalEntity/{legal}", {**SELLER, "phoneNumber": phone()}))
    S["timeZone"] = must(admin.get("Settings")).get("timeZone") or "UTC"

    S["phone"] = phone()
    S["account"] = create("Account", {"name": f"ООО «Покупатель {RUN}»", "cInn": "77-SYNTH-01", "cKpp": "770-SYNTH",
                                      "phoneNumber": S["phone"], **ADDRESS})["id"]
    S["contact"] = create("Contact", {"firstName": "Иван", "lastName": f"Синтетиков {RUN}",
                                      "accountId": S["account"]})["id"]
    S["monthly"] = create("Product", {"name": f"{TAG} Абонентское обслуживание", "type": "service",
                                      "unit": "мес."})["id"]
    S["hours"] = create("Product", {"name": f"{TAG} Настройка сети", "type": "service", "unit": "Hours"})["id"]
    S["licence"] = create("Product", {"name": f"{TAG} Лицензия", "type": "product", "unit": "Each"})["id"]
    S["nounit"] = create("Product", {"name": f"{TAG} Тег & «кавычки»", "type": "service"})["id"]


def cleanup():
    admin = S.get("admin")
    if not admin:
        return
    for entity, rid in reversed(S.get("created", [])):
        admin.delete(f"{entity}/{rid}")
    if S.get("legal"):
        legal, original = S["legal"]
        must(admin.put(f"LegalEntity/{legal}", original))
        restored = must(admin.get(f"LegalEntity/{legal}"))
        if any(restored.get(f) != v for f, v in original.items()):
            raise AssertionError("the legal entity was not restored")
    for rid in S.get("users", {}).values():
        admin.delete(f"User/{rid}")
    for rid in S.get("roles", []):
        admin.delete(f"Role/{rid}")


def phone():
    return "+7 900 " + "".join(secrets.choice(string.digits) for _ in range(7))


def create(entity, data, client=None):
    payload = must((client or S["clients"]["dir"]).post(entity, data))
    S["created"].append((entity, payload["id"]))
    return payload


def lines(*rows):
    return [{"productId": S[product] if product else None, "quantity": quantity, "unitPrice": price, **extra}
            for product, quantity, price, extra in rows]


REFERENCE = (("monthly", "1", "15000", {"description": "за октябрь 2026"}), ("hours", "2.5", "1800", {}))


def document(entity, rows=REFERENCE, **header):
    dates = {"Invoice": {"dateInvoiced": "2026-10-03", "dateDue": "2026-10-17"}, "Act": {"dateAct": "2026-10-03"}}
    return create(entity, {"name": f"{TAG} {entity}", "accountId": S["account"], "assignedUserId": S["users"]["dir"],
                           **dates.get(entity, {}), **ADDRESS, "itemList": lines(*rows), **header})


def download(entity, rid, client=None):
    return (client or S["clients"]["dir"]).entry_point(ENTRY, entityType=entity, id=rid)


def poppler(tool, pdf, *args):
    with tempfile.NamedTemporaryFile(suffix=".pdf") as fh:
        fh.write(pdf)
        fh.flush()
        return subprocess.run([tool, *args, fh.name, *(["-"] if tool == "pdftotext" else [])], check=True,
                              capture_output=True, text=True).stdout


def text(pdf, crop=None):
    """Text of the PDF (or of a region x, width in pt of the first page), NBSP and white space runs as one space."""
    args = ["-layout"] if crop is None else ["-layout", "-f", "1", "-l", "1", "-x", str(crop[0]), "-y", "0",
                                             "-W", str(crop[1]), "-H", "842"]
    return re.sub(r"\s+", " ", poppler("pdftotext", pdf, *args).replace(NBSP, " ")).strip()


# The cash receipt order: the order is the left 131 mm of the page (with the margin), the receipt the right part.
ORDER, RECEIPT = (0, 372), (372, 223)


def words_y(pdf, word):
    """Top coordinates (pt) of the occurrences of a word on the first page (pdftotext -bbox)."""
    html = poppler("pdftotext", pdf, "-bbox", "-f", "1", "-l", "1")
    return [float(m.group(1)) for m in re.finditer(r'<word xMin="[\d.]+" yMin="([\d.]+)"[^>]*>' + re.escape(word) + "<", html)]


def user_with_role(key, data, field_data=None):
    """A synthetic user of a synthetic role (finance access like the director, minus the given fields)."""
    admin = S["admin"]
    role = must(admin.post("Role", {"name": f"{TAG} {key}", "data": data, "fieldData": field_data or {}}))
    S["roles"].append(role["id"])
    password = secrets.token_urlsafe(18) + "Aa1!"
    user = must(admin.post("User", {"userName": f"synth-{RUN}-{key}", "lastName": f"{TAG} {key}", "type": "regular",
                                    "isActive": True, "password": password, "passwordConfirm": password,
                                    "rolesIds": [role["id"]], "sendAccessInfo": False}))
    S["users"][key] = user["id"]
    S["clients"][key] = Client(f"synth-{RUN}-{key}", password)
    return S["clients"][key]


READ_FINANCE = {scope: {"create": "no", "read": "all", "edit": "no", "delete": "no"}
                for scope in ("Invoice", "Quote", "Account", "Contact", "LegalEntity", "Product", "User")}
READ_FINANCE.update({scope: {"read": "all"} for scope in ("InvoiceItem", "QuoteItem")})


class PdfCase(unittest.TestCase):
    def pdf(self, entity, rid, client=None):
        status, body, headers = download(entity, rid, client)
        self.assertEqual(200, status, f"{entity}: HTTP {status}")
        self.assertTrue(body.startswith(b"%PDF-"), "not a PDF")
        self.assertEqual("application/pdf", headers.get("Content-Type"))
        self.assertIn("private, no-store", headers.get("Cache-Control", ""))
        return body, headers

    def assertPhrases(self, content, *phrases):
        for phrase in phrases:
            self.assertIn(phrase, content)


class InvoiceFormTest(PdfCase):
    @classmethod
    def setUpClass(cls):
        cls.invoice = document("Invoice")
        cls.body, cls.headers = PdfCase.pdf(cls(), "Invoice", cls.invoice["id"])
        cls.text = text(cls.body)

    def test_reproduces_the_source_invoice(self):
        seller, number = SELLER, self.invoice["number"]
        self.assertPhrases(self.text,
                           seller["name"], "101000, Московская обл., г. Тестовск, ул. Синтетическая, д. 1",
                           "Образец заполнения платежного поручения", f"ИНН {seller['inn']}", f"КПП {seller['kpp']}",
                           "Получатель", "Банк получателя", seller["bankName"], "БИК", seller["bic"],
                           seller["bankAccount"], seller["corrAccount"],
                           f"СЧЕТ № {number} от 3 октября 2026 г.",
                           f"Покупатель: ООО «Покупатель {RUN}», ИНН 77-SYNTH-01, КПП 770-SYNTH, 620000, "
                           f"Свердловская обл., г. Примерград, пр. Образцов, 10, тел.:",
                           "№ Наименование товара, работ, услуг Ед. изм. Кол-во Цена Сумма",
                           f"1 {TAG} Абонентское обслуживание за октябрь 2026 мес. 1 15 000,00 15 000,00",
                           f"2 {TAG} Настройка сети Часы 2,5 1 800,00 4 500,00",
                           "Итого: 19 500,00", "Без налога (НДС): --", "Всего к оплате: 19 500,00",
                           "Всего наименований 2, на сумму 19 500,00 руб.",
                           "Девятнадцать тысяч пятьсот рублей 00 копеек",
                           "Руководитель __________________ ( Тестов Т. Т. )")
        # The account phone as stored (EspoCRM keeps it in E.164).
        self.assertIn(S["phone"].replace(" ", ""), self.text.replace(" ", ""))
        self.assertNotIn("Скидка", self.text)

    def test_a4_portrait_one_page_liberation_sans_and_title(self):
        info = poppler("pdfinfo", self.body)
        self.assertRegex(info, r"Page size:\s+595\.\d+ x 841\.\d+ pts \(A4\)")
        self.assertRegex(info, r"Pages:\s+1\n")
        self.assertIn(f"Title:           Счёт {self.invoice['number']}", info)
        fonts = poppler("pdffonts", self.body)
        self.assertIn("LiberationSans", fonts)
        self.assertNotIn("DejaVu", fonts)
        self.assertEqual("", poppler("pdfimages", self.body, "-list").split("\n", 2)[2].strip())

    def test_file_name(self):
        disposition = self.headers.get("Content-Disposition", "")
        self.assertTrue(disposition.startswith('inline; filename="Invoice.pdf"; filename*=UTF-8\'\''))
        from urllib.parse import unquote
        self.assertEqual(f"Счёт {self.invoice['number']}.pdf", unquote(disposition.split("''", 1)[1]))


class DiscountsAndTotalsTest(PdfCase):
    def test_line_discounts_get_a_column_and_document_rows(self):
        invoice = document("Invoice", (
            *REFERENCE,
            ("licence", "2", "12345.67", {"discountPercent": "10"}),
            ("hours", "1", "1800", {"discountAmount": "300"})), discountAmount="1000", shippingAmount="500")
        content = text(self.pdf("Invoice", invoice["id"])[0])
        self.assertPhrases(content, "Кол-во Цена Скидка Сумма",
                           f"3 {TAG} Лицензия шт. 2 12 345,67 2 469,13 (10%) 22 222,21",
                           f"4 {TAG} Настройка сети Часы 1 1 800,00 300,00 1 500,00",
                           "Итого: 43 222,21", "Скидка: 1 000,00", "Доставка: 500,00", "Всего к оплате: 42 722,21",
                           "Сорок две тысячи семьсот двадцать два рубля 21 копейка")
        self.assertEqual("42722.21", str(invoice["grandTotal"]).rstrip("0").rstrip("."))

    def test_historical_tax_classes_print_stored_totals(self):
        # lineTaxNotApplied (2016–2018): 18 % in the lines, not in the totals — stored values, «Без налога (НДС)».
        plain = document("Invoice", (("hours", "2", "1000", {}), ("monthly", "1", "500", {})))
        sql(f"UPDATE invoice_item SET tax_rate=18 WHERE invoice_id='{plain['id']}'")
        content = text(self.pdf("Invoice", plain["id"])[0])
        self.assertPhrases(content, f"Настройка сети Часы 2 1 000,00 2 000,00", "Без налога (НДС): --",
                           "Всего к оплате: 2 500,00")
        self.assertNotIn("2 360,00", content)
        # groupTaxAdded (2 invoices of 2016–2017): total = pre-tax + 18 % — a VAT row reconciles lines and total.
        grouped = document("Invoice", (("hours", "2", "1000", {}), ("monthly", "1", "500", {})))
        sql(f"UPDATE invoice SET tax_mode='group', grand_total=2950 WHERE id='{grouped['id']}'")
        sql(f"UPDATE invoice_item SET tax_rate=18 WHERE invoice_id='{grouped['id']}'")
        content = text(self.pdf("Invoice", grouped["id"])[0])
        self.assertPhrases(content, "Итого: 2 500,00", "НДС: 450,00", "Всего к оплате: 2 950,00",
                           "Две тысячи девятьсот пятьдесят рублей 00 копеек")
        self.assertNotIn("Без налога", content)

    def test_buyer_address_of_the_document_then_of_the_account(self):
        own = document("Invoice", billingAddressCity="Другоград", billingAddressStreet="ул. Документная, 3",
                       billingAddressPostalCode=None, billingAddressState=None)
        self.assertIn("КПП 770-SYNTH, г. Другоград, ул. Документная, 3, тел.:", text(self.pdf("Invoice", own["id"])[0]))
        empty = document("Invoice", **{k: None for k in ADDRESS})
        self.assertIn("КПП 770-SYNTH, 620000, Свердловская обл., г. Примерград, пр. Образцов, 10",
                      text(self.pdf("Invoice", empty["id"])[0]))

    def test_values_are_printed_as_text_not_markup(self):
        invoice = document("Invoice", (("nounit", "1", "100", {"description": "<i>не курсив</i> & <br> ещё"}),))
        content = text(self.pdf("Invoice", invoice["id"])[0])
        self.assertIn(f"{TAG} Тег & «кавычки» <i>не курсив</i> & <br> ещё - 1 100,00 100,00", content)

    def test_empty_number_and_date_print_blanks(self):
        invoice = document("Invoice")
        sql(f"UPDATE invoice SET number=NULL, date_invoiced=NULL WHERE id='{invoice['id']}'")
        body, headers = self.pdf("Invoice", invoice["id"])
        self.assertIn("СЧЕТ № б/н от «___» __________ 20__ г.", text(body))
        # «/» cannot be in a file name: «Счёт б_н.pdf».
        self.assertTrue(headers["Content-Disposition"].endswith("%D0%B1_%D0%BD.pdf"))


class ActFormTest(PdfCase):
    def test_reproduces_the_source_act_with_every_line_in_the_table(self):
        act = document("Act", (("monthly", "1", "15000", {"description": "октябрь"}), REFERENCE[1],
                               ("licence", "3", "100", {})))
        body, _ = self.pdf("Act", act["id"])
        content = text(body)
        self.assertPhrases(content, f"Акт № {act['number']} от 3 октября 2026 г.",
                           f"Исполнитель: {SELLER['name']}, ИНН 50-SYNTH-02, 101000, Тестовск, ул. Синтетическая, д. 1",
                           f"Заказчик: ООО «Покупатель {RUN}», ИНН 77-SYNTH-01, КПП 770-SYNTH, 620000, "
                           "Свердловская обл., г. Примерград, пр. Образцов, 10",
                           "№ Услуга Количество Ед. Цена Сумма",
                           f"1 {TAG} Абонентское обслуживание. октябрь 1 мес. 15 000,00 15 000,00",
                           f"2 {TAG} Настройка сети 2,5 Часы 1 800,00 4 500,00",
                           f"3 {TAG} Лицензия 3 шт. 100,00 300,00",
                           "Сумма: 19 800,00 Без налога (НДС) Итого: 19 800,00",
                           "Всего оказано услуг 3, на сумму: 19 800,00 руб.",
                           "Девятнадцать тысяч восемьсот рублей 00 копеек",
                           "Вышеперечисленные работы выполнены в полном объеме и в установленный срок.",
                           "Исполнитель Заказчик", "(Тестов Т. Т.)")
        # All three rows are inside one table: they come before the totals in reading order.
        self.assertLess(content.index("3 " + TAG), content.index("Сумма: 19 800,00"))

    def test_long_act_repeats_the_table_header_and_prints_the_ending_once(self):
        rows = [("hours", "1", "10", {"description": f"строка {n}"}) for n in range(1, 61)]
        act = document("Act", rows)
        body, _ = self.pdf("Act", act["id"])
        pages = int(re.search(r"Pages:\s+(\d+)", poppler("pdfinfo", body)).group(1))
        content = text(body)
        self.assertGreater(pages, 1)
        self.assertEqual(1, content.count("Акт №"))
        self.assertGreaterEqual(content.count("№ Услуга Количество Ед. Цена Сумма"), 2)
        self.assertEqual(1, content.count("Итого: 600,00"))
        self.assertIn("строка 1 1", content)
        self.assertIn("строка 60 1", content)


class CashReceiptTest(PdfCase):
    def test_incoming_payment_prints_the_ko1_order_and_receipt(self):
        invoice = document("Invoice")
        payment = create("Payment", {"datePaid": "2026-10-03", "amount": "19500", "method": "cash",
                                     "documentNumber": "77", "assignedUserId": S["users"]["dir"],
                                     "payerType": "Account", "payerId": S["account"],
                                     "purpose": f"Оплата по счёту № {invoice['number']}",
                                     "allocationList": [{"invoiceId": invoice["id"], "amount": "19500"}]})
        body, headers = self.pdf("Payment", payment["id"])
        self.assertPhrases(text(body, ORDER), "Унифицированная форма КО-1", "Форма по ОКУД", "0310001",
                           "по ОКПО SYNTH-OKPO", SELLER["name"], "ПРИХОДНЫЙ КАССОВЫЙ ОРДЕР",
                           "Номер документа Дата составления", "77 03.10.2026", "19 500,00",
                           f"Принято от ООО «Покупатель {RUN}»", f"Основание Оплата по счёту № {invoice['number']}",
                           "Сумма Девятнадцать тысяч пятьсот рублей 00 копеек", "В том числе НДС (Без НДС)",
                           "Главный бухгалтер Счетова С. С.", "Получил кассир")
        self.assertPhrases(text(body, RECEIPT), SELLER["name"], "КВИТАНЦИЯ", "к ПКО № 77", "от 3 октября 2026 г.",
                           f"Принято от ООО «Покупатель {RUN}»", f"Основание Оплата по счёту № {invoice['number']}",
                           "Сумма 19 500,00", "Девятнадцать тысяч пятьсот рублей 00 копеек", "НДС (Без НДС)",
                           "М.П. (штампа)", "Главный бухгалтер", "Счетова С. С.", "Кассир")
        self.assertIn("%D0%9F%D0%9A%D0%9E%2077.pdf", headers["Content-Disposition"])

    def test_without_document_number_the_payment_number_is_printed(self):
        payment = create("Payment", {"datePaid": "2026-10-03", "amount": "100.5", "assignedUserId": S["users"]["dir"],
                                     "payerType": "Contact", "payerId": S["contact"]})
        body = self.pdf("Payment", payment["id"])[0]
        self.assertIn(f"{payment['number']} 03.10.2026", text(body, ORDER))
        self.assertIn(f"к ПКО № {payment['number']}", text(body, RECEIPT))
        self.assertIn(f"Принято от Иван Синтетиков {RUN}", text(body, ORDER))
        self.assertIn("Сто рублей 50 копеек", text(body, ORDER))

    def test_outgoing_payment_has_no_cash_receipt(self):
        payment = create("Payment", {"datePaid": "2026-10-03", "amount": "10", "direction": "outgoing",
                                     "assignedUserId": S["users"]["dir"]})
        status, body, _ = download("Payment", payment["id"])
        self.assertEqual(403, status)
        self.assertFalse((body or b"").startswith(b"%PDF"))


class OfferFormsTest(PdfCase):
    def created_date(self, table, rid):
        """Moves created_at to 22:30 UTC so the printed date depends on the system time zone (answer 4)."""
        sql(f"UPDATE {table} SET created_at='2026-10-02 22:30:00' WHERE id='{rid}'")
        moment = datetime(2026, 10, 2, 22, 30, tzinfo=timezone.utc).astimezone(ZoneInfo(S["timeZone"]))
# 22:30 UTC on 2 October is 2 or 3 October in any time zone of Russia: the month is October either way.
        return f"{moment.day} октября {moment.year} г."

    def test_commercial_offer(self):
        legal, _ = S["legal"]
        temporary = not must(S["admin"].get(f"LegalEntity/{legal}")).get("logoId")
        if temporary:
            logo = must(S["admin"].post("Attachment", {
                "name": "synth.png", "type": "image/png", "role": "Attachment", "relatedType": "LegalEntity",
                "field": "logo", "file": "data:image/png;base64," + png()}))
            must(S["admin"].put(f"LegalEntity/{legal}", {"logoId": logo["id"]}))
        try:
            quote = document("Quote", (*REFERENCE, ("licence", "1", "12345.67", {"discountPercent": "10"})),
                             contactId=S["contact"], dateValidUntil="2026-10-17")
            date = self.created_date("quote", quote["id"])
            body, _ = self.pdf("Quote", quote["id"])
        finally:
            if temporary:  # clearing the field removes the temporary attachment
                must(S["admin"].put(f"LegalEntity/{legal}", {"logoId": None}))
        content = text(body)
        self.assertPhrases(content, "КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ", f"№ {quote['number']} от {date}",
                           "Действительно до 17 октября 2026 г.", f"ООО «Покупатель {RUN}»",
                           f"Иван Синтетиков {RUN}", f"Менеджер {TAG} dir", f"synth-{RUN}-dir@example.com",
                           f"Предлагаем: {TAG} Quote", "Скидка, руб.", "1 234,57 (10%)", "11 111,10",
                           "Итого: 30 611,10", "Всего: 30 611,10 руб.",
                           "Тридцать тысяч шестьсот одиннадцать рублей 10 копеек",
                           # New quotes get the source terms as the default (vtiger_inventory_tandc).
                           "Счет действителен на протяжении 14 календарных дней",
                           "Руководитель", "( Тестов Т. Т. )")
        images = poppler("pdfimages", body, "-list").split("\n")[2:]
        self.assertEqual(1, len([line for line in images if line.strip()]), "the logo of the legal entity")

    def test_sales_order(self):
        order = document("SalesOrder", dateDue="2026-10-31", contactId=S["contact"])
        date = self.created_date("sales_order", order["id"])
        content = text(self.pdf("SalesOrder", order["id"])[0])
        self.assertPhrases(content, "ЗАКАЗ", f"№ {order['number']} от {date}", "Срок исполнения: 31 октября 2026 г.",
                           "ИСПОЛНИТЕЛЬ", "ЗАКАЗЧИК", f"Контактное лицо: Иван Синтетиков {RUN}",
                           "Всего к оплате: 19 500,00 руб.", "Девятнадцать тысяч пятьсот рублей 00 копеек")
        self.assertNotIn("Скидка", content)


class AccessTest(PdfCase):
    @classmethod
    def setUpClass(cls):
        cls.records = {"Invoice": document("Invoice")["id"], "Act": document("Act")["id"],
                       "Quote": document("Quote")["id"], "SalesOrder": document("SalesOrder")["id"],
                       "Payment": create("Payment", {"datePaid": "2026-10-03", "amount": "10",
                                                     "assignedUserId": S["users"]["dir"]})["id"]}

    def test_only_roles_with_finance_access_print(self):
        for entity, rid in self.records.items():
            self.pdf(entity, rid)
            self.pdf(entity, rid, S["admin"])
            for key in ("dep", "sales", "norole"):
                status, body, _ = download(entity, rid, S["clients"][key])
                self.assertEqual(403, status, f"{key} printed {entity}")

    def test_unknown_forms_records_and_parameters(self):
        dir_client = S["clients"]["dir"]
        self.assertEqual(404, dir_client.entry_point(ENTRY, entityType="Account", id=S["account"])[0])
        self.assertEqual(404, dir_client.entry_point(ENTRY, entityType="InvoiceItem", id="x")[0])
        self.assertEqual(404, dir_client.entry_point(ENTRY, entityType="Invoice", id="no-such-record")[0])
        self.assertEqual(400, dir_client.entry_point(ENTRY, entityType="Invoice")[0])
        stranger = Client(f"synth-{RUN}-nobody", secrets.token_urlsafe(12))
        self.assertEqual(401, stranger.entry_point(ENTRY, entityType="Invoice", id=self.records["Invoice"])[0])

    def test_printing_writes_nothing(self):
        before = sql("CHECKSUM TABLE " + ", ".join(TABLES))
        for entity, rid in self.records.items():
            for _ in range(2):
                self.pdf(entity, rid)
        download("Invoice", self.records["Invoice"], S["clients"]["dep"])
        self.assertEqual(before, sql("CHECKSUM TABLE " + ", ".join(TABLES)))


class ReviewFixesTest(PdfCase):
    """Findings of the quality review (stage 05): field access, the manager of a quote, long texts, the header."""

    def test_fields_the_user_may_not_read_are_not_printed(self):
        invoice = document("Invoice")
        client = user_with_role("fields", READ_FINANCE, {
            "Account": {"cInn": {"read": "no", "edit": "no"}},
            "LegalEntity": {"bankAccount": {"read": "no", "edit": "no"}}})
        espo_console("clear-cache")
        content = text(self.pdf("Invoice", invoice["id"], client)[0])
        self.assertNotIn("77-SYNTH-01", content)
        self.assertNotIn(SELLER["bankAccount"], content)
        self.assertIn("КПП 770-SYNTH", content)
        self.assertIn("Всего к оплате: 19 500,00", content)
        # The director (no field restriction) still prints them.
        self.assertIn("77-SYNTH-01", text(self.pdf("Invoice", invoice["id"])[0]))

    def test_a_forbidden_amount_refuses_the_print(self):
        invoice = document("Invoice")
        client = user_with_role("amounts", READ_FINANCE, {"Invoice": {"grandTotal": {"read": "no", "edit": "no"}}})
        espo_console("clear-cache")
        status, body, _ = download("Invoice", invoice["id"], client)
        self.assertEqual(403, status)
        self.assertFalse((body or b"").startswith(b"%PDF"))

    def test_only_records_the_user_may_read_are_printed(self):
        # A role that reads its own invoices and every account and the legal entity: the record decides.
        client = user_with_role("own", {**READ_FINANCE, "Invoice": {"create": "no", "read": "own", "edit": "no",
                                                                     "delete": "no"}})
        own = document("Invoice", assignedUserId=S["users"]["own"])
        foreign = document("Invoice")
        self.pdf("Invoice", own["id"], client)
        self.assertEqual(403, download("Invoice", foreign["id"], client)[0])

    def test_an_unreadable_account_refuses_the_print(self):
        client = user_with_role("noaccount", {**READ_FINANCE, "Account": {"create": "no", "read": "no", "edit": "no",
                                                                           "delete": "no"}})
        invoice = document("Invoice")
        self.assertEqual(403, download("Invoice", invoice["id"], client)[0])

    def test_a_forbidden_line_table_refuses_the_print(self):
        client = user_with_role("noitems", READ_FINANCE, {"Invoice": {"itemList": {"read": "no", "edit": "no"}}})
        invoice = document("Invoice")
        espo_console("clear-cache")
        self.assertEqual(403, download("Invoice", invoice["id"], client)[0])

    def test_saved_line_name_of_a_removed_product_follows_its_field_access(self):
        product = create("Product", {"name": f"{TAG} Удалённая услуга", "type": "service"})["id"]
        invoice = document("Invoice", ((None, "1", "10", {"productId": product}),))
        S["admin"].delete(f"Product/{product}")
        self.assertIn(f"{TAG} Удалённая услуга", text(self.pdf("Invoice", invoice["id"])[0]))
        client = user_with_role("hiddenname", READ_FINANCE, {"InvoiceItem": {"name": {"read": "no", "edit": "no"}}})
        espo_console("clear-cache")
        self.assertNotIn("Удалённая услуга", text(self.pdf("Invoice", invoice["id"], client)[0]))

    def test_forbidden_links_hide_their_blocks(self):
        invoice = document("Invoice")
        client = user_with_role("links", READ_FINANCE, {"Invoice": {"account": {"read": "no", "edit": "no"},
                                                                    "legalEntity": {"read": "no", "edit": "no"}}})
        espo_console("clear-cache")
        content = text(self.pdf("Invoice", invoice["id"], client)[0])
        for hidden in ("77-SYNTH-01", f"Покупатель {RUN}", SELLER["inn"], SELLER["bankAccount"], SELLER["name"]):
            self.assertNotIn(hidden, content)
        self.assertIn("Всего к оплате: 19 500,00", content)

    def test_cash_receipt_payer_follows_access(self):
        payment = create("Payment", {"datePaid": "2026-10-03", "amount": "10", "assignedUserId": S["users"]["dir"],
                                     "payerType": "Account", "payerId": S["account"]})
        payments = {**READ_FINANCE, "Payment": {"create": "no", "read": "all", "edit": "no", "delete": "no"}}
        hidden = user_with_role("nopayer", {**payments, "Account": {"create": "no", "read": "no", "edit": "no",
                                                                    "delete": "no"}})
        self.assertEqual(403, download("Payment", payment["id"], hidden)[0])
        masked = user_with_role("payerfield", payments, {"Payment": {"payer": {"read": "no", "edit": "no"}}})
        espo_console("clear-cache")
        order = text(self.pdf("Payment", payment["id"], masked)[0], ORDER)
        self.assertNotIn(f"Покупатель {RUN}", order)
        self.assertIn(f"Покупатель {RUN}", text(self.pdf("Payment", payment["id"])[0], ORDER))

    def test_a_long_word_wraps_inside_its_cell(self):
        url = "https://example.com/" + "verylongpath" * 10
        for entity, discount in (("Invoice", {}), ("Act", {"discountAmount": "1"})):
            record = document(entity, (("hours", "1", "10", {"description": url}), ("monthly", "1", "5", discount)))
            body, _ = self.pdf(entity, record["id"])
            right = max(float(m.group(1)) for m in re.finditer(r'xMax="([\d.]+)"',
                                                                 poppler("pdftotext", body, "-bbox", "-f", "1", "-l", "1")))
            self.assertLessEqual(right, 595.28 - 10 * 72 / 25.4 + 1, f"{entity}: text beyond the right margin")
            self.assertIn(url, re.sub(r"\s+", "", text(body)), entity)

    def test_quote_manager_contacts_only_of_a_readable_user(self):
        hidden = must(S["admin"].post("User", {
            "userName": f"synth-{RUN}-gone", "firstName": "Менеджер", "lastName": f"{TAG} gone", "type": "regular",
            "isActive": False, "emailAddress": f"synth-{RUN}-gone@example.com", "phoneNumber": phone()}))
        S["users"]["gone"] = hidden["id"]
        quote = document("Quote")
        # The director cannot assign a record to an inactive user; an imported quote can keep one (set as the import).
        sql(f"UPDATE quote SET assigned_user_id='{hidden['id']}' WHERE id='{quote['id']}'")
        content = text(self.pdf("Quote", quote["id"])[0])
        self.assertIn(f"Менеджер {TAG} gone", content)
        self.assertNotIn(f"synth-{RUN}-gone@example.com", content)

    def test_a_description_longer_than_a_page_is_printed_whole(self):
        description = "\n".join(f"LINE{n:03d}" for n in range(1, 151))
        for entity in ("Invoice", "Act", "Quote", "SalesOrder"):
            record = document(entity, (("hours", "1", "10", {"description": description}), ("monthly", "1", "5", {})))
            body, _ = self.pdf(entity, record["id"])
            content = text(body)
            self.assertIn("LINE150", content, entity)
            self.assertEqual(150, len(re.findall(r"LINE\d{3}", content)), entity)
            self.assertLess(content.index("LINE150"), content.rindex(f"{TAG} Абонентское обслуживание"), entity)

    def test_a_long_wrapped_description_in_the_narrowest_column_is_printed_whole(self):
        # Act with a discount column: the name column is the narrowest (150 pt); wide letters wrap the most.
        description = "WWWWWWWWWW " * 180 + "ENDMARKER"
        act = document("Act", (("hours", "1", "10", {"description": description}),
                               ("monthly", "1", "5", {"discountAmount": "1"})))
        content = text(self.pdf("Act", act["id"])[0])
        self.assertEqual(180, content.count("WWWWWWWWWW"))
        self.assertIn("ENDMARKER", content)

    def test_a_long_header_pushes_the_table_down(self):
        long = {"billingAddressStreet": "проспект " + "Очень-Длинный-Синтетический " * 8,
                "billingAddressCity": "Город " + "Длинное-Название " * 4}
        for entity, header in (("Invoice", "Наименование"), ("Act", "Услуга")):
            record = document(entity, **long)
            body, _ = self.pdf(entity, record["id"])
            self.assertLess(max(words_y(body, "Очень-Длинный-Синтетический")), min(words_y(body, header)), entity)

    def test_sales_order_shares_the_discount_column_of_the_offer(self):
        order = document("SalesOrder", (*REFERENCE, ("licence", "1", "12345.67", {"discountPercent": "10"})))
        content = text(self.pdf("SalesOrder", order["id"])[0])
        self.assertPhrases(content, "Скидка, руб.", "1 234,57 (10%)", "Итого: 30 611,10",
                           "Всего к оплате: 30 611,10 руб.")


class RegistryTest(unittest.TestCase):
    def test_every_form_has_its_files_and_entity(self):
        repo = Path(__file__).resolve().parents[2]
        module = repo / "custom/Espo/Modules/Itvolga"
        forms = json.loads((module / "Resources/metadata/app/itvolgaFinance.json").read_text())["printForms"]
        self.assertEqual({"Invoice", "Act", "Payment", "Quote", "SalesOrder"}, set(forms))
        for entity, form in forms.items():
            names = [form["template"] + ".html", form.get("style", form["template"]) + ".css", "common.css"]
            for name in names + ([form["partials"] + ".html"] if "partials" in form else []):
                self.assertTrue((module / "Resources/printForms" / name).is_file(), f"{entity}: {name}")
            defs = json.loads((module / f"Resources/metadata/entityDefs/{entity}.json").read_text())
            self.assertTrue(form["dateField"] == "createdAt" or form["dateField"] in defs["fields"], entity)
        self.assertEqual({10: "Invoice", 11: "Act", 5: "Payment"},
                         {f["sourceTemplateId"]: e for e, f in forms.items() if "sourceTemplateId" in f})


def png(width=40, height=20):
    """A synthetic one-colour PNG made with the standard library (the logo of the legal entity)."""
    import base64
    import struct
    import zlib

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    rows = b"".join(b"\x00" + b"\x1f\x3a\x5f" * width for _ in range(height))
    raw = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))
    return base64.b64encode(raw).decode()


if __name__ == "__main__":
    unittest.main()
