"""Stage 04.3 acceptance tests on the local stand: Invoice and InvoiceItem (synthetic data).

Run: task test:stage04   (or: python3 -m unittest tests.stage04.test_stage04_3 from tests/stage04)

Covers: model and DB columns, the generated status dictionary, the С- numbering, a multi-line invoice calculated by the
core (D-29, D-47), required dates, re-saves that must not change sums, imported invoices of every formula class with
their control totals («Пересчёт ядра» for rounded/mismatch, «Итоги Vtiger» after a recalculation), both source
spellings of the single legal entity (Default, По умолчанию) on the import path, «Создать счёт» from a quote and a
sales order, reverse links and access (director only; items follow their invoice; no direct item writes). Every record,
user and role is created by the run (names start with SYNTH-<run id>) and deleted at the end; imports are simulated by
SQL on synthetic records, then classified by itvolga-finance-verify (it saves with SaveOption::IMPORT, as the
importer of stage 06.3 will).
"""
import json
import secrets
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "stage03"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from espo import REPO, Client, admin_credentials, espo_console, sql  # noqa: E402
from test_stage04_2 import label, must, ok  # noqa: E402

RUN = secrets.token_hex(3)
TAG = f"SYNTH-{RUN}"
VT_BASE = 900_000_000 + secrets.randbelow(90_000_000)
DATES = {"dateInvoiced": "2026-10-02", "dateDue": "2026-10-16"}
MONEY = {"subtotal", "discount_amount", "shipping_amount", "adjustment", "pre_tax_total", "grand_total",
         "balance_source", "expected_subtotal", "expected_pre_tax_total", "expected_grand_total", "source_subtotal",
         "source_pre_tax_total", "source_grand_total"}
CONTROL = ["expectedSubtotal", "expectedPreTaxTotal", "expectedGrandTotal", "sourceSubtotal", "sourcePreTaxTotal",
           "sourceGrandTotal"]
S = {}


def setUpModule():
    S.update(created=[], users={}, clients={})
    unittest.addModuleCleanup(cleanup)
    admin = Client(*admin_credentials())
    S["admin"] = admin
    roles = {r["name"]: r["id"] for r in must(admin.get("Role", maxSize=50))["list"]}
    # Items follow their invoice whatever the item's own level (Invoice own, InvoiceItem all on purpose).
    own_role = must(admin.post("Role", {"name": f"{TAG} own invoices", "data": {
        "Invoice": {"create": "yes", "read": "own", "edit": "own", "delete": "own"},
        "InvoiceItem": {"read": "all"}, "Product": {"read": "all"}, "Account": {"read": "all"}}}))
    S["own_role"] = own_role["id"]
    for key, role_ids in (("dir", [roles["Директор"]]), ("dep", [roles["Заместитель директора"]]),
                          ("sales", [roles["Менеджер по продажам"]]), ("cust", [roles["Менеджер клиентов"]]),
                          ("own", [own_role["id"]]), ("norole", [])):
        password = secrets.token_urlsafe(18) + "Aa1!"
        user = must(admin.post("User", {
            "userName": f"synth-{RUN}-{key}", "lastName": f"{TAG} {key}", "type": "regular", "isActive": True,
            "password": password, "passwordConfirm": password, "rolesIds": role_ids, "sendAccessInfo": False}))
        S["users"][key] = user["id"]
        S["clients"][key] = Client(f"synth-{RUN}-{key}", password)
    espo_console("itvolga-setup-acl")
    S["account"] = create("Account", {"name": f"{TAG} account"})["id"]
    S["contact"] = create("Contact", {"lastName": f"{TAG} contact", "accountId": S["account"]})["id"]
    S["opportunity"] = create("Opportunity", {"name": f"{TAG} deal", "accountId": S["account"], "stage": "Qualification",
                                              "closeDate": "2026-12-31"})["id"]
    S["product"] = create("Product", {"name": f"{TAG} service", "unitPrice": "1500.00", "unitPriceCurrency": "RUB"})["id"]
    S["product2"] = create("Product", {"name": f"{TAG} product", "type": "product"})["id"]
    S["legalEntity"] = sql("SELECT id FROM legal_entity WHERE vtiger_company_key='Default' AND deleted=0")[0][0]


