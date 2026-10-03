"""Stage 04.5 acceptance tests on the local stand: Act and ActItem (synthetic data).

Run: task test:stage04   (or: python3 -m unittest tests.stage04.test_stage04_5 from tests/stage04)

Covers: model, DB columns and the generated status dictionary; the act number (counter without prefix, imported numbers
as they are, duplicates and empty ones); an act calculated by the core, required date, refusals that change nothing,
re-saves that change no stored line value; the import write path (ORM with SaveOption::IMPORT and SILENT through
tests/stage04/import_fixture.php) and itvolga-finance-verify; «Создать акт» from an invoice (reverse conversion: the
key stays on the invoice) — prefill, save, the one-live-act rule on the prefill and on the save under the invoice lock,
several invoices of one act through the invoice field, removal and restore; independent source values of an invoice
and its act; no link with payments; reverse links; access (director only, items follow their act, no direct writes,
no CSV import). Every record, user and role is created by the run (names start with SYNTH-<run id>) and deleted at
the end.
"""
import json
import secrets
import select
import subprocess
import sys
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "stage03"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from espo import DB_NAME, MYSQL_SOCKET, REPO, Client, admin_credentials, espo_console, sql  # noqa: E402
from test_stage04_2 import label, must, ok  # noqa: E402
from test_stage04_4 import import_save  # noqa: E402

RUN = secrets.token_hex(3)
TAG = f"SYNTH-{RUN}"
VT_BASE = 600_000_000 + secrets.randbelow(90_000_000)
INVOICE_DATES = {"dateInvoiced": "2026-10-03", "dateDue": "2026-10-17"}
DATE = {"dateAct": "2026-10-03"}
CONTROL = ["expectedSubtotal", "expectedPreTaxTotal", "expectedGrandTotal", "sourceSubtotal", "sourcePreTaxTotal",
           "sourceGrandTotal"]
LINKED = "financeConversionLinked"
S = {}


def setUpModule():
    S.update(created=[], users={}, clients={})
    unittest.addModuleCleanup(cleanup)
    admin = Client(*admin_credentials())
    S["admin"] = admin
    roles = {r["name"]: r["id"] for r in must(admin.get("Role", maxSize=50))["list"]}
    # Items follow their act whatever the item's own level; invoices of others are readable, not editable.
    own_role = must(admin.post("Role", {"name": f"{TAG} own acts", "data": {
        "Act": {"create": "yes", "read": "own", "edit": "own", "delete": "own"}, "ActItem": {"read": "all"},
        "Invoice": {"create": "yes", "read": "all", "edit": "own", "delete": "no"}, "InvoiceItem": {"read": "all"},
        "Product": {"read": "all"}, "Account": {"read": "all"}}}))
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
    S["product"] = create("Product", {"name": f"{TAG} service"})["id"]
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


def line(**values):
    return {"productId": S["product"], "quantity": "1", "unitPrice": "100", **values}


def invoice(lines=None, client=None, **header):
    return create("Invoice", {"name": f"{TAG} invoice", "accountId": S["account"], **INVOICE_DATES,
                              "itemList": lines or [line()], **header}, client or c("dir"))


def act(lines=None, client=None, **header):
    return create("Act", {"name": f"{TAG} act", "accountId": S["account"], **DATE, "itemList": lines or [line()],
                          **header}, client or c("dir"))


def from_invoice(inv, client=None):
    """«Создать акт»: the prefilled form saved as it is (with the act date the form would default to)."""
    attributes = must((client or c("dir")).get(f"FinanceDocument/Invoice/{inv['id']}/convertTo/Act"))
    return create("Act", {**attributes, **DATE}, client or c("dir"))


def get(entity, rid, client="admin"):
    return must((S["admin"] if client == "admin" else c(client)).get(f"{entity}/{rid}"))


def counter():
    return int(sql("SELECT value FROM next_number WHERE entity_type='Act' AND field_name='number'")[0][0])


def counts():
    return (sql("SELECT COUNT(*) FROM act")[0][0], sql("SELECT COUNT(*) FROM act_item")[0][0], counter())


def act_of(iid):
    value = sql(f"SELECT act_id FROM invoice WHERE id='{iid}'")[0][0]
    return None if value == "NULL" else value


def invoices_of(aid):
    return {r["id"] for r in must(c("dir").get(f"Act/{aid}/invoices", maxSize=200))["list"]}


def totals(got):
    return got["subtotal"], got["preTaxTotal"], got["grandTotal"]


def item_rows(table, parent, pid):
    """Every stored value of a document's lines (items are saved silently: modified_at would not show a rewrite)."""
    return sql("SELECT id, `order`, deleted, product_id, name, description, quantity, unit_price, discount_amount, "
               f"discount_percent, tax_rate, amount, purchase_cost, margin FROM {table} WHERE {parent}='{pid}' "
               "ORDER BY `order`")


def imported_act(number, stored, lines, **attributes):
    """An act written by the import path of stage 06.3 (ORM, IMPORT + SILENT), then classified by
    itvolga-finance-verify. Returns (id, console output)."""
    vt = VT_BASE + secrets.randbelow(10_000_000)
    header = {"name": f"{TAG} imported act", "number": number, "accountId": S["account"], "status": "Received",
              "dateAct": "2019-05-20", "taxMode": "individual", "subtotal": stored[0], "preTaxTotal": stored[1],
              "grandTotal": stored[2], "vtigerId": vt, "assignedUserId": S["users"]["dir"],
              "vtigerData": {"region_id": 0, "spcompany": "Default"}, **attributes}
    saved = import_save("Act", header)
    assert saved["ok"], saved
    S["created"].append(("Act", saved["id"]))
    for order, values in enumerate(lines, 1):
        row = import_save("ActItem", {"actId": saved["id"], "productId": S["product"], "name": f"{TAG} service",
                                      "order": order, "vtigerId": vt + order, "quantity": "1", "taxRate": "0",
                                      "discountAmount": "0", "purchaseCost": "0", **values})
        assert row["ok"], row
    return saved["id"], espo_console("itvolga-finance-verify", "--entity=Act", f"--id={saved['id']}")


