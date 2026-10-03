"""Stage 04.6 acceptance tests on the local stand: the end-to-end finance scenario (synthetic data).

Run: task test:stage04   (or: python3 -m unittest tests.stage04.test_stage04_6 from tests/stage04)

Covers: the full chain Quote → «Создать заказ» → «Создать счёт» → «Создать акт» → «Добавить платёж» on one record set
(header, owner, teams, tax mode, discounts, shipping and adjustment carried; totals and taxes; links and navigation;
statuses never derived; numbers taken once and never changed; access of every role); the variants the source allows
without a quote or an order (an invoice alone, an order invoiced and paid directly, an order linked afterwards, an act
without an invoice, imported invoice + act + payment, historical 18 % lines through «Создать акт»); the integration
fixes of the stage — teams of a conversion (G1), a payment's status change and removal need read access to every
document of the payment, the number of a stored record changes only by the import, the navigation panels; and that
docs/migration/finance-coverage.md is current. Every record, user, team and role is created by the run (names start
with SYNTH-<run id>) and deleted at the end.
"""
import re
import secrets
import subprocess
import sys
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "stage03"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from espo import REPO, Client, admin_credentials, espo_console, sql  # noqa: E402
from test_stage04_2 import label, must, ok  # noqa: E402
from test_stage04_4 import import_save  # noqa: E402

RUN = secrets.token_hex(3)
TAG = f"SYNTH-{RUN}"
VT_BASE = 500_000_000 + secrets.randbelow(90_000_000)
INVOICE_DATES = {"dateInvoiced": "2026-10-03", "dateDue": "2026-10-17"}
ACT_DATE = {"dateAct": "2026-10-03"}
PAID = {"datePaid": "2026-10-03"}
TABLES = {"Quote": "quote", "SalesOrder": "sales_order", "Invoice": "invoice", "Act": "act", "Payment": "payment"}
PREFIX = {"Quote": "ПРЕД_", "SalesOrder": "ЗАКАЗ_", "Invoice": "С-", "Act": "", "Payment": ""}
UNKNOWN = "financeAllocationUnknownTarget"
S = {}


def setUpModule():
    S.update(created=[], users={}, clients={})
    unittest.addModuleCleanup(cleanup)
    admin = Client(*admin_credentials())
    S["admin"] = admin
    roles = {r["name"]: r["id"] for r in must(admin.get("Role", maxSize=50))["list"]}
    # Own payments and invoices: a payment of this user may hold a row (given by the director) to an invoice the user
    # may not read.
    own_role = must(admin.post("Role", {"name": f"{TAG} own payments", "data": {
        "Payment": {"create": "yes", "read": "own", "edit": "own", "delete": "own", "stream": "own"},
        "PaymentAllocation": {"read": "all"}, "Invoice": {"create": "yes", "read": "own", "edit": "own"},
        "InvoiceItem": {"read": "all"}, "Product": {"read": "all"}, "Account": {"read": "all"}}}))
    S["own_role"] = own_role["id"]
    S["team"] = must(admin.post("Team", {"name": f"{TAG} team"}))["id"]
    for key, role_ids in (("dir", [roles["Директор"]]), ("dir2", [roles["Директор"]]),
                          ("dep", [roles["Заместитель директора"]]), ("sales", [roles["Менеджер по продажам"]]),
                          ("cust", [roles["Менеджер клиентов"]]), ("own", [own_role["id"]]), ("norole", [])):
        password = secrets.token_urlsafe(18) + "Aa1!"
        user = must(admin.post("User", {
            "userName": f"synth-{RUN}-{key}", "lastName": f"{TAG} {key}", "type": "regular", "isActive": True,
            "password": password, "passwordConfirm": password, "rolesIds": role_ids, "teamsIds": [S["team"]],
            "sendAccessInfo": False}))
        S["users"][key] = user["id"]
        S["clients"][key] = Client(f"synth-{RUN}-{key}", password)
    espo_console("itvolga-setup-acl")
    S["account"] = create("Account", {"name": f"{TAG} account"})["id"]
    S["contact"] = create("Contact", {"lastName": f"{TAG} contact", "accountId": S["account"]})["id"]
    S["opportunity"] = create("Opportunity", {"name": f"{TAG} deal", "accountId": S["account"],
                                              "closeDate": "2026-12-31"})["id"]
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
    if S.get("team"):
        admin.delete(f"Team/{S['team']}")
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


def get(entity, rid, client="dir"):
    return must((S["admin"] if client == "admin" else c(client)).get(f"{entity}/{rid}"))


def prefill(source, sid, target, client="dir"):
    return must(c(client).get(f"FinanceDocument/{source}/{sid}/convertTo/{target}"))


