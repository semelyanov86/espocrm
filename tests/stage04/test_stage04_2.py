"""Stage 04.2 acceptance tests on the local stand: Quote, SalesOrder, their items and LegalEntity (synthetic data).

Run: task test:stage04   (or: python3 -m unittest discover -s tests/stage04 -v)

Covers: model and DB columns, creation with server-side totals (D-29, D-47) and numbering (ПРЕД_N, ЗАКАЗ_N),
atomic refusals (floats, malformed numbers, VAT, discounts, unknown products, column limits), editing and deleting
lines, the edit rule of imported documents (owner decision 2026-10-01: source totals kept until a calculation input
changes, then recalculated with the originals preserved), SourceVerifier marks (itvolga-finance-verify), «Создать
заказ», the single legal entity and access separation (director only; items follow their document; no direct item
writes). Every record, user and role is created by the run (names start with SYNTH-<run id>) and deleted at the end.
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
from espo import DB_NAME, MYSQL_SOCKET, Client, admin_credentials, espo_console, sql  # noqa: E402

RUN = secrets.token_hex(3)
TAG = f"SYNTH-{RUN}"
VT_BASE = 800_000_000 + secrets.randbelow(90_000_000)
DOCS = {"Quote": ("QuoteItem", "quote", "quote_item"), "SalesOrder": ("SalesOrderItem", "sales_order",
                                                                         "sales_order_item")}
S = {}


def ok(test, result, codes=(200,)):
    status, payload, _ = result
    test.assertIn(status, codes, f"unexpected HTTP {status}: {json.dumps(payload, ensure_ascii=False)[:400]}")
    return payload


def must(result):
    status, payload, _ = result
    if status != 200:
        raise AssertionError(f"setup failed: HTTP {status} {json.dumps(payload, ensure_ascii=False)[:300]}")
    return payload


def label(result):
    """Translation label of a refused save (Global.messages.finance*)."""
    payload = result[1] or {}
    return (payload.get("messageTranslation") or {}).get("label")


def table(entity):
    return DOCS[entity][1] if entity in DOCS else {"QuoteItem": "quote_item", "SalesOrderItem": "sales_order_item"}[entity]


def setUpModule():
    # Registered first: unittest runs module cleanups even when setUpModule fails half-way.
    S.update(created=[], users={}, clients={})
    unittest.addModuleCleanup(cleanup)
    admin = Client(*admin_credentials())
    S["admin"] = admin
    roles = {r["name"]: r["id"] for r in must(admin.get("Role", maxSize=50))["list"]}
    # Items follow their document whatever the item's own level: the synthetic role grants items `all` on purpose
    # while quotes are `own` — the document's access must still decide.
    own_role = must(admin.post("Role", {"name": f"{TAG} own quotes", "data": {
        "Quote": {"create": "yes", "read": "own", "edit": "own", "delete": "own"},
        "QuoteItem": {"read": "all"}, "Product": {"read": "all"}, "Account": {"read": "all"}}}))
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


def doc(entity, lines, client=None, **header):
    return create(entity, {"name": f"{TAG} {entity}", "accountId": S["account"], "itemList": lines, **header},
                  client or c("dir"))


def counter(entity):
    return int(sql(f"SELECT value FROM next_number WHERE entity_type='{entity}' AND field_name='number'")[0][0])


def counts(entity):
    item_table = DOCS[entity][2]
    return (sql(f"SELECT COUNT(*) FROM {DOCS[entity][1]}")[0][0], sql(f"SELECT COUNT(*) FROM {item_table}")[0][0],
            counter(entity))


# ---------------------------------------------------------------------------------------------------- model
class ModelTest(unittest.TestCase):
    def test_money_columns_are_decimal_with_contract_precision(self):
        expected = {
            "quote": {"subtotal": "25,8", "discount_amount": "25,8", "discount_percent": "25,3", "shipping_amount": "25,8",
                      "shipping_tax_percent": "25,3", "adjustment": "25,8", "pre_tax_total": "25,8", "grand_total": "25,8"},
            "quote_item": {"quantity": "25,3", "unit_price": "27,8", "discount_amount": "27,8", "discount_percent": "7,3",
                           "tax_rate": "7,3", "amount": "25,8", "purchase_cost": "27,8", "margin": "27,8"},
        }
        expected["sales_order"], expected["sales_order_item"] = expected["quote"], expected["quote_item"]
        for tbl, columns in expected.items():
            rows = {r[0]: r[1] for r in sql(
                "SELECT column_name, CONCAT(numeric_precision, ',', numeric_scale) FROM information_schema.columns "
                f"WHERE table_schema=DATABASE() AND table_name='{tbl}' AND data_type='decimal'")}
            self.assertEqual({k: rows.get(k) for k in columns}, columns, tbl)
            self.assertEqual(sql("SELECT character_maximum_length FROM information_schema.columns WHERE "
                                 f"table_schema=DATABASE() AND table_name='{tbl}' AND column_name IN ('number', 'name') "
                                 "ORDER BY column_name"), [["255"], ["100"]] if "item" not in tbl else [["255"]])

    def test_enums_and_defaults(self):
        defs = ok(self, S["admin"].get("Metadata"))["entityDefs"]
        for entity in DOCS:
            fields = defs[entity]["fields"]
            self.assertEqual(fields["taxMode"]["options"], ["individual", "group", "group_tax_inc"])
            self.assertEqual(fields["sourceFormula"]["options"], ["", "noLineTax", "lineTaxNotApplied",
                                                                  "taxIncludedInPrice", "groupTaxAdded", "unverified"])
            self.assertEqual(fields["totalsCheck"]["options"], ["", "exact", "rounded", "mismatch", "unverified"])
            self.assertEqual(fields["status"]["default"], "Created")
            self.assertIn("", fields["status"]["options"], "an empty source status stays empty")
        self.assertEqual(defs["Quote"]["fields"]["status"]["options"], ["", "Created", "Delivered", "Reviewed",
                                                                        "Accepted", "Rejected"])

    def test_single_legal_entity(self):
        self.assertEqual(sql("SELECT COUNT(*) FROM legal_entity WHERE deleted=0"), [["1"]])
        self.assertEqual(S["admin"].post("LegalEntity", {"name": f"{TAG} second"})[0], 403)
        self.assertEqual(S["admin"].delete(f"LegalEntity/{S['legalEntity']}")[0], 403)
        self.assertEqual(c("dir").get(f"LegalEntity/{S['legalEntity']}")[0], 200)
        self.assertEqual(c("dir").put(f"LegalEntity/{S['legalEntity']}", {"name": "x"})[0], 403)
        self.assertIn("no changes", espo_console("itvolga-setup-finance"), "setup is idempotent")


# ---------------------------------------------------------------------------------------------------- calculation
class CalculationTest(unittest.TestCase):
    def test_create_calculates_numbers_and_defaults(self):
        for entity, (item, *_) in DOCS.items():
            first_prefix = "ПРЕД_" if entity == "Quote" else "ЗАКАЗ_"
            number = counter(entity)
            created = doc(entity, [
                line(quantity="2.5", unitPrice="1333.33", discountPercent="7.5", purchaseCost="100"),
                line(S["product2"], quantity="3", unitPrice="33.335", discountAmount="0.01", description="Часы"),
            ], discountAmount="83.33", shippingAmount="150", adjustment="-0.5")
            got = ok(self, c("dir").get(f"{entity}/{created['id']}"))
            self.assertEqual(got["number"], f"{first_prefix}{number}", entity)
            self.assertGreaterEqual(number, 25 if entity == "Quote" else 15)
            self.assertEqual(counter(entity), number + 1)
            self.assertEqual((got["subtotal"], got["preTaxTotal"], got["grandTotal"]),
                             ("3183.33000000", "3250.00000000", "3249.50000000"), entity)
            self.assertEqual((got["status"], got["legalEntityId"], got["grandTotalCurrency"]),
                             ("Created", S["legalEntity"], "RUB"))
            self.assertEqual((got["sourceFormula"], got["totalsCheck"]), ("", ""))
            lines = got["itemList"]
            self.assertEqual([(i["order"], i["amount"], i["margin"]) for i in lines],
                             [(1, "3083.33000000", "2983.33000000"), (2, "100.00000000", "100.00000000")])
            self.assertEqual((lines[1]["productName"], lines[1]["description"]), (f"{TAG} product", "Часы"))
            items = ok(self, c("dir").get(f"{entity}/{created['id']}/items"))
            self.assertEqual(items["total"], 2, "items are records of their own")

    def test_refusals_change_nothing(self):
        cases = [
            ({"itemList": [line(quantity=1.5)]}, "financeFloat"),
            ({"itemList": [line()], "shippingAmount": 10.5}, "financeFloat"),
            ({"itemList": [line(unitPrice="1,5")]}, "financeNotDecimal"),
            ({"itemList": [line(), line(taxRate="18")]}, "financeVat"),
            ({"itemList": [line(discountAmount="1", discountPercent="1")]}, "financeBothDiscounts"),
            ({"itemList": [line(discountAmount="101")]}, "financeNegativeLine"),
            ({"itemList": [line(quantity="0")]}, "financeNonPositiveQuantity"),
            ({"itemList": []}, "financeNoLines"),
            ({"itemList": [line(product="no-such-product")]}, "financeUnknownProduct"),
            ({"itemList": [line(quantity="1" + "0" * 9, unitPrice="1" + "0" * 9)]}, "financeTooLarge"),
            ({"itemList": [line(quantity="1.0001")]}, "financeTooManyDecimals"),
            ({"itemList": [line()], "adjustment": "-101"}, "financeNegativeTotal"),
        ]
        for entity in DOCS:
            before = counts(entity)
            for data, expected in cases:
                result = c("dir").post(entity, {"name": f"{TAG} refused", "accountId": S["account"], **data})
                self.assertEqual((result[0], label(result)), (400, expected), f"{entity} {data}")
            self.assertEqual(counts(entity), before, f"{entity}: no document, item or number is taken")

    def test_vat_message_names_the_line(self):
        result = c("dir").post("Quote", {"name": f"{TAG} vat", "accountId": S["account"],
                                         "itemList": [line(), line(taxRate="18")]})
        self.assertEqual(result[1]["messageTranslation"]["data"]["place"], "Строка 2, «НДС, %»")

    def test_edit_add_change_and_delete_lines(self):
        for entity, (item, _, item_table) in DOCS.items():
            created = doc(entity, [line(unitPrice="10"), line(unitPrice="20"), line(unitPrice="30")])
            a, b, _c = ok(self, c("dir").get(f"{entity}/{created['id']}"))["itemList"]
            updated = ok(self, c("dir").put(f"{entity}/{created['id']}", {"itemList": [
                {**b, "quantity": "2"}, a, line(unitPrice="0.01")]}))
            self.assertEqual(updated["grandTotal"], "50.01000000", entity)
            lines = updated["itemList"]
            self.assertEqual([(i["id"], i["order"]) for i in lines[:2]], [(b["id"], 1), (a["id"], 2)])
            self.assertEqual(lines[0]["amount"], "40.00000000")
            self.assertEqual(sql(f"SELECT deleted FROM {item_table} WHERE id='{_c['id']}'"), [["1"]], "line deleted")
            self.assertEqual(ok(self, c("dir").get(f"{entity}/{created['id']}/items"))["total"], 3)

    def test_header_only_edit_keeps_totals_and_items(self):
        created = doc("Quote", [line(unitPrice="10")])
        stamp = sql(f"SELECT modified_at FROM quote_item WHERE quote_id='{created['id']}'")
        updated = ok(self, c("dir").put(f"Quote/{created['id']}", {"status": "Accepted", "description": "x"}))
        self.assertEqual((updated["status"], updated["grandTotal"]), ("Accepted", "10.00000000"))
        self.assertEqual(sql(f"SELECT modified_at FROM quote_item WHERE quote_id='{created['id']}'"), stamp)
        discounted = ok(self, c("dir").put(f"Quote/{created['id']}", {"discountPercent": "10"}))
        self.assertEqual(discounted["grandTotal"], "9.00000000", "a header input recalculates the stored lines")

    def test_items_of_another_document_are_refused(self):
        first = doc("Quote", [line()])
        second = doc("Quote", [line()])
        foreign = ok(self, c("dir").get(f"Quote/{second['id']}"))["itemList"][0]
        result = c("dir").put(f"Quote/{first['id']}", {"itemList": [foreign]})
        self.assertEqual((result[0], label(result)), (400, "financeUnknownLine"))

    def test_delete_document_deletes_items(self):
        created = must(c("dir").post("SalesOrder", {"name": f"{TAG} del", "accountId": S["account"],
                                                   "itemList": [line(), line()]}))
        self.assertEqual(c("dir").delete(f"SalesOrder/{created['id']}")[0], 200)
        self.assertEqual(sql(f"SELECT COUNT(*), SUM(deleted) FROM sales_order_item WHERE sales_order_id='{created['id']}'"),
                         [["2", "2"]])

    def test_concurrent_save_uses_the_locked_header(self):
        """A save that waited for the document lock calculates with what was committed meanwhile, not with the
        values it loaded before, and writes its totals even when they equal the stale loaded ones (the ORM writes
        only attributes that differ from the fetched values)."""
        created = doc("Quote", [line(unitPrice="100")])
        qid = created["id"]
        # --unbuffered: the client runs each statement as it arrives and prints its result at once.
        holder = subprocess.Popen(
            ["sudo", "-n", "mysql", f"--socket={MYSQL_SOCKET}", "-N", "-B", "--unbuffered", DB_NAME],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        result = {}
        try:
            holder.stdin.write(f"START TRANSACTION; SELECT id FROM quote WHERE id='{qid}' FOR UPDATE;\n")
            holder.stdin.flush()
            ready, _, _ = select.select([holder.stdout], [], [], 15)
            self.assertTrue(ready, "the locking session answers")
            self.assertEqual(holder.stdout.readline().strip(), qid, "the row is locked by another session")
            saver = threading.Thread(target=lambda: result.update(r=c("dir").put(f"Quote/{qid}", {"adjustment": "-5"})))
            saver.start()
            saver.join(3)
            self.assertTrue(saver.is_alive(), "the save waits for the document lock")
            # Another save commits shipping 0 → 5 with its totals (100 → 105) after the waiting one loaded the quote.
            holder.stdin.write(f"UPDATE quote SET shipping_amount=5, pre_tax_total=105, grand_total=105 "
                               f"WHERE id='{qid}'; COMMIT;\n")
            holder.stdin.close()
            holder.wait(15)
            saver.join(30)
        finally:
            if holder.poll() is None:
                holder.kill()
                holder.wait(5)
            for stream in (holder.stdin, holder.stdout, holder.stderr):
                stream.close()
        saved = ok(self, result["r"])
        self.assertEqual((saved["shippingAmount"], saved["grandTotal"]), ("5.00000000", "100.00000000"),
                         "the response shows the stored header")
        got = ok(self, c("dir").get(f"Quote/{qid}"))
        # 100 + 5 − 5 = 100: equal to the total the waiting save loaded, still written over the committed 105.
        self.assertEqual((got["shippingAmount"], got["adjustment"], got["preTaxTotal"], got["grandTotal"]),
                         ("5.00000000", "-5.00000000", "105.00000000", "100.00000000"))

    def test_preview_writes_nothing(self):
        before = counts("Quote")
        preview = ok(self, c("dir").request("POST", "FinanceDocument/Quote/calculate", {"attributes": {
            "itemList": [line(quantity="2", unitPrice="10")], "shippingAmount": "5"}}))
        self.assertEqual((preview["recalculated"], preview["grandTotal"], preview["lines"][0]["amount"]),
                         (True, "25.00", "20.00"))
        refused = ok(self, c("dir").request("POST", "FinanceDocument/Quote/calculate", {"attributes": {
            "itemList": [line(taxRate="18")]}}))
        self.assertEqual((refused["error"]["line"], refused["error"]["field"]), (1, "taxRate"))
        floats = ok(self, c("dir").request("POST", "FinanceDocument/Quote/calculate", {"attributes": {
            "itemList": [line()], "adjustment": 0.5}}))
        self.assertEqual(floats["error"]["field"], "adjustment")
        self.assertEqual(counts("Quote"), before)

    def test_numbers_skip_taken_ones(self):
        nxt = counter("Quote")
        holder = doc("Quote", [line()])  # takes ПРЕД_<nxt>
        taker = doc("Quote", [line()])
        sql(f"UPDATE quote SET number='ПРЕД_{nxt + 2}' WHERE id='{taker['id']}'")  # as an imported number would be
        after = doc("Quote", [line()])
        self.assertEqual(ok(self, c("dir").get(f"Quote/{after['id']}"))["number"], f"ПРЕД_{nxt + 3}")
        self.assertEqual(ok(self, c("dir").get(f"Quote/{holder['id']}"))["number"], f"ПРЕД_{nxt}")
        dry = espo_console("itvolga-setup-finance", "--dry-run", f"--next=Quote:{counter('Quote') + 10}")
        self.assertIn("counter ~ Quote", dry)
        self.assertIn("no changes", espo_console("itvolga-setup-finance", "--next=Quote:1"), "never lowered")


# ---------------------------------------------------------------------------------------------------- imported documents
class ImportedDocumentTest(unittest.TestCase):
    """Owner decision 2026-10-01: an imported document keeps the Vtiger totals (D-05) until its calculation inputs
    change; then it is recalculated like a new one, historical 18 % lines are refused (D-21), the originals stay."""

    def setUp(self):
        created = doc("Quote", [line(quantity="2", unitPrice="1000"), line(unitPrice="500")])
        self.id = created["id"]
        self.vt = VT_BASE + secrets.randbelow(1_000_000)
        # The importer writes source values as they are; here SQL plays its part (synthetic values only).
        sql(f"UPDATE quote SET vtiger_id={self.vt}, number='SYNTH-{RUN}-{self.vt}', subtotal=2500, pre_tax_total=2500, "
            f"grand_total=2500, vtiger_data='{{\"region_id\":null}}' WHERE id='{self.id}'")
        sql(f"UPDATE quote_item SET tax_rate=18, margin=0 WHERE quote_id='{self.id}'")
        out = espo_console("itvolga-finance-verify", "--entity=Quote", f"--id={self.id}")
        self.assertIn("Quote: lineTaxNotApplied / exact — 1", out)

    def get(self, client="admin"):
        return ok(self, (S["admin"] if client == "admin" else c(client)).get(f"Quote/{self.id}"))

    def test_source_marks_and_non_money_edits(self):
        got = self.get()
        self.assertEqual((got["sourceFormula"], got["totalsCheck"], got["grandTotal"]),
                         ("lineTaxNotApplied", "exact", "2500.00000000"))
        lines = got["itemList"]
        edited = ok(self, c("dir").put(f"Quote/{self.id}", {"status": "Accepted", "itemList": [
            {**lines[1], "description": "новое описание"}, lines[0]]}))
        self.assertEqual((edited["sourceFormula"], edited["grandTotal"]), ("lineTaxNotApplied", "2500.00000000"),
                         "product, description and order are not calculation inputs")
        self.assertEqual([i["taxRate"] for i in edited["itemList"]], ["18.000", "18.000"])
        self.assertEqual(edited["number"], f"SYNTH-{RUN}-{self.vt}", "the original number is kept")

    def test_money_edit_with_historical_vat_is_refused(self):
        lines = self.get()["itemList"]
        result = c("dir").put(f"Quote/{self.id}", {"itemList": [{**lines[0], "quantity": "3"}, lines[1]]})
        self.assertEqual((result[0], label(result)), (400, "financeVat"))
        got = self.get()
        self.assertEqual((got["grandTotal"], got["sourceFormula"], got["itemList"][0]["quantity"]),
                         ("2500.00000000", "lineTaxNotApplied", "2.000"))

    def test_money_edit_replaces_and_keeps_source_totals(self):
        lines = self.get()["itemList"]
        edited = ok(self, c("dir").put(f"Quote/{self.id}", {"itemList": [
            {**lines[0], "quantity": "3", "taxRate": "0"}, {**lines[1], "taxRate": "0"}]}))
        self.assertEqual((edited["grandTotal"], edited["sourceFormula"], edited["totalsCheck"]),
                         ("3500.00000000", "", ""))
        self.assertNotIn("vtigerData", edited, "originals are visible to administrators only")
        snapshot = self.get()["vtigerData"]["sourceTotals"]
        self.assertEqual((snapshot["grandTotal"], snapshot["sourceFormula"], snapshot["totalsCheck"]),
                         ("2500.00000000", "lineTaxNotApplied", "exact"))
        self.assertEqual([x["taxRate"] for x in snapshot["lines"]], ["18.000", "18.000"])
        self.assertIsNone(self.get()["vtigerData"]["region_id"], "source values stay")
        again = ok(self, c("dir").put(f"Quote/{self.id}", {"discountAmount": "100"}))
        self.assertEqual(again["grandTotal"], "3400.00000000")
        self.assertEqual(self.get()["vtigerData"]["sourceTotals"], snapshot, "originals are written once")
        # Source marks written late (a verification that read the quote before the recalculation) change nothing:
        # a document with kept originals is calculated in EspoCRM for good.
        sql(f"UPDATE quote SET source_formula='lineTaxNotApplied', totals_check='exact' WHERE id='{self.id}'")
        late = ok(self, c("dir").put(f"Quote/{self.id}", {"discountAmount": "200"}))
        self.assertEqual((late["grandTotal"], late["sourceFormula"]), ("3300.00000000", ""))
        self.assertEqual(self.get()["vtigerData"]["sourceTotals"], snapshot, "originals are never replaced")
        self.assertIn("Quote: recalculated in EspoCRM (skipped) — 1",
                      espo_console("itvolga-finance-verify", "--entity=Quote", f"--id={self.id}"))


# ---------------------------------------------------------------------------------------------------- quote → order
class ConversionTest(unittest.TestCase):
    def test_create_sales_order_from_quote(self):
        quote = doc("Quote", [line(quantity="2", unitPrice="10", description="копия"), line(taxRate="0")],
                    shippingAmount="5")
        attributes = ok(self, c("dir").get(f"FinanceDocument/Quote/{quote['id']}/convertTo/SalesOrder"))
        self.assertEqual((attributes["quoteId"], attributes["accountId"], attributes["shippingAmount"]),
                         (quote["id"], S["account"], "5.00000000"))
        self.assertTrue(all("id" not in x and "amount" not in x for x in attributes["itemList"]))
        self.assertNotIn("number", attributes)
        order = create("SalesOrder", attributes, c("dir"))
        got = ok(self, c("dir").get(f"SalesOrder/{order['id']}"))
        self.assertTrue(got["number"].startswith("ЗАКАЗ_"))
        self.assertEqual((got["quoteId"], got["grandTotal"], got["itemList"][0]["description"]),
                         (quote["id"], "125.00000000", "копия"))
        related = ok(self, c("dir").get(f"Quote/{quote['id']}/salesOrders"))
        self.assertEqual([r["id"] for r in related["list"]], [order["id"]])
        self.assertEqual(c("dep").get(f"FinanceDocument/Quote/{quote['id']}/convertTo/SalesOrder")[0], 403)


# ---------------------------------------------------------------------------------------------------- access
class AccessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.quote = doc("Quote", [line()])
        cls.order = doc("SalesOrder", [line()])
        cls.item = must(c("dir").get(f"Quote/{cls.quote['id']}"))["itemList"][0]["id"]

    def test_only_the_director_sees_finance(self):
        for user in ("dep", "sales", "cust", "norole"):
            for scope in ("Quote", "SalesOrder", "QuoteItem", "SalesOrderItem", "LegalEntity"):
                self.assertEqual(c(user).get(scope)[0], 403, f"{user} list {scope}")
            self.assertEqual(c(user).get(f"Quote/{self.quote['id']}")[0], 403, user)
            self.assertEqual(c(user).get(f"QuoteItem/{self.item}")[0], 403, user)
            self.assertEqual(c(user).request("POST", "FinanceDocument/Quote/calculate",
                                             {"attributes": {"itemList": [line()]}})[0], 403, user)
        self.assertEqual(c("dir").get(f"QuoteItem/{self.item}")[0], 200)
        self.assertEqual(c("dir").get(f"SalesOrder/{self.order['id']}")[0], 200)

    def test_items_are_never_written_directly(self):
        for client in (S["admin"], c("dir")):
            self.assertEqual(client.post("QuoteItem", {"quoteId": self.quote["id"], "productId": S["product"],
                                                       "quantity": "1", "unitPrice": "1"})[0], 403)
            self.assertEqual(client.put(f"QuoteItem/{self.item}", {"quantity": "5"})[0], 403)
            self.assertEqual(client.delete(f"QuoteItem/{self.item}")[0], 403)
            self.assertEqual(client.request("POST", f"Quote/{self.quote['id']}/items", {"id": self.item})[0], 403)
            self.assertEqual(client.request("DELETE", f"Quote/{self.quote['id']}/items", {"id": self.item})[0], 403)
            self.assertIn(client.post("MassAction", {"entityType": "QuoteItem", "action": "update",
                                                     "params": {"ids": [self.item]}, "data": {"quantity": "9"}})[0],
                          (400, 403))
        self.assertEqual(sql(f"SELECT quantity, deleted FROM quote_item WHERE id='{self.item}'"), [["1.000", "0"]])

    def test_item_access_follows_the_document(self):
        mine = doc("Quote", [line(), line()], client=c("own"))
        theirs = self.quote
        mine_items = {i["id"] for i in must(c("own").get(f"Quote/{mine['id']}"))["itemList"]}
        listed = {i["id"] for i in ok(self, c("own").get("QuoteItem", maxSize=200))["list"]}
        self.assertEqual(listed, mine_items, "the list holds the items of the user's own documents only")
        self.assertEqual(c("own").get(f"Quote/{theirs['id']}")[0], 403)
        self.assertEqual(c("own").get(f"QuoteItem/{self.item}")[0], 403)
        self.assertEqual(c("own").get(f"QuoteItem/{next(iter(mine_items))}")[0], 200)


if __name__ == "__main__":
    unittest.main()