def cleanup():
    admin = S.get("admin")
    if not admin:
        return
    for entity, rid in reversed(S.get("created", [])):
        admin.delete(f"{entity}/{rid}")
    for rid in S.get("users", {}).values():
        admin.delete(f"User/{rid}")
    if S.get("own_role"):
        admin.delete(f"Role/{S['own_role']}")


def create(entity, data, client=None):
    payload = must((client or S["admin"]).post(entity, data))
    S["created"].append((entity, payload["id"]))
    return payload


def c(key):
    return S["clients"][key]


def line(product=None, **values):
    return {"productId": product or S["product"], "quantity": "1", "unitPrice": "100", **values}


def invoice(lines, client=None, **header):
    return create("Invoice", {"name": f"{TAG} invoice", "accountId": S["account"], **DATES, "itemList": lines,
                              **header}, client or c("dir"))


def counter():
    return int(sql("SELECT value FROM next_number WHERE entity_type='Invoice' AND field_name='number'")[0][0])


def counts():
    return (sql("SELECT COUNT(*) FROM invoice")[0][0], sql("SELECT COUNT(*) FROM invoice_item")[0][0], counter())


def get(iid, client="admin"):
    return must((S["admin"] if client == "admin" else c(client)).get(f"Invoice/{iid}"))


def totals(got):
    return got["subtotal"], got["preTaxTotal"], got["grandTotal"]


def item_rows(iid):
    """Every stored value of the invoice's lines (items are saved silently: modified_at would not show a rewrite)."""
    return sql("SELECT id, `order`, deleted, product_id, name, description, quantity, unit_price, discount_amount, "
               "discount_percent, tax_rate, amount, purchase_cost, margin FROM invoice_item "
               f"WHERE invoice_id='{iid}' ORDER BY `order`")


def imported(lines, stored, tax_rate="0", tax_mode="individual", data=None, prefix="СЧЕТ_", **columns):
    """An invoice as the importer would write it: created through the API, then given source values by SQL
    (synthetic only), then classified by itvolga-finance-verify. Returns (id, vtiger id, console output)."""
    iid = invoice(lines)["id"]
    vt = VT_BASE + secrets.randbelow(10_000_000)
    data = {"region_id": None, "spcompany": "Default", **(data or {})}
    # Source numbers far above the counter: both historical formats, never a number the counter could reach.
    sets = {"vtiger_id": vt, "number": f"{prefix}{vt}", "tax_mode": tax_mode, "subtotal": stored[0],
            "pre_tax_total": stored[1], "grand_total": stored[2], "status": "Paid", "balance_source": stored[2],
            **columns}
    assignments = ", ".join(f"{k}={quote_sql(v)}" for k, v in sets.items())
    sql(f"UPDATE invoice SET {assignments}, vtiger_data={quote_sql(json.dumps(data, ensure_ascii=False))} "
        f"WHERE id='{iid}'")
    sql(f"UPDATE invoice_item SET tax_rate={tax_rate}, margin=0 WHERE invoice_id='{iid}'")
    return iid, vt, espo_console("itvolga-finance-verify", "--entity=Invoice", f"--id={iid}")


def quote_sql(value):
    if value is None:
        return "NULL"
    if isinstance(value, int):
        return str(value)
    return "'" + str(value).replace("\\", "\\\\").replace("'", "''") + "'"