def invoice(lines=None, client="dir", **header):
    return create("Invoice", {"name": f"{TAG} invoice", "accountId": S["account"], **INVOICE_DATES,
                              "itemList": lines or [line()], **header}, c(client))


def counter(entity):
    return int(sql(f"SELECT value FROM next_number WHERE entity_type='{entity}' AND field_name='number'")[0][0])


def counters():
    return {entity: counter(entity) for entity in TABLES}


def column(entity, rid, name):
    """One stored value (the id is selected too: sql() drops a line that is empty)."""
    return sql(f"SELECT {name}, id FROM {TABLES[entity]} WHERE id='{rid}'")[0][0]


def number(entity, rid):
    return column(entity, rid, "number")


def status(entity, rid):
    return column(entity, rid, "status")


def settlement(entity, rid):
    return tuple(sql(f"SELECT paid_amount, balance_amount, settlement_state FROM {TABLES[entity]} WHERE id='{rid}'")[0])


def totals(got):
    return got["subtotal"], got["preTaxTotal"], got["grandTotal"]


def related(entity, rid, link, client="dir"):
    return {r["id"] for r in must(c(client).get(f"{entity}/{rid}/{link}", maxSize=200))["list"]}


def allocation_rows(pid):
    return sql("SELECT id, deleted, invoice_id, sales_order_id, amount FROM payment_allocation "
               f"WHERE payment_id='{pid}' ORDER BY `order`, id")


def imported(entity, number_, stored, lines, status_, **header):
    """A document written by the import path of stage 06.3 (ORM with IMPORT + SILENT), then classified by
    itvolga-finance-verify. `lines`: (quantity, price, tax rate) of each line. Returns the id."""
    vt = VT_BASE + secrets.randbelow(10_000_000)
    item, parent = {"Invoice": ("InvoiceItem", "invoiceId"), "Act": ("ActItem", "actId")}[entity]
    saved = import_save(entity, {"name": f"{TAG} imported {entity}", "number": number_, "accountId": S["account"],
                                 "status": status_, "taxMode": "individual", "subtotal": stored, "preTaxTotal": stored,
                                 "grandTotal": stored, "vtigerId": vt, "assignedUserId": S["users"]["dir"], **header})
    assert saved["ok"], saved
    S["created"].append((entity, saved["id"]))
    for order, (quantity, price, rate) in enumerate(lines, 1):
        amount = str(Decimal(quantity) * Decimal(price))
        row = import_save(item, {parent: saved["id"], "productId": S["product"], "name": f"{TAG} service",
                                 "order": order, "vtigerId": vt + order, "quantity": quantity, "unitPrice": price,
                                 "taxRate": rate, "discountAmount": "0", "purchaseCost": "0", "amount": amount,
                                 "margin": "0"})
        assert row["ok"], row
    espo_console("itvolga-finance-verify", f"--entity={entity}", f"--id={saved['id']}")
    return saved["id"]


def chain():
    """One record set through every action of the chain, as the director: the quote has another owner (dir2), a team,
    a contact, a deal, a non-default tax mode and status, line and header discounts, shipping and an adjustment."""
    before = counters()
    quote = create("Quote", {
        "name": f"{TAG} chain", "accountId": S["account"], "contactId": S["contact"],
        "opportunityId": S["opportunity"], "assignedUserId": S["users"]["dir2"], "teamsIds": [S["team"]],
        "status": "Accepted", "taxMode": "group_tax_inc", "discountPercent": "5", "shippingAmount": "7.50",
        "adjustment": "-0.26", "billingAddressCity": f"{TAG} city", "shippingAddressStreet": f"{TAG} street",
        "termsAndConditions": f"{TAG} terms", "description": f"{TAG} description",
        "itemList": [line(quantity="2.5", unitPrice="100", discountPercent="10", purchaseCost="80"),
                     line(quantity="3", unitPrice="33.335", purchaseCost="20")]}, c("dir"))
    forms = {"SalesOrder": prefill("Quote", quote["id"], "SalesOrder")}
    order = create("SalesOrder", forms["SalesOrder"], c("dir"))
    must(c("dir").put(f"SalesOrder/{order['id']}", {"status": "Approved"}))
    forms["Invoice"] = prefill("SalesOrder", order["id"], "Invoice")
    inv = create("Invoice", {**forms["Invoice"], **INVOICE_DATES}, c("dir"))
    must(c("dir").put(f"Invoice/{inv['id']}", {"status": "Sent"}))
    forms["Act"] = prefill("Invoice", inv["id"], "Act")
    act = create("Act", {**forms["Act"], **ACT_DATE}, c("dir"))
    forms["Payment"] = prefill("Invoice", inv["id"], "Payment")
    pay = create("Payment", {**forms["Payment"], **PAID}, c("dir"))
    return {"before": before, "forms": forms, "Quote": quote["id"], "SalesOrder": order["id"], "Invoice": inv["id"],
            "Act": act["id"], "Payment": pay["id"]}