def hold(lock_sql, then_sql, call, waits=True):
    """Another MySQL session holds a lock while `call` runs in a thread. waits: the call must wait for the lock — the
    session then runs `then_sql` and commits; otherwise the call must finish while the lock is still held. Returns the
    raw result of `call`."""
    holder = subprocess.Popen(["sudo", "-n", "mysql", f"--socket={MYSQL_SOCKET}", "-N", "-B", "--unbuffered", DB_NAME],
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    result = {}
    try:
        holder.stdin.write(f"START TRANSACTION; {lock_sql};\n")
        holder.stdin.flush()
        ready, _, _ = select.select([holder.stdout], [], [], 15)
        assert ready and holder.stdout.readline().strip(), "the locking session holds the row"
        worker = threading.Thread(target=lambda: result.update(r=call()))
        worker.start()
        worker.join(3 if waits else 20)
        assert worker.is_alive() == waits, "the save waits for the lock" if waits else "the save ignores the held row"
        holder.stdin.write(f"{then_sql}; COMMIT;\n" if then_sql else "COMMIT;\n")
        holder.stdin.close()
        holder.wait(15)
        worker.join(60)
    finally:
        if holder.poll() is None:
            holder.kill()
            holder.wait(5)
        for stream in (holder.stdin, holder.stdout, holder.stderr):
            stream.close()
    return result["r"]


# ---------------------------------------------------------------------------------------------------- model
class ModelTest(unittest.TestCase):
    def test_columns_and_indexes(self):
        def decimals(table):
            return {r[0]: r[1] for r in sql(
                "SELECT column_name, CONCAT(numeric_precision, ',', numeric_scale) FROM information_schema.columns "
                f"WHERE table_schema=DATABASE() AND table_name='{table}' AND data_type='decimal'")}
        invoice_only = {"balance_source", "paid_amount", "balance_amount"}
        self.assertEqual(decimals("act"), {k: v for k, v in decimals("invoice").items() if k not in invoice_only})
        self.assertEqual(decimals("act_item"), decimals("invoice_item"), "items: the contract Item structure")
        types = dict(sql("SELECT column_name, column_type FROM information_schema.columns WHERE table_schema=DATABASE() "
                         "AND table_name='act' AND column_name IN ('date_act', 'number')"))
        self.assertEqual(types, {"date_act": "date", "number": "varchar(100)"})
        for table in ("act", "act_item"):
            self.assertEqual(sql("SELECT non_unique FROM information_schema.statistics WHERE table_schema=DATABASE() "
                                 f"AND table_name='{table}' AND column_name='vtiger_id'"), [["0"]], table)
        # Several invoices may point to one act: the key on the invoice is indexed, never unique.
        self.assertEqual({r[0] for r in sql("SELECT non_unique FROM information_schema.statistics WHERE "
                                            "table_schema=DATABASE() AND table_name='invoice' AND column_name='act_id'")},
                         {"1"})
        self.assertEqual(sql("SELECT COUNT(*) FROM information_schema.columns WHERE table_schema=DATABASE() AND "
                             "table_name='act_document' AND column_name IN ('act_id', 'document_id')"), [["2"]])

    def test_metadata(self):
        meta = ok(self, S["admin"].get("Metadata"))
        defs = meta["entityDefs"]
        fields = defs["Act"]["fields"]
        self.assertEqual((fields["status"]["options"], fields["status"]["default"]),
                         (["", "Created", "Sent", "Done", "Received"], "Created"))
        self.assertTrue(all(fields[f].get("required") for f in ("dateAct", "name", "account")))
        self.assertEqual(set(defs["Act"]["links"]), {
            "items", "account", "contact", "legalEntity", "assignedUser", "teams", "documents", "createdBy",
            "modifiedBy", "invoices"})
        for absent in ("opportunity", "termsAndConditions", "salesOrder", "quote", "dateInvoiced", "dateDue",
                       "balanceSource", "paidAmount", "balanceAmount", "settlementState", "invoices"):
            self.assertNotIn(absent, fields, absent)
        for activity in ("Task", "Call", "Meeting"):
            self.assertNotIn("Act", defs[activity]["fields"]["parent"]["entityList"], activity)
        # The common Document fields stay identical across the finance documents (finance-contract.md §11).
        keys = ("type", "precision", "scale", "readOnly", "onlyDefaultCurrency", "options", "view", "required")
        for name, spec in defs["Invoice"]["fields"].items():
            if name in fields and name not in ("status", "number"):
                other = fields[name]
                self.assertEqual({k: spec.get(k) for k in keys}, {k: other.get(k) for k in keys}, name)
        item, invoice_item = defs["ActItem"]["fields"], defs["InvoiceItem"]["fields"]
        self.assertEqual(set(item) - {"act"}, set(invoice_item) - {"invoice"})
        for name in set(item) - {"act"}:
            self.assertEqual({k: item[name].get(k) for k in keys}, {k: invoice_item[name].get(k) for k in keys}, name)
        registry = json.loads((REPO / "custom/Espo/Modules/Itvolga/Resources/metadata/app/itvolgaFinance.json")
                              .read_text(encoding="utf-8"))
        self.assertEqual((registry["documents"]["Act"]["numberPrefix"], registry["documents"]["Act"]["firstNumber"]),
                         ("", 403))
        self.assertEqual(registry["conversions"]["Invoice"]["Act"]["link"], "invoices")
        self.assertEqual(set(registry["payments"]["Payment"]["targets"]), {"Invoice", "SalesOrder"},
                         "no payment is allocated to an act")
        self.assertGreaterEqual(counter(), 403)
        self.assertEqual(defs["Invoice"]["links"]["act"], {"type": "belongsTo", "entity": "Act", "foreign": "invoices"})
        self.assertTrue(defs["Invoice"]["fields"]["act"].get("audited"))
        self.assertFalse(meta["scopes"]["Act"]["stream"])
        panel = meta["clientDefs"]["Act"]["relationshipPanels"]["invoices"]
        self.assertEqual((panel["createDisabled"], panel["selectDisabled"], panel["unlinkDisabled"],
                          panel["rowActionsView"]),
                         (True, True, True, "views/record/row-actions/relationship-view-only"), "view only")
        labels = ok(self, S["admin"].get("I18n"))["Act"]["options"]["status"]
        self.assertEqual(labels, {"Created": "Создан", "Sent": "Отправлен", "Done": "Выполнен", "Received": "Получен"})
        tabs = ok(self, S["admin"].get("Settings"))["tabList"]
        self.assertEqual(tabs[tabs.index("Invoice"):tabs.index("Invoice") + 3], ["Invoice", "Act", "Payment"])


# ---------------------------------------------------------------------------------------------------- calculation
class CalculationTest(unittest.TestCase):
    def test_act_calculated_by_the_core(self):
        number = counter()
        created = act([line(quantity="2.5", unitPrice="1333.33", discountAmount="0.33", description="Часы"),
                       line(quantity="0.25", unitPrice="1500")], contactId=S["contact"], adjustment="-0.5")
        got = get("Act", created["id"], "dir")
        self.assertEqual(got["number"], str(number), "digits only, no prefix")
        self.assertEqual(counter(), number + 1)
        self.assertEqual([(i["order"], i["amount"]) for i in got["itemList"]],
                         [(1, "3333.00000000"), (2, "375.00000000")])
        self.assertEqual(totals(got), ("3708.00000000", "3708.00000000", "3707.50000000"))
        self.assertEqual((got["status"], got["legalEntityId"], got["grandTotalCurrency"], got["dateAct"],
                          got["contactId"], got["sourceFormula"], got["totalsCheck"]),
                         ("Created", S["legalEntity"], "RUB", DATE["dateAct"], S["contact"], "", ""))
        self.assertEqual(ok(self, c("dir").get(f"Act/{created['id']}/items"))["total"], 2)

    def test_date_is_required_and_refusals_change_nothing(self):
        before = counts()
        refused = c("dir").post("Act", {"name": f"{TAG} no date", "accountId": S["account"], "itemList": [line()]})
        self.assertEqual((refused[0], label(refused), refused[1]["messageTranslation"]["data"]["field"]),
                         (400, "validationFailure", "dateAct"))
        for data, expected in (({"itemList": [line(quantity=1.5)]}, "financeFloat"),
                               ({"itemList": [line(), line(taxRate="18")]}, "financeVat"),
                               ({"itemList": []}, "financeNoLines")):
            result = c("dir").post("Act", {"name": f"{TAG} refused", "accountId": S["account"], **DATE, **data})
            self.assertEqual((result[0], label(result)), (400, expected))
        self.assertEqual(counts(), before, "no act, item or number is taken")

    def test_resave_and_cascade(self):
        aid = act([line(quantity="2.5", unitPrice="1333.33"), line(quantity="3", unitPrice="33.335")])["id"]
        first = get("Act", aid, "dir")
        stored = item_rows("act_item", "act_id", aid)
        respelled = [{**first["itemList"][0], "quantity": "2.500", "unitPrice": "1333.33000000"},
                     {**first["itemList"][1], "quantity": "3", "unitPrice": "33.33500"}]
        again = ok(self, c("dir").put(f"Act/{aid}", {"itemList": respelled, "status": "Sent"}))
        self.assertEqual((totals(again), again["number"], again["status"]), (totals(first), first["number"], "Sent"))
        self.assertEqual(item_rows("act_item", "act_id", aid), stored, "equivalent values change no stored line value")
        removed = must(c("dir").post("Act", {"name": f"{TAG} del", "accountId": S["account"], **DATE,
                                             "itemList": [line(), line()]}))
        self.assertEqual(c("dir").delete(f"Act/{removed['id']}")[0], 200)
        self.assertEqual(sql(f"SELECT COUNT(*), SUM(deleted) FROM act_item WHERE act_id='{removed['id']}'"),
                         [["2", "2"]])

    def test_numbers_of_imported_acts(self):
        # Imported numbers are kept as they are: digits, repeated and empty (D-17); the counter skips a taken number.
        number = counter()
        stored = ("100.00000000",) * 3
        for imported_number in (str(number), str(number), ""):
            aid, _ = imported_act(imported_number, stored, [{"quantity": "1", "unitPrice": "100", "amount": "100",
                                                             "margin": "100"}])
            self.assertEqual(get("Act", aid)["number"], imported_number)
        self.assertEqual(counter(), number, "the import takes no number")
        self.assertEqual(act()["number"], str(number + 1), "the number held by imported acts is skipped")


# ---------------------------------------------------------------------------------------------------- import path
class ImportTest(unittest.TestCase):
    def test_imported_act_keeps_its_source_values(self):
        stored = ("1502.50000000",) * 3
        aid, out = imported_act("77", stored, [
            {"quantity": "1.5", "unitPrice": "1000", "amount": "1500", "margin": "1500", "description": "работы"},
            {"quantity": "1", "unitPrice": "2.5", "amount": "2.5", "margin": "0"}],
            status="", dateAct=None, vtigerData={"region_id": 0, "spcompany": "По умолчанию"}, taxMode="group_tax_inc")
        self.assertIn("Act: noLineTax / exact — 1", out)
        got = get("Act", aid)
        self.assertEqual((totals(got), got["number"], got["status"], got["dateAct"], got["legalEntityId"],
                          got["taxMode"], got["vtigerData"]["spcompany"]),
                         (stored, "77", "", None, S["legalEntity"], "group_tax_inc", "По умолчанию"))
        self.assertEqual([(i["amount"], i["margin"]) for i in got["itemList"]],
                         [("1500.00000000", "1500.00000000"), ("2.50000000", "0.00000000")])
        self.assertNotIn("vtigerData", get("Act", aid, "dir"), "source data is for administrators")
        self.assertEqual(int(sql(f"SELECT COUNT(*) FROM note WHERE parent_type='Act' AND parent_id='{aid}'")[0][0]), 0)
        # A partial update of an imported act without a date passes; clearing the date through the API does not.
        self.assertEqual(c("dir").put(f"Act/{aid}", {"status": "Sent"})[0], 200)
        refused = c("dir").put(f"Act/{aid}", {"dateAct": None})
        self.assertEqual((refused[0], label(refused)), (400, "validationFailure"))
        self.assertEqual(totals(get("Act", aid)), stored)

    def test_discrepancy_is_shown_not_corrected(self):
        stored = ("5000.01000000",) * 3
        aid, out = imported_act("78", stored, [{"quantity": "1", "unitPrice": "5000", "amount": "5000",
                                                "margin": "5000"}])
        self.assertIn("Act: noLineTax / mismatch — 1", out)
        got = get("Act", aid, "dir")
        self.assertEqual((totals(got), [got[f] for f in CONTROL[:3]]), (stored, ["5000.00000000"] * 3))

    def test_import_needs_silent(self):
        before = counts()
        refused = import_save("Act", {"name": f"{TAG} loud", "accountId": S["account"], "number": "79",
                                      "vtigerData": {"region_id": 0}}, silent=False)
        self.assertFalse(refused["ok"])
        aid, _ = imported_act("80", ("1.00000000",) * 3, [{"unitPrice": "1", "amount": "1", "margin": "1"}])
        loud_item = import_save("ActItem", {"actId": aid, "productId": S["product"], "order": 2, "quantity": "1",
                                            "unitPrice": "1"}, silent=False)
        self.assertFalse(loud_item["ok"])
        self.assertEqual(int(sql(f"SELECT COUNT(*) FROM act_item WHERE act_id='{aid}'")[0][0]), 1)
        self.assertEqual(counts()[2], before[2])

    def test_lines_removed_by_the_import_are_not_restored(self):
        """A line the importer removes while its act stays is marked like one removed by an edit (not restored with the
        act); the lines of a removed act are not marked and come back with it."""
        aid, _ = imported_act("84", ("150.00000000",) * 3, [
            {"unitPrice": "100", "amount": "100", "margin": "100"}, {"unitPrice": "50", "amount": "50", "margin": "50"}])
        kept, removed = (r[0] for r in sql(f"SELECT id FROM act_item WHERE act_id='{aid}' ORDER BY `order`"))
        self.assertTrue(import_save("ActItem", {}, rid=removed, op="remove")["ok"])
        ok(self, c("dir").delete(f"Act/{aid}"))
        self.assertEqual(sql(f"SELECT id, deleted, removed_by_edit FROM act_item WHERE act_id='{aid}' ORDER BY `order`"),
                         [[kept, "1", "0"], [removed, "1", "1"]])

    def test_imported_invoices_point_to_their_act(self):
        aid, _ = imported_act("81", ("200.00000000",) * 3, [{"quantity": "2", "unitPrice": "100", "amount": "200",
                                                             "margin": "200"}])
        first, second = invoice(), invoice()
        for inv in (first, second):
            self.assertTrue(import_save("Invoice", {"actId": aid}, rid=inv["id"])["ok"])
        self.assertEqual(invoices_of(aid), {first["id"], second["id"]})


# ---------------------------------------------------------------------------------------------------- «Создать акт»
class ConversionTest(unittest.TestCase):
    def test_create_act_from_invoice(self):
        inv = invoice([line(quantity="2", unitPrice="10", description="копия", discountAmount="1")],
                      contactId=S["contact"], shippingAmount="5", status="Paid")
        before = counts()
        attributes = ok(self, c("dir").get(f"FinanceDocument/Invoice/{inv['id']}/convertTo/Act"))
        self.assertEqual(counts(), before, "the prefill writes nothing and takes no number")
        self.assertEqual((attributes["invoicesIds"], attributes["invoicesNames"], attributes["accountId"],
                          attributes["contactId"], attributes["shippingAmount"]),
                         ([inv["id"]], {inv["id"]: inv["name"]}, S["account"], S["contact"], "5.00000000"))
        for absent in ("number", "status", "dateAct", "dateInvoiced", "invoiceId", "vtigerId", "opportunityId",
                       "termsAndConditions", "salesOrderId", "paidAmount", *CONTROL):
            self.assertNotIn(absent, attributes)
        self.assertTrue(all("id" not in x and "amount" not in x and "margin" not in x for x in attributes["itemList"]))
        self.assertIsNone(act_of(inv["id"]))
        created = create("Act", {**attributes, **DATE}, c("dir"))
        got = get("Act", created["id"], "dir")
        self.assertEqual((got["grandTotal"], got["status"], got["itemList"][0]["description"], got["number"]),
                         ("24.00000000", "Created", "копия", str(before[2])))
        self.assertEqual(act_of(inv["id"]), created["id"])
        self.assertEqual(invoices_of(created["id"]), {inv["id"]})
        shown = get("Invoice", inv["id"], "dir")
        self.assertEqual((shown["actId"], shown["actName"], shown["status"]), (created["id"], created["name"], "Paid"))

    def test_second_act_is_refused(self):
        inv = invoice()
        first = from_invoice(inv)
        before = counts()
        prefill = c("dir").get(f"FinanceDocument/Invoice/{inv['id']}/convertTo/Act")
        self.assertEqual((prefill[0], label(prefill)), (409, LINKED))
        attributes = {"name": f"{TAG} second", "accountId": S["account"], **DATE, "itemList": [line()],
                      "invoicesIds": [inv["id"]]}
        refused = c("dir").post("Act", attributes)
        self.assertEqual((refused[0], label(refused)), (409, LINKED))
        self.assertEqual((counts(), act_of(inv["id"])), (before, first["id"]), "nothing is written")

    def test_core_limits_of_the_source(self):
        first, second, gone = invoice(), invoice(), invoice()
        ok(self, c("dir").delete(f"Invoice/{gone['id']}"))
        before = counts()
        base = {"name": f"{TAG} limits", "accountId": S["account"], **DATE, "itemList": [line()]}
        self.assertEqual(c("dir").post("Act", {**base, "invoicesIds": [first["id"], second["id"]]})[0], 403)
        self.assertEqual(c("dir").post("Act", {**base, "invoicesIds": [gone["id"]]})[0], 403)
        self.assertEqual(c("dir").get(f"FinanceDocument/Invoice/{gone['id']}/convertTo/Act")[0], 404)
        # Saving the act writes the invoice's key: the invoice must be editable, not only readable.
        theirs = invoice()
        self.assertEqual(c("own").get(f"Invoice/{theirs['id']}")[0], 200)
        self.assertEqual(c("own").get(f"FinanceDocument/Invoice/{theirs['id']}/convertTo/Act")[0], 403)
        self.assertEqual(c("own").post("Act", {**base, "invoicesIds": [theirs["id"]]})[0], 403)
        self.assertEqual(counts(), before)
        self.assertEqual({act_of(i["id"]) for i in (first, second, theirs)}, {None})
        # The stub links only a new act: an update of an existing one does not take an invoice.
        existing = act()
        ok(self, c("dir").put(f"Act/{existing['id']}", {"invoicesIds": [first["id"]], "description": "x"}))
        self.assertIsNone(act_of(first["id"]))

    def test_several_invoices_of_one_act(self):
        first, second, third = invoice(), invoice(), invoice()
        shared = from_invoice(first)
        ok(self, c("dir").put(f"Invoice/{second['id']}", {"actId": shared["id"]}))
        self.assertEqual(invoices_of(shared["id"]), {first["id"], second["id"]}, "no 1:1 restriction")
        prefill = c("dir").get(f"FinanceDocument/Invoice/{second['id']}/convertTo/Act")
        self.assertEqual((prefill[0], label(prefill)), (409, LINKED), "a linked invoice gets no second act")
        other = from_invoice(third)
        ok(self, c("dir").put(f"Invoice/{second['id']}", {"actId": other["id"]}))
        self.assertEqual((invoices_of(shared["id"]), invoices_of(other["id"])),
                         ({first["id"]}, {third["id"], second["id"]}), "re-pointing moves one invoice only")
        ok(self, c("dir").put(f"Invoice/{second['id']}", {"actId": None}))
        self.assertEqual(invoices_of(other["id"]), {third["id"]})
        audit = ok(self, c("dir").get(f"Invoice/{second['id']}/updateStream"))["list"]
        self.assertEqual(sum("act" in note["data"]["fields"] for note in audit), 3, "every re-pointing is audited")
        self.assertEqual(get("Act", shared["id"], "dir")["grandTotal"], "100.00000000", "the act keeps its totals")

    def test_removed_act_frees_its_invoices(self):
        inv = invoice()
        first = from_invoice(inv)
        ok(self, c("dir").delete(f"Act/{first['id']}"))
        shown = get("Invoice", inv["id"], "dir")
        self.assertEqual((act_of(inv["id"]), shown["actId"], shown.get("actName")), (first["id"], first["id"], None),
                         "a deleted act keeps the invoice key; its name is not loaded")
        ok(self, S["admin"].post("Act/action/restoreDeleted", {"id": first["id"]}))
        self.assertEqual(get("Invoice", inv["id"], "dir")["actName"], first["name"], "restore brings the link back")
        self.assertEqual(sql(f"SELECT COUNT(*), SUM(deleted) FROM act_item WHERE act_id='{first['id']}'"), [["1", "0"]])
        ok(self, c("dir").delete(f"Act/{first['id']}"))
        second = from_invoice(inv)
        self.assertEqual(act_of(inv["id"]), second["id"], "a removed act does not block a new one")

    def test_restore_brings_back_cascade_lines_only(self):
        """The core restores a document's removed items by time (modified not before the document): a line removed by
        an edit in the same second as the document's removal stays removed (external review of stage 04.5)."""
        for entity, table, parent, create in (("Act", "act_item", "act_id", act), ("Invoice", "invoice_item", "invoice_id",
                                                                                    invoice)):
            did = create([line(), line(unitPrice="50")])["id"]
            lines = get(entity, did, "dir")["itemList"]
            ok(self, c("dir").put(f"{entity}/{did}", {"itemList": [lines[0]]}))
            ok(self, c("dir").delete(f"{entity}/{did}"))
            # The same second as the removal, deterministically.
            sql(f"UPDATE {table} SET modified_at=(SELECT modified_at FROM {table.rsplit('_', 1)[0]} WHERE id='{did}') "
                f"WHERE id='{lines[1]['id']}'")
            ok(self, S["admin"].post(f"{entity}/action/restoreDeleted", {"id": did}))
            self.assertEqual(sql(f"SELECT id, deleted, removed_by_edit FROM {table} WHERE {parent}='{did}' ORDER BY `order`"),
                             [[lines[0]["id"], "0", "0"], [lines[1]["id"], "1", "1"]], entity)
            self.assertEqual(totals(get(entity, did))[2], "100.00000000", entity)

    def test_source_values_are_independent(self):
        inv = invoice([line(quantity="2", unitPrice="500")])
        aid = from_invoice(inv)["id"]
        act_lines, invoice_lines = item_rows("act_item", "act_id", aid), item_rows("invoice_item", "invoice_id", inv["id"])
        lines = get("Invoice", inv["id"], "dir")["itemList"]
        ok(self, c("dir").put(f"Invoice/{inv['id']}", {"itemList": [{**lines[0], "quantity": "3"}]}))
        self.assertEqual((totals(get("Act", aid)), item_rows("act_item", "act_id", aid)),
                         (("1000.00000000",) * 3, act_lines), "an invoice edit leaves its act as it was")
        lines = get("Act", aid, "dir")["itemList"]
        ok(self, c("dir").put(f"Act/{aid}", {"itemList": [{**lines[0], "unitPrice": "600"}]}))
        self.assertEqual(totals(get("Act", aid))[2], "1200.00000000", "an act total above its invoice's is accepted")
        self.assertEqual(totals(get("Invoice", inv["id"]))[2], "1500.00000000")
        self.assertNotEqual(item_rows("invoice_item", "invoice_id", inv["id"]), invoice_lines)
        # Imported invoice and act with different totals keep their own source values.
        imported_aid, _ = imported_act("82", ("110.00000000",) * 3, [{"unitPrice": "110", "amount": "110",
                                                                      "margin": "110"}], dateAct="2018-01-15")
        older = invoice()
        self.assertTrue(import_save("Invoice", {"actId": imported_aid}, rid=older["id"])["ok"])
        self.assertEqual((totals(get("Act", imported_aid))[2], totals(get("Invoice", older["id"]))[2]),
                         ("110.00000000", "100.00000000"))


# ---------------------------------------------------------------------------------------------------- concurrency
class ConcurrencyTest(unittest.TestCase):
    """The one-live-act rule is checked again on the save, under the invoice lock and with a locking read of its act:
    a link or a removal committed while the save waited is seen (not the transaction's older snapshot)."""

    def post_from(self, inv):
        attributes = must(c("dir").get(f"FinanceDocument/Invoice/{inv['id']}/convertTo/Act"))
        return lambda: c("dir").post("Act", {**attributes, **DATE})

    def test_a_link_committed_meanwhile_is_seen(self):
        inv, other = invoice(), act()
        before = counts()
        result = hold(f"SELECT id FROM invoice WHERE id='{inv['id']}' FOR UPDATE",
                      f"UPDATE invoice SET act_id='{other['id']}' WHERE id='{inv['id']}'", self.post_from(inv))
        self.assertEqual((result[0], label(result)), (409, LINKED))
        self.assertEqual((counts(), act_of(inv["id"])), (before, other["id"]))

    def test_a_restored_act_is_seen(self):
        # The invoice points to a removed act (no obstacle) that another transaction is restoring: the save waits for
        # the act row — a plain read would pass the uncommitted removal and give the invoice a second act.
        inv, other = invoice(), act()
        ok(self, c("dir").put(f"Invoice/{inv['id']}", {"actId": other["id"]}))
        ok(self, c("dir").delete(f"Act/{other['id']}"))
        before = counts()
        result = hold(f"SELECT id FROM act WHERE id='{other['id']}' FOR UPDATE",
                      f"UPDATE act SET deleted=0 WHERE id='{other['id']}'", self.post_from(inv))
        self.assertEqual((result[0], label(result)), (409, LINKED))
        self.assertEqual(counts(), before)

    def test_saves_lock_their_own_rows_only(self):
        """A locking read of a full record would also lock the rows its names are joined from — the act, the single
        legal entity and the account of an invoice — and deadlock with saves that lock them in another order (review
        of stage 04.5): payment and invoice saves do not wait for those rows."""
        inv, linked = invoice(), act()
        ok(self, c("dir").put(f"Invoice/{inv['id']}", {"actId": linked["id"]}))
        data = {"datePaid": "2026-10-03", "amount": "10", "payerType": "Account", "payerId": S["account"],
                "assignedUserId": S["users"]["dir"], "allocationList": [{"invoiceId": inv["id"], "amount": "10"}]}
        for n, (table, rid) in enumerate((("act", linked["id"]), ("legal_entity", S["legalEntity"]),
                                          ("account", S["account"]))):
            lock = f"SELECT id FROM {table} WHERE id='{rid}' FOR UPDATE"
            paid = ok(self, hold(lock, None, lambda: c("dir").post("Payment", data), waits=False))
            S["created"].append(("Payment", paid["id"]))
            edited = hold(lock, None, lambda: c("dir").put(f"Invoice/{inv['id']}", {"discountAmount": str(n + 1)}),
                          waits=False)
            self.assertEqual(ok(self, edited)["discountAmount"], f"{n + 1}.00000000", table)

    def test_row_locks_join_nothing(self):
        """RowLock selects the own columns only: no locking read of a finance record joins another table (a foreign
        field such as PaymentAllocation.paymentStatus is storable but joined)."""
        script = r"""<?php
include getenv('ESPO_ROOT') . '/bootstrap.php';
$app = new Espo\Core\Application();
$app->setupSystemUser();
$em = $app->getContainer()->getByClass(Espo\ORM\EntityManager::class);
$lock = $app->getContainer()->getByClass(Espo\Core\InjectableFactory::class)
    ->create(Espo\Modules\Itvolga\Tools\FinanceDocument\RowLock::class);
$attributes = (new ReflectionMethod($lock, 'attributes'))->getClosure($lock);
$out = [];
foreach (json_decode($argv[1], true) as $type) {
    $query = $em->getQueryBuilder()->select($attributes($type))->from($type)->where(['id' => 'x'])->forUpdate()->build();
    $out[$type] = substr_count($em->getQueryComposer()->composeSelect($query), 'JOIN');
}
echo json_encode($out), "\n";
"""
        types = ["Quote", "QuoteItem", "SalesOrder", "SalesOrderItem", "Invoice", "InvoiceItem", "Act", "ActItem",
                 "Payment", "PaymentAllocation"]
        php = subprocess.run(["bash", "-c", f"source {REPO}/scripts/stand/lib.sh && echo $PHP_BIN"],
                             capture_output=True, text=True, check=True).stdout.strip()
        out = subprocess.run(["sudo", "-n", "-u", "espocrm", "env", f"ESPO_ROOT={REPO}", php, "--", json.dumps(types)],
                             input=script, capture_output=True, text=True, check=True).stdout
        self.assertEqual(json.loads(out.strip().splitlines()[-1]), dict.fromkeys(types, 0))

    def test_a_removed_invoice_is_refused(self):
        inv = invoice()
        before = counts()
        result = hold(f"SELECT id FROM invoice WHERE id='{inv['id']}' FOR UPDATE",
                      f"UPDATE invoice SET deleted=1 WHERE id='{inv['id']}'", self.post_from(inv))
        self.assertEqual((result[0], label(result)), (409, "financeConversionSourceMissing"))
        self.assertEqual(counts(), before, "no act without its invoice")


# ---------------------------------------------------------------------------------------------------- links, access
class LinkTest(unittest.TestCase):
    def test_reverse_links(self):
        aid = act(contactId=S["contact"])["id"]
        for scope, rid in (("Account", S["account"]), ("Contact", S["contact"])):
            listed = {r["id"] for r in ok(self, c("dir").get(f"{scope}/{rid}/cActs", maxSize=200))["list"]}
            self.assertIn(aid, listed, scope)
        document = create("Document", {"name": f"{TAG} doc", "publishDate": "2026-10-03"}, c("dir"))
        ok(self, c("dir").request("POST", f"Act/{aid}/documents", {"id": document["id"]}))
        self.assertEqual([r["id"] for r in ok(self, c("dir").get(f"Document/{document['id']}/cActs"))["list"]], [aid])

    def test_no_link_with_payments(self):
        aid = act()["id"]
        self.assertEqual(c("dir").get(f"FinanceDocument/Act/{aid}/convertTo/Payment")[0], 404)
        refused = c("dir").post("Payment", {"datePaid": "2026-10-03", "amount": "10", "assignedUserId": S["users"]["dir"],
                                            "allocationList": [{"actId": aid, "amount": "10"}]})
        self.assertEqual((refused[0], label(refused)), (400, "financeAllocationTargetRequired"))


class AccessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.act = act()
        cls.item = must(c("dir").get(f"Act/{cls.act['id']}"))["itemList"][0]["id"]
        cls.invoice = invoice()

    def test_only_the_director_sees_acts(self):
        for user in ("dep", "sales", "cust", "norole"):
            for scope in ("Act", "ActItem"):
                self.assertEqual(c(user).get(scope)[0], 403, f"{user} list {scope}")
            self.assertEqual(c(user).get(f"Act/{self.act['id']}")[0], 403, user)
            self.assertEqual(c(user).get(f"ActItem/{self.item}")[0], 403, user)
            self.assertEqual(c(user).post("Act", {"name": f"{TAG} x", "accountId": S["account"], **DATE,
                                                  "itemList": [line()]})[0], 403, user)
            self.assertEqual(c(user).get(f"FinanceDocument/Invoice/{self.invoice['id']}/convertTo/Act")[0], 403, user)
            self.assertEqual(c(user).request("POST", "FinanceDocument/Act/calculate",
                                             {"attributes": {"itemList": [line()]}})[0], 403, user)
        self.assertEqual(c("dir").get(f"ActItem/{self.item}")[0], 200)

    def test_items_are_never_written_directly(self):
        aid = self.act["id"]
        for client in (S["admin"], c("dir")):
            self.assertEqual(client.post("ActItem", {"actId": aid, "productId": S["product"], "quantity": "1",
                                                     "unitPrice": "1"})[0], 403)
            self.assertEqual(client.put(f"ActItem/{self.item}", {"quantity": "5"})[0], 403)
            self.assertEqual(client.delete(f"ActItem/{self.item}")[0], 403)
            self.assertEqual(client.request("POST", f"Act/{aid}/items", {"id": self.item})[0], 403)
            self.assertEqual(client.request("DELETE", f"Act/{aid}/items", {"id": self.item})[0], 403)
            self.assertIn(client.post("MassAction", {"entityType": "ActItem", "action": "update",
                                                     "params": {"ids": [self.item]}, "data": {"quantity": "9"}})[0],
                          (400, 403))
        self.assertEqual(sql(f"SELECT quantity, deleted FROM act_item WHERE id='{self.item}'"), [["1.000", "0"]])

    def test_item_access_follows_the_act(self):
        mine = act([line(), line()], client=c("own"))
        mine_items = {i["id"] for i in must(c("own").get(f"Act/{mine['id']}"))["itemList"]}
        own_items = {r[0] for r in sql("SELECT i.id FROM act_item i JOIN act a ON a.id=i.act_id WHERE i.deleted=0 AND "
                                       f"a.deleted=0 AND a.assigned_user_id='{S['users']['own']}'")}
        listed = {i["id"] for i in ok(self, c("own").get("ActItem", maxSize=200))["list"]}
        self.assertTrue(mine_items <= listed)
        self.assertEqual(listed, own_items, "only the items of the user's own acts")
        self.assertEqual(c("own").get(f"ActItem/{self.item}")[0], 403)

    def test_items_are_restored_only_with_their_document(self):
        aid = act([line(), line(unitPrice="50")])["id"]
        lines = get("Act", aid, "dir")["itemList"]
        ok(self, c("dir").put(f"Act/{aid}", {"itemList": [lines[0]]}))
        inv = invoice([line(), line(unitPrice="50")])
        invoice_lines = get("Invoice", inv["id"], "dir")["itemList"]
        ok(self, c("dir").put(f"Invoice/{inv['id']}", {"itemList": [invoice_lines[0]]}))
        for scope, rid, parent in (("ActItem", lines[1]["id"], ("Act", aid)),
                                   ("InvoiceItem", invoice_lines[1]["id"], ("Invoice", inv["id"]))):
            refused = S["admin"].post(f"{scope}/action/restoreDeleted", {"id": rid})
            self.assertEqual((refused[0], label(refused)), (409, "financeRestoreItemDenied"), scope)
            table = "act_item" if scope == "ActItem" else "invoice_item"
            self.assertEqual(sql(f"SELECT deleted FROM {table} WHERE id='{rid}'"), [["1"]], scope)
            self.assertEqual(totals(get(*parent))[2], "100.00000000", "the totals keep the document's lines")

    def test_act_side_links_need_the_invoice_edit_right(self):
        """Relating or unrelating an invoice from the act's side writes the invoice's key: edit access to the invoice is
        required as for its «Акт» field."""
        mine = act(client=c("own"))
        theirs = invoice()
        refused = c("own").request("POST", f"Act/{mine['id']}/invoices", {"id": theirs["id"]})
        self.assertEqual(refused[0], 403)
        self.assertIsNone(act_of(theirs["id"]))
        ok(self, c("dir").put(f"Invoice/{theirs['id']}", {"actId": mine["id"]}))
        refused = c("own").request("DELETE", f"Act/{mine['id']}/invoices", {"id": theirs["id"]})
        self.assertEqual(refused[0], 403)
        self.assertEqual(act_of(theirs["id"]), mine["id"])

    def test_control_fields_are_read_only(self):
        aid, _ = imported_act("83", ("100.01000000",) * 3, [{"quantity": "3", "unitPrice": "33.335",
                                                             "amount": "100.01", "margin": "100.01"}])
        before = get("Act", aid)
        ok(self, c("dir").put(f"Act/{aid}", {"number": "x", "vtigerId": 1, "sourceFormula": "groupTaxAdded",
                                             "totalsCheck": "exact", "legalEntityId": None, **{f: "1" for f in CONTROL}}))
        after = get("Act", aid)
        for f in ["number", "vtigerId", "sourceFormula", "totalsCheck", "legalEntityId", *CONTROL]:
            self.assertEqual(after[f], before[f], f)

    def test_no_csv_import_of_acts(self):
        attachment = ok(self, c("dir").request("POST", "Import/file", "synthetic description\n"))["attachmentId"]
        for entity in ("Act", "ActItem"):
            result = c("dir").request("POST", "Import", {"entityType": entity, "attributeList": ["description"],
                                                          "attachmentId": attachment, "delimiter": ",",
                                                          "textQualifier": "\"", "headerRow": False})
            self.assertEqual(result[0], 403, entity)
        self.assertEqual(int(sql("SELECT COUNT(*) FROM import WHERE entity_type IN ('Act','ActItem') "
                                 "AND deleted=0")[0][0]), 0)


if __name__ == "__main__":
    unittest.main()