# ---------------------------------------------------------------------------------------------------- model
class ModelTest(unittest.TestCase):
    def test_columns_are_decimal_dates_and_numbers(self):
        def decimals(table):
            return {r[0]: r[1] for r in sql(
                "SELECT column_name, CONCAT(numeric_precision, ',', numeric_scale) FROM information_schema.columns "
                f"WHERE table_schema=DATABASE() AND table_name='{table}' AND data_type='decimal'")}
        head = decimals("invoice")
        self.assertEqual({k: head.get(k) for k in MONEY}, dict.fromkeys(MONEY, "25,8"))
        self.assertEqual((head["discount_percent"], head["shipping_tax_percent"]), ("25,3", "25,3"))
        self.assertEqual(decimals("invoice_item"), decimals("quote_item"), "items: the contract Item structure")
        for table in ("quote", "sales_order"):
            columns = decimals(table)
            self.assertEqual({k: columns.get(k) for k in MONEY - {"balance_source"}},
                             dict.fromkeys(MONEY - {"balance_source"}, "25,8"), f"control totals of {table}")
        types = dict(sql("SELECT column_name, column_type FROM information_schema.columns WHERE "
                         "table_schema=DATABASE() AND table_name='invoice' AND column_name IN "
                         "('date_invoiced', 'date_due', 'number')"))
        self.assertEqual(types, {"date_invoiced": "date", "date_due": "date", "number": "varchar(100)"})
        self.assertEqual(sql("SELECT non_unique FROM information_schema.statistics WHERE table_schema=DATABASE() "
                             "AND table_name='invoice' AND column_name='vtiger_id'"), [["0"]])

    def test_metadata(self):
        defs = ok(self, S["admin"].get("Metadata"))["entityDefs"]
        fields = defs["Invoice"]["fields"]
        self.assertEqual(fields["status"]["options"], ["", "AutoCreated", "Cancel", "Created", "Approved", "Sent",
                                                       "Credit Invoice", "Paid"])
        self.assertEqual(fields["status"]["default"], "Created")
        self.assertTrue(fields["dateInvoiced"]["required"] and fields["dateDue"]["required"])
        for activity in ("Task", "Call", "Meeting"):
            self.assertIn("Invoice", defs[activity]["fields"]["parent"]["entityList"], activity)
        # Copied from the sales order template: no link of SalesOrder's own (invoices) may come along.
        self.assertEqual(set(defs["Invoice"]["links"]), {
            "items", "account", "contact", "opportunity", "legalEntity", "assignedUser", "teams", "documents",
            "createdBy", "modifiedBy", "salesOrder", "quote", "vtigerArchives", "meetings", "calls", "tasks", "emails"})
        # The common Document fields stay identical across the finance documents (finance-contract.md §11).
        keys = ("type", "precision", "scale", "readOnly", "onlyDefaultCurrency", "options", "view")
        for name, spec in defs["Quote"]["fields"].items():
            if name in fields and name not in ("status", "number"):
                for entity in ("SalesOrder", "Invoice"):
                    other = defs[entity]["fields"][name]
                    self.assertEqual({k: spec.get(k) for k in keys}, {k: other.get(k) for k in keys}, f"{entity}.{name}")
        registry = json.loads((REPO / "custom/Espo/Modules/Itvolga/Resources/metadata/app/itvolgaFinance.json")
                              .read_text(encoding="utf-8"))["documents"]["Invoice"]
        self.assertEqual((registry["numberPrefix"], registry["firstNumber"]), ("С-", 637), "Cyrillic С")
        self.assertGreaterEqual(counter(), 637)