# ---------------------------------------------------------------------------------------------------- the chain
class ChainTest(unittest.TestCase):
    """Quote → SalesOrder → Invoice → Act, and a payment of the invoice, on one record set (the source never ran the
    whole chain: quotes never became orders, invoices of orders have no act — finance-contract.md §9)."""

    @classmethod
    def setUpClass(cls):
        cls.c = chain()
        cls.docs = {e: get(e, cls.c[e]) for e in ("Quote", "SalesOrder", "Invoice", "Act")}

    def test_forms_carry_header_owner_and_teams(self):
        quote, forms = self.docs["Quote"], self.c["forms"]
        team = {"teamsIds": [S["team"]], "teamsNames": {S["team"]: f"{TAG} team"}}
        for target, form in forms.items():
            if target == "Payment":
                continue
            self.assertEqual({k: form.get(k) for k in team}, team, f"{target}: the source teams (G1)")
            self.assertEqual((form["assignedUserId"], form["accountId"], form["contactId"], form["taxMode"],
                              form["discountPercent"], form["shippingAmount"], form["adjustment"],
                              form["billingAddressCity"], form["shippingAddressStreet"], form["description"]),
                             (S["users"]["dir2"], S["account"], S["contact"], "group_tax_inc", quote["discountPercent"],
                              quote["shippingAmount"], quote["adjustment"], f"{TAG} city", f"{TAG} street",
                              f"{TAG} description"), target)
            for absent in ("number", "status", "vtigerId", "legalEntityId", "subtotal", "grandTotal", "sourceFormula"):
                self.assertNotIn(absent, form, f"{target}: {absent} is not copied")
            self.assertTrue(all("id" not in x and "amount" not in x for x in form["itemList"]), target)
        self.assertEqual((forms["SalesOrder"]["quoteId"], forms["SalesOrder"]["opportunityId"]),
                         (self.c["Quote"], S["opportunity"]))
        self.assertEqual((forms["Invoice"]["salesOrderId"], forms["Invoice"]["quoteId"],
                          forms["Invoice"]["termsAndConditions"]), (self.c["SalesOrder"], self.c["Quote"], f"{TAG} terms"))
        self.assertEqual(forms["Act"]["invoicesIds"], [self.c["Invoice"]])
        for absent in ("opportunityId", "quoteId", "salesOrderId", "termsAndConditions"):
            self.assertNotIn(absent, forms["Act"], "an act has no deal, quote, order or terms (D-69)")
        payment = forms["Payment"]
        self.assertEqual((payment["assignedUserId"], payment["payerType"], payment["payerId"], payment["amount"]),
                         (S["users"]["dir"], "Account", S["account"], "316.00"), "D-67: the current user pays")
        self.assertNotIn("teamsIds", payment)
        # A source without teams gives an empty list, not null: the form takes nothing of the user's defaults.
        bare = create("Quote", {"name": f"{TAG} bare", "accountId": S["account"], "itemList": [line()]}, c("dir"))
        self.assertEqual(prefill("Quote", bare["id"], "Invoice")["teamsIds"], [])

    def test_saved_documents_keep_the_header(self):
        for entity, got in self.docs.items():
            self.assertEqual((got["assignedUserId"], got["teamsIds"], got["createdById"], got["accountId"],
                              got["contactId"], got["taxMode"], got["legalEntityId"]),
                             (S["users"]["dir2"], [S["team"]], S["users"]["dir"], S["account"], S["contact"],
                              "group_tax_inc", S["legalEntity"]), entity)
            self.assertEqual(got.get("opportunityId"), None if entity == "Act" else S["opportunity"], entity)
        pay = get("Payment", self.c["Payment"])
        self.assertEqual((pay["assignedUserId"], pay["legalEntityId"], pay["status"], pay["direction"]),
                         (S["users"]["dir"], S["legalEntity"], "Executed", "incoming"))
        # A later owner change of the quote stays on the quote.
        ok(self, c("dir").put(f"Quote/{self.c['Quote']}", {"assignedUserId": S["users"]["dir"]}))
        for entity in ("SalesOrder", "Invoice", "Act"):
            self.assertEqual(get(entity, self.c[entity])["assignedUserId"], S["users"]["dir2"], entity)

    def test_totals_and_taxes_along_the_chain(self):
        # Lines: 2.5 × 100 − 10 % = 225.00; 3 × 33.335 = 100.005 → 100.01 (D-29). Subtotal 325.01, 5 % = 16.25,
        # + 7.50 shipping = 316.26, − 0.26 adjustment = 316.00; no tax in any mode (D-21).
        expected = ("325.01000000", "316.26000000", "316.00000000")
        for entity, got in self.docs.items():
            self.assertEqual(totals(got), expected, entity)
            self.assertEqual([(x["amount"], x["margin"]) for x in got["itemList"]],
                             [("225.00000000", "145.00000000"), ("100.01000000", "80.01000000")], entity)
            self.assertEqual({Decimal(x["taxRate"]) for x in got["itemList"]}, {Decimal(0)}, entity)
        self.assertEqual(get("Payment", self.c["Payment"])["amount"], "316.00000000")
        self.assertEqual(settlement("Invoice", self.c["Invoice"]), ("316.00000000", "0.00000000", "paid"))
        self.assertEqual(settlement("SalesOrder", self.c["SalesOrder"])[2], "unpaid",
                         "a payment of the invoice does not pay its order")

    def test_links_and_navigation(self):
        q, so, inv, act, pay = (self.c[e] for e in ("Quote", "SalesOrder", "Invoice", "Act", "Payment"))
        self.assertEqual((related("Quote", q, "salesOrders"), related("Quote", q, "invoices")), ({so}, {inv}))
        self.assertEqual((related("SalesOrder", so, "invoices"), related("Act", act, "invoices")), ({inv}, {inv}))
        shown = get("Invoice", inv)
        self.assertEqual((shown["quoteId"], shown["salesOrderId"], shown["actId"], shown["actName"]),
                         (q, so, act, self.docs["Act"]["name"]))
        [allocation] = must(c("dir").get(f"Invoice/{inv}/paymentAllocations"))["list"]
        self.assertEqual((allocation["paymentId"], allocation["amount"]), (pay, "316.00000000"))
        self.assertEqual(must(c("dir").get(f"SalesOrder/{so}/paymentAllocations"))["list"], [])
        self.assertEqual(get("Payment", pay)["allocationList"][0]["invoiceId"], inv)
        for party, rid in (("Account", S["account"]), ("Contact", S["contact"])):
            for link, record in (("cQuotes", q), ("cSalesOrders", so), ("cInvoices", inv), ("cActs", act)):
                self.assertIn(record, related(party, rid, link), f"{party}.{link}")
        self.assertIn(pay, related("Account", S["account"], "cPayments"), "the account is the payer")
        for link, record in (("cQuotes", q), ("cSalesOrders", so), ("cInvoices", inv)):
            self.assertIn(record, related("Opportunity", S["opportunity"], link), link)
        self.assertEqual(c("dir").get(f"FinanceDocument/Act/{act}/convertTo/Payment")[0], 404, "no payments of acts")

    def test_statuses_are_never_derived(self):
        expected = {"Quote": "Accepted", "SalesOrder": "Approved", "Invoice": "Sent", "Act": "Created"}
        self.assertEqual({e: status(e, self.c[e]) for e in expected}, expected,
                         "a conversion gives the new document its own default, the source keeps its status (D-26)")
        pay = self.c["Payment"]
        ok(self, c("dir").put(f"Payment/{pay}", {"status": "Canceled"}))
        self.assertEqual(settlement("Invoice", self.c["Invoice"])[2], "unpaid")
        ok(self, c("dir").put(f"Payment/{pay}", {"status": "Executed"}))
        self.assertEqual(settlement("Invoice", self.c["Invoice"])[2], "paid")
        self.assertEqual({e: status(e, self.c[e]) for e in expected}, expected, "settlement never sets a status")

    def test_numbers_taken_once_and_never_changed(self):
        before = self.c["before"]
        numbers = {e: number(e, self.c[e]) for e in TABLES}
        self.assertEqual(numbers, {e: f"{PREFIX[e]}{before[e]}" for e in TABLES},
                         "each record takes the next number of its counter; prefills take none")
        for entity in TABLES:
            ok(self, c("dir").put(f"{entity}/{self.c[entity]}", {"number": f"{TAG}-x", "description": f"{TAG} edit"}))
        lines = get("Quote", self.c["Quote"])["itemList"]
        ok(self, c("dir").put(f"Quote/{self.c['Quote']}", {"itemList": [{**lines[0], "quantity": "3"}, lines[1]]}))
        espo_console("itvolga-finance-settle", "--entity=Invoice", f"--id={self.c['Invoice']}")
        self.assertEqual({e: number(e, self.c[e]) for e in TABLES}, numbers,
                         "API edits (the number is read-only), recalculation and settlement keep every number")

    def test_access_of_the_chain(self):
        ids = {e: self.c[e] for e in TABLES}
        for user in ("dep", "sales", "cust", "norole"):
            for entity, rid in ids.items():
                self.assertEqual(c(user).get(f"{entity}/{rid}")[0], 403, f"{user} {entity}")
                self.assertEqual(c(user).post(entity, {"name": f"{TAG} {user}"})[0], 403, f"{user} creates {entity}")
            for source, target in (("Quote", "SalesOrder"), ("Quote", "Invoice"), ("SalesOrder", "Invoice"),
                                   ("Invoice", "Act"), ("Invoice", "Payment"), ("SalesOrder", "Payment")):
                self.assertEqual(c(user).get(f"FinanceDocument/{source}/{ids[source]}/convertTo/{target}")[0], 403,
                                 f"{user} {source} → {target}")
            for link in ("cQuotes", "cSalesOrders", "cInvoices", "cActs", "cPayments"):
                self.assertEqual(c(user).get(f"Account/{S['account']}/{link}")[0], 403, f"{user} Account.{link}")
        for entity, rid in ids.items():
            self.assertEqual(c("dir").get(f"{entity}/{rid}")[0], 200, entity)