# ---------------------------------------------------------------------------------------------------- calculation
class CalculationTest(unittest.TestCase):
    def test_multi_line_invoice(self):
        number = counter()
        created = invoice([
            line(quantity="2.5", unitPrice="1333.33", discountPercent="7.5", purchaseCost="100"),
            line(S["product2"], quantity="3", unitPrice="33.335", discountAmount="0.01", description="Часы"),
            line(unitPrice="0.005"), line(unitPrice="0.005"),
            line(quantity="4", unitPrice="250"), line(quantity="0.25", unitPrice="1500"),
        ], discountAmount="58.35", shippingAmount="150", adjustment="-0.5", contactId=S["contact"],
            opportunityId=S["opportunity"])
        got = get(created["id"], "dir")
        self.assertEqual(got["number"], f"С-{number}")
        self.assertEqual(counter(), number + 1)
        # Lines rounded to kopecks one by one (D-29): 0.005 + 0.005 → 0.01 + 0.01.
        self.assertEqual([(i["order"], i["amount"]) for i in got["itemList"]], [
            (1, "3083.33000000"), (2, "100.00000000"), (3, "0.01000000"), (4, "0.01000000"), (5, "1000.00000000"),
            (6, "375.00000000")])
        self.assertEqual(got["itemList"][0]["margin"], "2983.33000000")
        self.assertEqual(totals(got), ("4558.35000000", "4650.00000000", "4649.50000000"))
        self.assertEqual((got["status"], got["legalEntityId"], got["grandTotalCurrency"], got["dateInvoiced"],
                          got["dateDue"], got["contactId"], got["opportunityId"]),
                         ("Created", S["legalEntity"], "RUB", DATES["dateInvoiced"], DATES["dateDue"], S["contact"],
                          S["opportunity"]))
        self.assertEqual([got[f] for f in ["sourceFormula", "totalsCheck", *CONTROL]], ["", ""] + [None] * 6)
        self.assertEqual(ok(self, c("dir").get(f"Invoice/{created['id']}/items"))["total"], 6)

    def test_dates_are_required_and_refusals_change_nothing(self):
        before = counts()
        for missing in ("dateInvoiced", "dateDue"):
            data = {"name": f"{TAG} no date", "accountId": S["account"], **DATES, "itemList": [line()]}
            del data[missing]
            result = c("dir").post("Invoice", data)
            self.assertEqual((result[0], label(result)), (400, "validationFailure"), missing)
            self.assertEqual(result[1]["messageTranslation"]["data"]["field"], missing)
        for data, expected in (({"itemList": [line(quantity=1.5)]}, "financeFloat"),
                               ({"itemList": [line(), line(taxRate="18")]}, "financeVat"),
                               ({"itemList": []}, "financeNoLines")):
            result = c("dir").post("Invoice", {"name": f"{TAG} refused", "accountId": S["account"], **DATES, **data})
            self.assertEqual((result[0], label(result)), (400, expected))
        self.assertEqual(counts(), before, "no invoice, item or number is taken")

    def test_resave_does_not_change_sums(self):
        created = invoice([line(quantity="2.5", unitPrice="1333.33"), line(quantity="3", unitPrice="33.335")])
        iid = created["id"]
        first = get(iid, "dir")
        stored = item_rows(iid)
        same = ok(self, c("dir").put(f"Invoice/{iid}", {"itemList": first["itemList"], "status": "Sent"}))
        respelled = [{**first["itemList"][0], "quantity": "2.500", "unitPrice": "1333.33000000"},
                     {**first["itemList"][1], "quantity": "3", "unitPrice": "33.33500"}]
        again = ok(self, c("dir").put(f"Invoice/{iid}", {"itemList": respelled, "description": "повтор"}))
        for saved in (same, again, get(iid, "dir")):
            self.assertEqual((totals(saved), saved["number"]), (totals(first), first["number"]))
        self.assertEqual(get(iid)["status"], "Sent")
        self.assertEqual(item_rows(iid), stored, "equivalent values change no stored line value")

    def test_preview_and_cascade(self):
        before = counts()
        preview = ok(self, c("dir").request("POST", "FinanceDocument/Invoice/calculate", {"attributes": {
            "itemList": [line(quantity="2", unitPrice="10")], "shippingAmount": "5"}}))
        self.assertEqual((preview["grandTotal"], preview["lines"][0]["amount"]), ("25.00", "20.00"))
        self.assertEqual(counts(), before)
        created = must(c("dir").post("Invoice", {"name": f"{TAG} del", "accountId": S["account"], **DATES,
                                                 "itemList": [line(), line()]}))
        self.assertEqual(c("dir").delete(f"Invoice/{created['id']}")[0], 200)
        self.assertEqual(sql(f"SELECT COUNT(*), SUM(deleted) FROM invoice_item WHERE invoice_id='{created['id']}'"),
                         [["2", "2"]])