# ---------------------------------------------------------------------------------------------------- variants
class VariantTest(unittest.TestCase):
    """Variants of the source: most invoices have no quote and no order; orders are invoiced and paid directly."""

    def test_invoice_without_quote_or_order(self):
        inv = invoice([line(unitPrice="1500")])
        act = create("Act", {**prefill("Invoice", inv["id"], "Act"), **ACT_DATE}, c("dir"))
        pay = create("Payment", {**prefill("Invoice", inv["id"], "Payment"), **PAID}, c("dir"))
        shown = get("Invoice", inv["id"])
        self.assertEqual((shown["quoteId"], shown["salesOrderId"], shown["actId"]), (None, None, act["id"]))
        self.assertEqual((settlement("Invoice", inv["id"])[2], status("Invoice", inv["id"])), ("paid", "Created"))
        self.assertEqual((related("Act", act["id"], "invoices"), get("Payment", pay["id"])["amount"]),
                         ({inv["id"]}, "1500.00000000"))

    def test_order_invoiced_and_paid_directly(self):
        order = create("SalesOrder", {"name": f"{TAG} order", "accountId": S["account"],
                                      "itemList": [line(unitPrice="1000")]}, c("dir"))
        inv = create("Invoice", {**prefill("SalesOrder", order["id"], "Invoice"), **INVOICE_DATES}, c("dir"))
        self.assertEqual((get("Invoice", inv["id"])["quoteId"], get("Invoice", inv["id"])["salesOrderId"]),
                         (None, order["id"]))
        part = prefill("Invoice", inv["id"], "Payment")
        part["amount"] = part["allocationList"][0]["amount"] = "400.00"
        create("Payment", {**part, **PAID}, c("dir"))
        create("Payment", {**prefill("SalesOrder", order["id"], "Payment"), **PAID}, c("dir"))
        self.assertEqual(settlement("SalesOrder", order["id"]), ("1000.00000000", "0.00000000", "paid"))
        self.assertEqual(settlement("Invoice", inv["id"]), ("400.00000000", "600.00000000", "partial"),
                         "the order and its invoice are settled independently (2 orders of the source)")
        self.assertEqual((status("SalesOrder", order["id"]), status("Invoice", inv["id"])), ("Created", "Created"))
        self.assertIsNone(get("Invoice", inv["id"])["actId"])
        self.assertEqual(c("dir").get(f"FinanceDocument/Invoice/{inv['id']}/convertTo/Act")[0], 200,
                         "an invoice of an order may get an act (none of the source has one)")

    def test_order_linked_afterwards(self):
        inv = invoice()
        before = (number("Invoice", inv["id"]), status("Invoice", inv["id"]), totals(get("Invoice", inv["id"])))
        order = create("SalesOrder", {"name": f"{TAG} later order", "accountId": S["account"],
                                      "itemList": [line(unitPrice="90")]}, c("dir"))
        ok(self, c("dir").put(f"Invoice/{inv['id']}", {"salesOrderId": order["id"]}))
        self.assertEqual(related("SalesOrder", order["id"], "invoices"), {inv["id"]})
        self.assertEqual((number("Invoice", inv["id"]), status("Invoice", inv["id"]), totals(get("Invoice", inv["id"]))),
                         before, "a link set afterwards changes nothing else (3 invoices of the source)")

    def test_act_without_invoice(self):
        act = create("Act", {"name": f"{TAG} act", "accountId": S["account"], **ACT_DATE, "itemList": [line()]},
                     c("dir"))
        self.assertEqual(related("Act", act["id"], "invoices"), set())
        self.assertIn(act["id"], related("Account", S["account"], "cActs"))
        self.assertEqual(number("Act", act["id"]), str(int(number("Act", act["id"]))), "digits only")

    def test_imported_invoice_act_and_payment(self):
        vt = VT_BASE + secrets.randbelow(10_000_000)
        iid = imported("Invoice", f"СЧЕТ_{vt}", "1500.00000000", [("1", "1500", "0")], "Paid",
                       dateInvoiced="2019-04-01", balanceSource="1500.00000000",
                       vtigerData={"region_id": 0, "spcompany": "По умолчанию"})
        aid = imported("Act", "82", "1500.00000000", [("1", "1500", "0")], "Received", dateAct="2019-04-05",
                       vtigerData={"region_id": 0, "spcompany": "Default"})
        self.assertTrue(import_save("Invoice", {"actId": aid}, rid=iid)["ok"])
        pay = import_save("Payment", {"vtigerId": vt, "number": str(vt), "datePaid": "2019-04-10",
                                      "direction": "incoming", "status": "", "amount": "1500.00000000",
                                      "assignedUserId": S["users"]["dir"], "payerType": "Account",
                                      "payerId": S["account"], "vtigerData": {"spcompany": "Default"}})
        self.assertTrue(pay["ok"], pay)
        S["created"].append(("Payment", pay["id"]))
        self.assertTrue(import_save("PaymentAllocation", {"paymentId": pay["id"], "invoiceId": iid,
                                                          "amount": "1500", "source": "relatedTo"})["ok"])
        espo_console("itvolga-finance-settle", "--entity=Invoice", f"--id={iid}")
        numbers = {"Invoice": f"СЧЕТ_{vt}", "Act": "82", "Payment": str(vt)}
        ids = {"Invoice": iid, "Act": aid, "Payment": pay["id"]}
        self.assertEqual({e: number(e, ids[e]) for e in ids}, numbers, "source numbers as they are (D-17)")
        self.assertEqual(settlement("Invoice", iid), ("1500.00000000", "0.00000000", "paid"), "empty status counts")
        self.assertEqual((status("Invoice", iid), status("Act", aid), status("Payment", pay["id"])),
                         ("Paid", "Received", ""))
        self.assertEqual(related("Act", aid, "invoices"), {iid})
        refused = c("dir").get(f"FinanceDocument/Invoice/{iid}/convertTo/Act")
        self.assertEqual((refused[0], label(refused)), (409, "financeConversionLinked"))
        self.assertEqual(prefill("Invoice", iid, "Payment")["amount"], "1500.00")
        # Director's edits of imported records keep their numbers, statuses of the others and the source totals.
        ok(self, c("dir").put(f"Invoice/{iid}", {"status": "Sent"}))
        ok(self, c("dir").put(f"Payment/{pay['id']}", {"description": f"{TAG} edit"}))
        ok(self, c("dir").put(f"Act/{aid}", {"status": "Done"}))
        self.assertEqual({e: number(e, ids[e]) for e in ids}, numbers)
        self.assertEqual((totals(get("Invoice", iid)), totals(get("Act", aid))), (("1500.00000000",) * 3,) * 2)
        self.assertEqual(settlement("Invoice", iid)[2], "paid")

    def test_historical_vat_through_create_act(self):
        vt = VT_BASE + secrets.randbelow(10_000_000)
        iid = imported("Invoice", f"СЧЕТ_{vt}", "2500.00000000", [("2", "1000", "18"), ("1", "500", "18")], "Paid",
                       dateInvoiced="2017-05-01", balanceSource="2500.00000000",
                       vtigerData={"region_id": None, "spcompany": "По умолчанию"})
        stored = (totals(get("Invoice", iid)), sql(f"SELECT tax_rate, amount FROM invoice_item WHERE invoice_id='{iid}' "
                                                   "ORDER BY `order`"))
        form = prefill("Invoice", iid, "Act")
        self.assertEqual([Decimal(x["taxRate"]) for x in form["itemList"]], [Decimal(18)] * 2, "rates stay visible")
        before = counters()
        refused = c("dir").post("Act", {**form, **ACT_DATE})
        self.assertEqual((refused[0], label(refused)), (400, "financeVat"))
        self.assertEqual((counters(), get("Invoice", iid)["actId"]), (before, None), "nothing is written")
        lines = [{**x, "taxRate": "0"} for x in form["itemList"]]
        act = create("Act", {**form, **ACT_DATE, "itemList": lines}, c("dir"))
        self.assertEqual(totals(get("Act", act["id"])), ("2500.00000000",) * 3)
        self.assertEqual(get("Invoice", iid)["actId"], act["id"])
        self.assertEqual((totals(get("Invoice", iid)), sql(f"SELECT tax_rate, amount FROM invoice_item WHERE "
                                                          f"invoice_id='{iid}' ORDER BY `order`")), stored,
                         "the invoice keeps its historical lines and totals")
        self.assertEqual(number("Invoice", iid), f"СЧЕТ_{vt}")