# ---------------------------------------------------------------------------------------------------- imported invoices
class ImportedInvoiceTest(unittest.TestCase):
    """Source totals are the reference (D-05): the core recomputes them only to compare (D-46), the recomputation is
    shown next to a rounded or mismatching mark, and a recalculation keeps the Vtiger totals for the director."""

    def assert_kept(self, iid, stored, number):
        got = get(iid)
        self.assertEqual((totals(got), got["number"], got["status"], got["balanceSource"]),
                         (stored, number, "Paid", stored[2]))
        return got

    def test_formula_classes_are_exact(self):
        two = [line(quantity="2", unitPrice="1000"), line(unitPrice="500")]
        cases = [
            ("lineTaxNotApplied", dict(tax_rate="18"), ("2500.00000000",) * 3),
            ("taxIncludedInPrice", dict(tax_rate="18", tax_mode="group_tax_inc"), ("2500.00000000",) * 3),
            ("groupTaxAdded", dict(tax_rate="18", tax_mode="group"), ("2500.00000000", "2500.00000000",
                                                                      "2950.00000000")),
            ("noLineTax", dict(data={"region_id": 0}), ("2500.00000000",) * 3),
        ]
        for formula, options, stored in cases:
            iid, vt, out = imported(two, stored, **options)
            self.assertIn(f"Invoice: {formula} / exact — 1", out)
            got = self.assert_kept(iid, stored, f"СЧЕТ_{vt}")
            self.assertEqual([got[f] for f in CONTROL[:3]], list(stored), "the recomputation equals the source")
            self.assertEqual([i["taxRate"] for i in got["itemList"]], [f"{options.get('tax_rate', '0')}.000"] * 2)

    def test_discrepancies_are_shown_not_corrected(self):
        cases = [
            # 3 × 33.335 = 100.005 kept by Vtiger as 100.01: equal after rounding to kopecks.
            ([line(quantity="3", unitPrice="33.335")], ("100.01000000",) * 3, "rounded", "100.00500000"),
            ([line(unitPrice="5000")], ("5000.01000000",) * 3, "mismatch", "5000.00000000"),
        ]
        for lines, stored, check, expected in cases:
            iid, vt, out = imported(lines, stored, data={"region_id": 0}, prefix="С-")
            self.assertIn(f"Invoice: noLineTax / {check} — 1", out)
            got = self.assert_kept(iid, stored, f"С-{vt}")
            self.assertEqual([got[f] for f in CONTROL[:3]], [expected] * 3)
        iid, _, out = imported([line()], ("105.00000000",) * 3, data={"region_id": 0}, shipping_amount=5)
        self.assertIn("Invoice: unverified / unverified — 1", out)
        self.assertEqual([get(iid)[f] for f in CONTROL[:3]], [None] * 3, "no confirmed formula, no recomputation")

    def test_resave_without_distortion(self):
        stored = ("2500.00000000", "2500.00000000", "2950.00000000")
        iid, vt, _ = imported([line(quantity="2", unitPrice="1000"), line(unitPrice="500")], stored, tax_rate="18",
                              tax_mode="group")
        first = get(iid, "dir")
        stored_lines = item_rows(iid)
        ok(self, c("dir").put(f"Invoice/{iid}", {"itemList": first["itemList"], "description": "без изменения сумм"}))
        respelled = [{**first["itemList"][0], "quantity": "2", "unitPrice": "1000"},
                     {**first["itemList"][1], "quantity": "1.000", "unitPrice": "500.00000000", "taxRate": "18"}]
        ok(self, c("dir").put(f"Invoice/{iid}", {"itemList": respelled, "status": "Paid"}))
        got = self.assert_kept(iid, stored, f"СЧЕТ_{vt}")
        self.assertEqual((got["sourceFormula"], got["totalsCheck"], got["expectedGrandTotal"]),
                         ("groupTaxAdded", "exact", "2950.00000000"))
        self.assertEqual(item_rows(iid), stored_lines, "source line amounts, margins and rates stay as imported")
        self.assertEqual([i["taxRate"] for i in got["itemList"]], ["18.000", "18.000"])

    def test_recalculation_keeps_vtiger_totals_for_the_director(self):
        stored = ("2500.00000000",) * 3
        iid, vt, _ = imported([line(quantity="2", unitPrice="1000"), line(unitPrice="500")], stored, tax_rate="18")
        lines = get(iid, "dir")["itemList"]
        refused = c("dir").put(f"Invoice/{iid}", {"itemList": [{**lines[0], "quantity": "3"}, lines[1]]})
        self.assertEqual((refused[0], label(refused)), (400, "financeVat"), "historical VAT is never recalculated")
        edited = ok(self, c("dir").put(f"Invoice/{iid}", {"itemList": [
            {**lines[0], "quantity": "3", "taxRate": "0"}, {**lines[1], "taxRate": "0"}]}))
        self.assertEqual(totals(edited), ("3500.00000000",) * 3)
        self.assertEqual([edited[f] for f in ["sourceFormula", "totalsCheck", *CONTROL]],
                         ["", "", None, None, None, *stored])
        self.assertNotIn("vtigerData", get(iid, "dir"), "the snapshot itself is for administrators")
        snapshot = get(iid)["vtigerData"]["sourceTotals"]
        self.assertEqual((snapshot["grandTotal"], snapshot["expectedGrandTotal"], snapshot["sourceFormula"]),
                         ("2500.00000000", "2500.00000000", "lineTaxNotApplied"))
        again = ok(self, c("dir").put(f"Invoice/{iid}", {"discountAmount": "100"}))
        self.assertEqual((again["grandTotal"], [again[f] for f in CONTROL[3:]]), ("3400.00000000", list(stored)))
        self.assertEqual(get(iid)["vtigerData"]["sourceTotals"], snapshot, "written once")
        got = get(iid)
        self.assertEqual((got["number"], got["status"], got["balanceSource"]), (f"СЧЕТ_{vt}", "Paid", stored[2]))
        self.assertIn("Invoice: recalculated in EspoCRM (skipped) — 1",
                      espo_console("itvolga-finance-verify", "--entity=Invoice", f"--id={iid}"))

    def test_control_fields_are_read_only(self):
        stored = ("100.01000000",) * 3
        iid, vt, _ = imported([line(quantity="3", unitPrice="33.335")], stored, data={"region_id": 0})
        before = get(iid)
        ok(self, c("dir").put(f"Invoice/{iid}", {
            "balanceSource": "1", "number": "x", "vtigerId": 1, "sourceFormula": "groupTaxAdded", "totalsCheck": "exact",
            **{f: "1" for f in CONTROL}}))
        after = get(iid)
        for f in ["balanceSource", "number", "vtigerId", "sourceFormula", "totalsCheck", *CONTROL]:
            self.assertEqual(after[f], before[f], f)

    def test_due_date_of_an_imported_invoice(self):
        iid, _, _ = imported([line()], ("100.00000000",) * 3, data={"region_id": 0}, date_due=None)
        self.assertEqual(c("dir").put(f"Invoice/{iid}", {"status": "Sent"})[0], 200, "a partial update is allowed")
        refused = c("dir").put(f"Invoice/{iid}", {"dateDue": None})
        self.assertEqual((refused[0], label(refused)), (400, "validationFailure"))
        self.assertEqual(totals(get(iid)), ("100.00000000",) * 3)


# ---------------------------------------------------------------------------------------------------- legal entity
class LegalEntityImportTest(unittest.TestCase):
    """Both source spellings (and the empty value) are the single legal entity (D-04, D-48); another value stops the
    import without creating a second legal entity and without printing the value."""

    def test_known_spellings_resolve_to_the_single_legal_entity(self):
        for spelling in ("Default", "По умолчанию", "", None, "(no key)"):
            iid = invoice([line()])["id"]
            data = {"region_id": 0} if spelling == "(no key)" else {"region_id": 0, "spcompany": spelling}
            sql(f"UPDATE invoice SET vtiger_id={VT_BASE + secrets.randbelow(10_000_000)}, legal_entity_id=NULL, "
                f"vtiger_data={quote_sql(json.dumps(data, ensure_ascii=False))} WHERE id='{iid}'")
            self.assertIn("Invoice: noLineTax / exact — 1",
                          espo_console("itvolga-finance-verify", "--entity=Invoice", f"--id={iid}"))
            got = get(iid)
            self.assertEqual(got["legalEntityId"], S["legalEntity"], spelling)
            self.assertEqual(got["vtigerData"].get("spcompany", "(no key)"), spelling, "the source value is kept")
        self.assertEqual(sql("SELECT COUNT(*) FROM legal_entity WHERE deleted=0"), [["1"]])

    def test_unknown_value_stops_the_import(self):
        iid = invoice([line()])["id"]
        unknown = f"{TAG} Holding"
        sql(f"UPDATE invoice SET vtiger_id={VT_BASE + secrets.randbelow(10_000_000)}, legal_entity_id=NULL, "
            f"vtiger_data={quote_sql(json.dumps({'region_id': 0, 'spcompany': unknown}))} WHERE id='{iid}'")
        run = subprocess.run([str(REPO / "scripts/stand/espo.sh"), "itvolga-finance-verify", "--entity=Invoice",
                              f"--id={iid}"], capture_output=True, text=True)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("Unknown spcompany value", run.stdout + run.stderr)
        self.assertNotIn(unknown, run.stdout + run.stderr, "the value is never printed")
        self.assertEqual(sql(f"SELECT legal_entity_id IS NULL, source_formula FROM invoice WHERE id='{iid}'"),
                         [["1", ""]], "nothing is written")
        self.assertEqual(sql("SELECT COUNT(*) FROM legal_entity WHERE deleted=0"), [["1"]])