# ---------------------------------------------------------------------------------------------------- fixes of 04.6
class PaymentAccessTest(unittest.TestCase):
    """A payment write that changes what is paid on a document needs read access to it (D-63): a status change and a
    removal change every document of the payment (owner decision 2026-10-03)."""

    def setUp(self):
        self.mine = invoice([line(unitPrice="40")], client="own")
        self.theirs = invoice([line(unitPrice="10")])
        self.pay = create("Payment", {"amount": "50", **PAID, "assignedUserId": S["users"]["own"],
                                      "allocationList": [{"invoiceId": self.mine["id"], "amount": "40"}]}, c("own"))
        rows = get("Payment", self.pay["id"])["allocationList"]
        ok(self, c("dir").put(f"Payment/{self.pay['id']}", {"allocationList": [
            {"id": rows[0]["id"], "invoiceId": self.mine["id"], "amount": "40"},
            {"invoiceId": self.theirs["id"], "amount": "10"}]}))
        self.assertEqual(c("own").get(f"Invoice/{self.theirs['id']}")[0], 403)

    def snapshot(self):
        pid = self.pay["id"]
        return (sql(f"SELECT status, deleted FROM payment WHERE id='{pid}'"), allocation_rows(pid),
                settlement("Invoice", self.mine["id"]), settlement("Invoice", self.theirs["id"]),
                sql(f"SELECT COUNT(*) FROM note WHERE parent_type='Payment' AND parent_id='{pid}'"))

    def test_status_change_needs_every_document(self):
        before = self.snapshot()
        refused = c("own").put(f"Payment/{self.pay['id']}", {"status": "Canceled"})
        self.assertEqual((refused[0], label(refused)), (400, UNKNOWN))
        self.assertEqual(self.snapshot(), before, "nothing is written")
        # Controls: the director may; the user may for a payment of own documents only.
        ok(self, c("dir").put(f"Payment/{self.pay['id']}", {"status": "Canceled"}))
        self.assertEqual((settlement("Invoice", self.mine["id"])[2], settlement("Invoice", self.theirs["id"])[2]),
                         ("unpaid", "unpaid"))
        only_mine = create("Payment", {"amount": "5", **PAID, "assignedUserId": S["users"]["own"], "allocationList": [
            {"invoiceId": self.mine["id"], "amount": "5"}]}, c("own"))
        ok(self, c("own").put(f"Payment/{only_mine['id']}", {"status": "Delayed"}))
        ok(self, c("own").put(f"Payment/{self.pay['id']}", {"description": f"{TAG} no settlement change"}))

    def test_removal_needs_every_document(self):
        before = self.snapshot()
        refused = c("own").delete(f"Payment/{self.pay['id']}")
        self.assertEqual((refused[0], label(refused)), (400, UNKNOWN))
        self.assertEqual(self.snapshot(), before, "nothing is removed")
        only_mine = create("Payment", {"amount": "5", **PAID, "assignedUserId": S["users"]["own"], "allocationList": [
            {"invoiceId": self.mine["id"], "amount": "5"}]}, c("own"))
        ok(self, c("own").delete(f"Payment/{only_mine['id']}"))
        ok(self, c("dir").delete(f"Payment/{self.pay['id']}"))
        self.assertEqual(settlement("Invoice", self.theirs["id"])[2], "unpaid")

    def test_import_is_not_limited(self):
        self.assertTrue(import_save("Payment", {"status": "Canceled"}, rid=self.pay["id"])["ok"])
        self.assertEqual(settlement("Invoice", self.theirs["id"])[2], "unpaid")
        self.assertTrue(import_save("Payment", {}, rid=self.pay["id"], op="remove")["ok"])
        self.assertEqual(sql(f"SELECT deleted FROM payment WHERE id='{self.pay['id']}'"), [["1"]])


class NumberGuardTest(unittest.TestCase):
    """The number of a stored document or payment changes only by the import (owner decision 2026-10-03)."""

    def test_orm_saves_keep_the_number(self):
        quote = create("Quote", {"name": f"{TAG} q", "accountId": S["account"], "itemList": [line()]}, c("dir"))
        order = create("SalesOrder", {"name": f"{TAG} so", "accountId": S["account"], "itemList": [line()]}, c("dir"))
        inv = invoice()
        act = create("Act", {"name": f"{TAG} act", "accountId": S["account"], **ACT_DATE, "itemList": [line()]},
                     c("dir"))
        pay = create("Payment", {"amount": "1", **PAID, "assignedUserId": S["users"]["dir"]}, c("dir"))
        for entity, rid in (("Quote", quote["id"]), ("SalesOrder", order["id"]), ("Invoice", inv["id"]),
                            ("Act", act["id"]), ("Payment", pay["id"])):
            kept = number(entity, rid)
            refused = import_save(entity, {"number": f"{TAG}-x", "description": f"{TAG} orm"}, rid=rid, imported=False)
            self.assertEqual((refused["ok"], refused.get("error"), refused.get("message")),
                             (False, "Espo\\Core\\Exceptions\\Forbidden", "financeNumberReadOnly"), entity)
            self.assertEqual(number(entity, rid), kept, entity)
            # Controls: an ORM save that keeps the number passes; the importer writes the source number (D-17).
            self.assertTrue(import_save(entity, {"description": f"{TAG} orm"}, rid=rid, imported=False)["ok"], entity)
            self.assertTrue(import_save(entity, {"number": kept, "description": f"{TAG} same"}, rid=rid,
                                        imported=False)["ok"], entity)
            moved = import_save(entity, {"number": f"{TAG}-{entity}"}, rid=rid)
            self.assertTrue(moved["ok"], moved)
            self.assertEqual(number(entity, rid), f"{TAG}-{entity}", entity)

    def test_empty_imported_number(self):
        aid = imported("Act", "", "100.00000000", [("1", "100", "0")], "", dateAct="2019-10-01",
                       vtigerData={"region_id": 0, "spcompany": "По умолчанию"})
        refused = import_save("Act", {"number": "403"}, rid=aid, imported=False)
        self.assertEqual((refused["ok"], refused.get("message")), (False, "financeNumberReadOnly"))
        ok(self, c("dir").put(f"Act/{aid}", {"number": "403", "status": "Created"}))
        self.assertEqual((number("Act", aid), status("Act", aid)), ("", "Created"), "the API drops the number")