# ---------------------------------------------------------------------------------------------------- conversion, links
class ConversionTest(unittest.TestCase):
    def test_create_invoice_from_quote_and_sales_order(self):
        quote = create("Quote", {"name": f"{TAG} quote", "accountId": S["account"], "shippingAmount": "5",
                                 "itemList": [line(quantity="2", unitPrice="10", description="копия")]}, c("dir"))
        attributes = ok(self, c("dir").get(f"FinanceDocument/Quote/{quote['id']}/convertTo/Invoice"))
        self.assertEqual((attributes["quoteId"], attributes["accountId"], attributes["shippingAmount"]),
                         (quote["id"], S["account"], "5.00000000"))
        for absent in ("number", "salesOrderId", "dateInvoiced", "dateDue", "vtigerId", "balanceSource", *CONTROL):
            self.assertNotIn(absent, attributes)
        self.assertTrue(all("id" not in x and "amount" not in x for x in attributes["itemList"]))
        from_quote = create("Invoice", {**attributes, **DATES}, c("dir"))
        got = get(from_quote["id"], "dir")
        self.assertEqual((got["number"][:2], got["grandTotal"], got["itemList"][0]["description"]),
                         ("С-", "25.00000000", "копия"))

        order = create("SalesOrder", {"name": f"{TAG} order", "accountId": S["account"], "quoteId": quote["id"],
                                      "itemList": [line()]}, c("dir"))
        attributes = ok(self, c("dir").get(f"FinanceDocument/SalesOrder/{order['id']}/convertTo/Invoice"))
        self.assertEqual((attributes["salesOrderId"], attributes["quoteId"]), (order["id"], quote["id"]))
        from_order = create("Invoice", {**attributes, **DATES}, c("dir"))
        self.assertEqual({r["id"] for r in ok(self, c("dir").get(f"Quote/{quote['id']}/invoices"))["list"]},
                         {from_quote["id"], from_order["id"]})
        self.assertEqual([r["id"] for r in ok(self, c("dir").get(f"SalesOrder/{order['id']}/invoices"))["list"]],
                         [from_order["id"]])
        for source, sid in (("Quote", quote["id"]), ("SalesOrder", order["id"])):
            self.assertEqual(c("dep").get(f"FinanceDocument/{source}/{sid}/convertTo/Invoice")[0], 403)

    def test_reverse_links_and_activities(self):
        iid = invoice([line()], contactId=S["contact"], opportunityId=S["opportunity"])["id"]
        for scope, rid in (("Account", S["account"]), ("Contact", S["contact"]), ("Opportunity", S["opportunity"])):
            listed = {r["id"] for r in ok(self, c("dir").get(f"{scope}/{rid}/cInvoices", maxSize=200))["list"]}
            self.assertIn(iid, listed, scope)
        document = create("Document", {"name": f"{TAG} doc", "publishDate": "2026-10-02"}, c("dir"))
        ok(self, c("dir").request("POST", f"Invoice/{iid}/documents", {"id": document["id"]}))
        self.assertEqual([r["id"] for r in ok(self, c("dir").get(f"Document/{document['id']}/cInvoices"))["list"]],
                         [iid])
        mine = {"parentType": "Invoice", "parentId": iid, "assignedUserId": S["users"]["dir"]}
        task = create("Task", {"name": f"{TAG} task", **mine}, c("dir"))
        call = create("Call", {"name": f"{TAG} call", "status": "Held", "dateStart": "2026-10-02 10:00:00",
                               "dateEnd": "2026-10-02 10:05:00", **mine}, c("dir"))
        self.assertEqual([r["id"] for r in ok(self, c("dir").get(f"Invoice/{iid}/tasks"))["list"]], [task["id"]])
        self.assertEqual([r["id"] for r in ok(self, c("dir").get(f"Invoice/{iid}/calls"))["list"]], [call["id"]])
        self.assertEqual(ok(self, c("dir").get(f"Invoice/{iid}/vtigerArchives"))["total"], 0)