class PanelTest(unittest.TestCase):
    """Relationship panels of finance documents are navigation: child documents are view-only on their source; on an
    account, a contact and a deal documents are created, never selected or unlinked (as in Vtiger)."""

    def test_panels(self):
        panels = must(S["admin"].get("Metadata"))["clientDefs"]
        view_only = "views/record/row-actions/relationship-view-only"
        for entity, link in (("Quote", "salesOrders"), ("Quote", "invoices"), ("SalesOrder", "invoices"),
                             ("Act", "invoices")):
            defs = panels[entity]["relationshipPanels"][link]
            self.assertEqual((defs.get("rowActionsView"), defs.get("createDisabled"), defs.get("selectDisabled"),
                              defs.get("unlinkDisabled")), (view_only, True, True, True), f"{entity}.{link}")
        for party, links in (("Account", ("cQuotes", "cSalesOrders", "cInvoices", "cActs", "cPayments")),
                             ("Contact", ("cQuotes", "cSalesOrders", "cInvoices", "cActs", "cPayments")),
                             ("Opportunity", ("cQuotes", "cSalesOrders", "cInvoices"))):
            for link in links:
                defs = panels[party]["relationshipPanels"][link]
                self.assertEqual((defs.get("selectDisabled"), defs.get("unlinkDisabled"), bool(defs.get("createDisabled"))),
                                 (True, True, False), f"{party}.{link}")


class CoverageTest(unittest.TestCase):
    def test_finance_coverage_is_current(self):
        result = subprocess.run([sys.executable, str(REPO / "scripts/model/build_finance_coverage.py"), "--check"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertRegex(result.stdout, re.compile(r"\d+ fields, \d+ relations, open 0"))

    def test_a_dictionary_without_options_or_decision_is_open(self):
        """A missing value map must not pass as «not used» (quality review of stage 04.6)."""
        sys.path.insert(0, str(REPO / "scripts/model"))
        import build_finance_coverage as coverage
        row = {"source_table": "vtiger_invoicestatus", "espo_check": "—"}
        text = "не используется: поле без данных, служебное или модуль без записей"
        self.assertEqual(coverage.disposition(row, "предложено", "переносится как опции enum", "entityDefs options",
                                              None, text, None)[0], "открыто")
        row["source_table"] = "vtiger_postatus"
        self.assertEqual(coverage.disposition(row, "предложено", "переносится как опции enum", "entityDefs options",
                                              None, text, None)[0], "исключено", "an explicit decision closes it")


if __name__ == "__main__":
    unittest.main()