# ---------------------------------------------------------------------------------------------------- access
class AccessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.invoice = invoice([line()])
        cls.item = must(c("dir").get(f"Invoice/{cls.invoice['id']}"))["itemList"][0]["id"]

    def test_only_the_director_sees_invoices(self):
        for user in ("dep", "sales", "cust", "norole"):
            for scope in ("Invoice", "InvoiceItem"):
                self.assertEqual(c(user).get(scope)[0], 403, f"{user} list {scope}")
            self.assertEqual(c(user).get(f"Invoice/{self.invoice['id']}")[0], 403, user)
            self.assertEqual(c(user).get(f"InvoiceItem/{self.item}")[0], 403, user)
            self.assertEqual(c(user).request("POST", "FinanceDocument/Invoice/calculate",
                                             {"attributes": {"itemList": [line()]}})[0], 403, user)
            self.assertEqual(c(user).post("Invoice", {"name": f"{TAG} x", "accountId": S["account"], **DATES,
                                                      "itemList": [line()]})[0], 403, user)
        self.assertEqual(c("dir").get(f"InvoiceItem/{self.item}")[0], 200)

    def test_items_are_never_written_directly(self):
        iid = self.invoice["id"]
        for client in (S["admin"], c("dir")):
            self.assertEqual(client.post("InvoiceItem", {"invoiceId": iid, "productId": S["product"],
                                                         "quantity": "1", "unitPrice": "1"})[0], 403)
            self.assertEqual(client.put(f"InvoiceItem/{self.item}", {"quantity": "5"})[0], 403)
            self.assertEqual(client.delete(f"InvoiceItem/{self.item}")[0], 403)
            self.assertEqual(client.request("POST", f"Invoice/{iid}/items", {"id": self.item})[0], 403)
            self.assertEqual(client.request("DELETE", f"Invoice/{iid}/items", {"id": self.item})[0], 403)
            self.assertIn(client.post("MassAction", {"entityType": "InvoiceItem", "action": "update",
                                                     "params": {"ids": [self.item]}, "data": {"quantity": "9"}})[0],
                          (400, 403))
        self.assertEqual(sql(f"SELECT quantity, deleted FROM invoice_item WHERE id='{self.item}'"), [["1.000", "0"]])

    def test_item_access_follows_the_invoice(self):
        mine = invoice([line(), line()], client=c("own"))
        mine_items = {i["id"] for i in must(c("own").get(f"Invoice/{mine['id']}"))["itemList"]}
        listed = {i["id"] for i in ok(self, c("own").get("InvoiceItem", maxSize=200))["list"]}
        self.assertEqual(listed, mine_items, "the list holds the items of the user's own invoices only")
        self.assertEqual(c("own").get(f"Invoice/{self.invoice['id']}")[0], 403)
        self.assertEqual(c("own").get(f"InvoiceItem/{self.item}")[0], 403)


if __name__ == "__main__":
    unittest.main()
