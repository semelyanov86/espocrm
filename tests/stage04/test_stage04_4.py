"""Stage 04.4 acceptance tests on the local stand: Payment and PaymentAllocation (synthetic data).

Run: task test:stage04   (or: python3 -m unittest tests.stage04.test_stage04_4 from tests/stage04)

Covers: model, DB columns and the generated dictionary; payments to one or several invoices and sales orders, partial
payment, overpayment and the unallocated rest; statuses that count (Executed, empty) and do not; re-applying the same
document (refused), re-saving the table (no duplicates, no writes, no notes), moving a payment to another document,
editing and cancelling an allocation, the sum control; refusals that change nothing; the history (payment stream,
document audit log); removal of payments and documents; the stored settlement under concurrent saves; access
(director only, rows follow their payment, no direct writes, no relate, no CSV import, no restore); «Добавить платёж»;
the import write path (ORM with SaveOption::IMPORT through tests/stage04/import_fixture.php) and itvolga-finance-settle.
Every record, user and role is created by the run (names start with SYNTH-<run id>) and deleted at the end.
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

RUN = secrets.token_hex(3)
TAG = f"SYNTH-{RUN}"
VT_BASE = 700_000_000 + secrets.randbelow(90_000_000)
DATES = {"dateInvoiced": "2026-10-02", "dateDue": "2026-10-16"}
FIXTURE = Path(__file__).resolve().parent / "import_fixture.php"
S = {}


def setUpModule():
    S.update(created=[], users={}, clients={})
    unittest.addModuleCleanup(cleanup)
    admin = Client(*admin_credentials())
    S["admin"] = admin
    S["adminId"] = must(admin.get("App/user"))["user"]["id"]
    roles = {r["name"]: r["id"] for r in must(admin.get("Role", maxSize=50))["list"]}
    # Rows follow their payment whatever their own level; invoices of others are not readable for this role.
    own_role = must(admin.post("Role", {"name": f"{TAG} own payments", "data": {
        "Payment": {"create": "yes", "read": "own", "edit": "own", "delete": "own", "stream": "own"},
        "PaymentAllocation": {"read": "all"}, "Invoice": {"create": "yes", "read": "own", "edit": "own"},
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
    S["account2"] = create("Account", {"name": f"{TAG} other account"})["id"]
    S["contact"] = create("Contact", {"lastName": f"{TAG} contact", "accountId": S["account"]})["id"]
    S["vendor"] = create("Vendor", {"name": f"{TAG} vendor"})["id"]
    S["product"] = create("Product", {"name": f"{TAG} service"})["id"]


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


def invoice(total, client=None, **header):
    return create("Invoice", {"name": f"{TAG} invoice", "accountId": S["account"], **DATES, **header, "itemList": [
        {"productId": S["product"], "quantity": "1", "unitPrice": total}]}, client or c("dir"))


def sales_order(total):
    return create("SalesOrder", {"name": f"{TAG} order", "accountId": S["account"], "itemList": [
        {"productId": S["product"], "quantity": "1", "unitPrice": total}]}, c("dir"))


def row(document, amount, **extra):
    key = "salesOrderId" if document.get("number", "").startswith("ЗАКАЗ_") else "invoiceId"
    return {key: document["id"], "amount": amount, **extra}


def payment_data(amount, rows=None, user="dir", **fields):
    data = {"datePaid": "2026-10-02", "amount": amount, "assignedUserId": S["users"].get(user, S["adminId"]),
            "payerType": "Account", "payerId": S["account"], **fields}
    if rows is not None:
        data["allocationList"] = rows
    return data


def payment(amount, rows=None, user="dir", **fields):
    return create("Payment", payment_data(amount, rows, user, **fields), c(user))


def settlement(document):
    table = "sales_order" if document["number"].startswith("ЗАКАЗ_") else "invoice"
    return tuple(sql(f"SELECT paid_amount, balance_amount, settlement_state FROM {table} WHERE id='{document['id']}'")[0])


def allocation_rows(pid, deleted=False):
    """Every stored value of a payment's rows (rows are saved silently: modified_at would not show a rewrite)."""
    where = "" if deleted else " AND deleted=0"
    return sql("SELECT id, `order`, deleted, invoice_id, sales_order_id, amount, source, name, modified_at FROM "
               f"payment_allocation WHERE payment_id='{pid}'{where} ORDER BY `order`, id")


def notes(pid):
    return int(sql(f"SELECT COUNT(*) FROM note WHERE parent_type='Payment' AND parent_id='{pid}' AND deleted=0")[0][0])


def counter():
    return int(sql("SELECT value FROM next_number WHERE entity_type='Payment' AND field_name='number'")[0][0])


def counts():
    return (sql("SELECT COUNT(*) FROM payment")[0][0], sql("SELECT COUNT(*) FROM payment_allocation")[0][0],
            counter(), sql("SELECT COUNT(*) FROM note WHERE parent_type IN ('Payment','Invoice','SalesOrder')")[0][0])


def get(entity, rid, client="dir"):
    return must((S["admin"] if client == "admin" else c(client)).get(f"{entity}/{rid}"))


def import_save(entity, attributes, rid=None, op="save", imported=True, silent=True):
    """One ORM save (or removal) with SaveOption::IMPORT and SILENT, as the importer of stage 06.3 will do it (a removal
    without the options and with attributes set on the loaded copy stands for the core cascade with a stale snapshot)."""
    php = subprocess.run(["bash", "-c", f"source {REPO}/scripts/stand/lib.sh && echo $PHP_BIN"],
                         capture_output=True, text=True, check=True).stdout.strip()
    payload = json.dumps({"op": op, "entityType": entity, "id": rid, "attributes": attributes, "import": imported,
                          "silent": silent}, ensure_ascii=False)
    out = subprocess.run(["sudo", "-n", "-u", "espocrm", "env", f"ESPO_ROOT={REPO}", php, "--", payload],
                         input=FIXTURE.read_text(encoding="utf-8"), capture_output=True, text=True, check=True).stdout
    return json.loads(out.strip().splitlines()[-1])


def quote_sql(value):
    return "NULL" if value is None else "'" + str(value).replace("\\", "\\\\").replace("'", "''") + "'"


# ---------------------------------------------------------------------------------------------------- model
class ModelTest(unittest.TestCase):
    def test_columns_and_indexes(self):
        cols = {(t, c): ty for t, c, ty in sql(
            "SELECT table_name, column_name, column_type FROM information_schema.columns WHERE table_schema=DATABASE() "
            "AND ((table_name='payment' AND column_name IN ('amount','number','date_paid','vtiger_id')) "
            "OR (table_name='payment_allocation' AND column_name IN ('amount','removed_with')) "
            "OR (table_name IN ('invoice','sales_order') AND column_name IN ('paid_amount','balance_amount')))")}
        self.assertEqual(cols, {
            ("payment", "amount"): "decimal(25,8)", ("payment", "number"): "varchar(100)",
            ("payment", "date_paid"): "date", ("payment", "vtiger_id"): "int",
            ("payment_allocation", "amount"): "decimal(25,8)", ("payment_allocation", "removed_with"): "varchar(64)",
            ("invoice", "paid_amount"): "decimal(25,8)", ("invoice", "balance_amount"): "decimal(25,8)",
            ("sales_order", "paid_amount"): "decimal(25,8)", ("sales_order", "balance_amount"): "decimal(25,8)"})
        self.assertEqual(sql("SELECT non_unique FROM information_schema.statistics WHERE table_schema=DATABASE() "
                             "AND table_name='payment' AND column_name='vtiger_id'"), [["0"]])

    def test_metadata(self):
        meta = ok(self, S["admin"].get("Metadata"))
        fields = meta["entityDefs"]["Payment"]["fields"]
        self.assertEqual((fields["direction"]["options"], fields["direction"]["default"]), (["incoming", "outgoing"], "incoming"))
        self.assertEqual((fields["method"]["options"], fields["method"]["default"]), (["", "cash", "bank"], "bank"))
        self.assertEqual((fields["status"]["options"], fields["status"]["default"]),
                         (["", "Executed", "Запланирован", "Canceled", "Delayed"], "Executed"))
        self.assertTrue(all(fields[f].get("required") for f in ("datePaid", "direction", "amount")))
        self.assertEqual(fields["payer"]["entityList"], ["Account", "Contact", "Vendor"])
        self.assertTrue(all(fields[f].get("audited") for f in ("amount", "status", "direction", "datePaid", "payer",
                                                               "allocationList")))
        self.assertTrue(meta["scopes"]["Payment"]["stream"])
        self.assertFalse(meta["scopes"]["Invoice"]["stream"], "documents keep no stream; settlement goes to audit")
        for entity in ("Invoice", "SalesOrder"):
            defs = meta["entityDefs"][entity]
            self.assertIn("paymentAllocations", defs["links"])
            self.assertTrue(all(defs["fields"][f].get("audited") and defs["fields"][f].get("readOnly")
                                for f in ("paidAmount", "balanceAmount", "settlementState")), entity)
        registry = json.loads((REPO / "custom/Espo/Modules/Itvolga/Resources/metadata/app/itvolgaFinance.json")
                              .read_text(encoding="utf-8"))["payments"]["Payment"]
        self.assertEqual((registry["numberPrefix"], registry["firstNumber"]), ("", 991))
        self.assertGreaterEqual(counter(), 991)
        value_map = json.loads((REPO / "custom/Espo/Modules/Itvolga/Resources/metadata/vtigerValueMap/Payment.json")
                               .read_text(encoding="utf-8"))["fields"]
        self.assertEqual(value_map["direction"]["map"]["SPPayments.pay_type"], {"Приход": "incoming", "Expense": "outgoing"})
        self.assertEqual(value_map["method"]["map"]["SPPayments.type_payment"],
                         {"": "", "Наличные": "cash", "Cashless Transfer": "bank"})
        self.assertEqual(set(value_map["status"]["map"]["SPPayments.spstatus"].values()),
                         {"", "Executed", "Запланирован", "Canceled"})


# ---------------------------------------------------------------------------------------------------- allocation
class AllocationTest(unittest.TestCase):
    def test_partial_payment_and_number(self):
        inv = invoice("1000")
        number = counter()
        pay = payment("600", [row(inv, "600")])
        self.assertEqual((pay["number"], pay["name"]), (str(number), str(number)), "a counter without a prefix")
        self.assertEqual(counter(), number + 1)
        self.assertTrue(pay["legalEntityId"])
        self.assertEqual((pay["amountCurrency"], pay["allocatedAmount"], pay["unallocatedAmount"]),
                         ("RUB", "600.00000000", "0.00000000"))
        self.assertEqual(settlement(inv), ("600.00000000", "400.00000000", "partial"))
        stored = get("Invoice", inv["id"])
        self.assertEqual((stored["status"], stored["grandTotal"]), ("Created", "1000.00000000"),
                         "the status and the total of the document are not derived from payments (D-26)")
        self.assertEqual(allocation_rows(pay["id"])[0][6], "manual")

    def test_one_payment_several_documents_and_the_rest(self):
        inv, inv2, so = invoice("1000"), invoice("250.50"), sales_order("300")
        pay = payment("2000", [row(inv, "1000"), row(so, "100"), row(inv2, "250.50")])
        self.assertEqual((pay["allocatedAmount"], pay["unallocatedAmount"]), ("1350.50000000", "649.50000000"))
        self.assertEqual(settlement(inv), ("1000.00000000", "0.00000000", "paid"))
        self.assertEqual(settlement(so), ("100.00000000", "200.00000000", "partial"))
        self.assertEqual(settlement(inv2), ("250.50000000", "0.00000000", "paid"))
        self.assertEqual([r["documentNumber"] for r in pay["allocationList"]], [inv["number"], so["number"], inv2["number"]])

    def test_several_payments_and_overpayment(self):
        inv = invoice("1000")
        payment("400", [row(inv, "400")])
        payment("600", [row(inv, "600")], method="cash")
        self.assertEqual(settlement(inv), ("1000.00000000", "0.00000000", "paid"))
        payment("150", [row(inv, "150")])
        self.assertEqual(settlement(inv), ("1150.00000000", "-150.00000000", "overpaid"),
                         "overpaying is allowed and shown (D-49)")

    def test_statuses_that_count(self):
        inv = invoice("1000")
        pay = payment("1000", [row(inv, "1000")])
        expected = {"Canceled": "unpaid", "": "paid", "Запланирован": "unpaid", "Delayed": "unpaid", "Executed": "paid"}
        for status, state in expected.items():
            ok(self, c("dir").put(f"Payment/{pay['id']}", {"status": status}))
            self.assertEqual(settlement(inv)[2], state, f"status {status!r}")
        self.assertEqual(len(allocation_rows(pay["id"])), 1, "allocations of any status are kept")
        planned = payment("200", [row(invoice("200"), "200")], status="Запланирован")
        self.assertEqual(planned["allocatedAmount"], "200.00000000", "a planned payment may be allocated")

    def test_payer_of_every_type_and_none(self):
        for payer_type, payer_id in (("Contact", S["contact"]), ("Vendor", S["vendor"]), ("Account", S["account2"])):
            pay = payment("10", payerType=payer_type, payerId=payer_id)
            self.assertEqual((pay["payerType"], pay["payerId"]), (payer_type, payer_id))
        pay = payment("10", payerType=None, payerId=None)
        self.assertIsNone(pay["payerId"])
        # The payer and the account of the invoice may differ (36 such payments in Vtiger).
        inv = invoice("10")
        self.assertEqual(payment("10", [row(inv, "10")], payerType="Account", payerId=S["account2"])["allocatedAmount"],
                         "10.00000000")
        self.assertEqual(c("dir").put(f"Payment/{pay['id']}", {"payerType": "Lead", "payerId": S["account"]})[0], 400)


# ---------------------------------------------------------------------------------------------------- edits
class EditTest(unittest.TestCase):
    def setUp(self):
        self.inv, self.inv2 = invoice("1000"), invoice("500")
        self.pay = payment("1000", [row(self.inv, "600")])
        self.rid = self.pay["allocationList"][0]["id"]

    def test_repeated_save_changes_nothing(self):
        before, notes_before = allocation_rows(self.pay["id"]), notes(self.pay["id"])
        for table in ([{"id": self.rid, "invoiceId": self.inv["id"], "amount": "600.00000000"}],
                      [row(self.inv, "600")],
                      self.pay["allocationList"]):
            ok(self, c("dir").put(f"Payment/{self.pay['id']}", {"allocationList": table}))
            self.assertEqual(allocation_rows(self.pay["id"]), before, "rows unchanged")
        self.assertEqual(notes(self.pay["id"]), notes_before, "no history for a save that changes nothing")

    def test_same_document_twice_is_refused(self):
        before = (allocation_rows(self.pay["id"]), counts(), settlement(self.inv))
        result = c("dir").put(f"Payment/{self.pay['id']}", {"allocationList": [
            {"id": self.rid, "invoiceId": self.inv["id"], "amount": "600"}, row(self.inv, "100")]})
        self.assertEqual((result[0], label(result)), (400, "financeAllocationDuplicateTarget"))
        self.assertEqual((allocation_rows(self.pay["id"]), counts(), settlement(self.inv)), before)
        new = c("dir").post("Payment", payment_data("300", [row(self.inv, "100"), row(self.inv, "200")]))
        self.assertEqual(label(new), "financeAllocationDuplicateTarget")

    def test_move_edit_and_cancel(self):
        moved = ok(self, c("dir").put(f"Payment/{self.pay['id']}", {"allocationList": [
            {"id": self.rid, "invoiceId": self.inv2["id"], "amount": "500"}]}))
        self.assertEqual(moved["allocationList"][0]["id"], self.rid, "the row is kept, its document changes")
        self.assertEqual(settlement(self.inv), ("0.00000000", "1000.00000000", "unpaid"))
        self.assertEqual(settlement(self.inv2), ("500.00000000", "0.00000000", "paid"))
        edited = ok(self, c("dir").put(f"Payment/{self.pay['id']}", {"allocationList": [
            {"id": self.rid, "invoiceId": self.inv2["id"], "amount": "200.10"}, row(self.inv, "799.90")]}))
        self.assertEqual(edited["unallocatedAmount"], "0.00000000")
        self.assertEqual(settlement(self.inv2)[2], "partial")
        cancelled = ok(self, c("dir").put(f"Payment/{self.pay['id']}", {"allocationList": [row(self.inv, "799.90")]}))
        self.assertEqual(cancelled["unallocatedAmount"], "200.10000000", "the cancelled share returns to the payment")
        self.assertEqual(settlement(self.inv2), ("0.00000000", "500.00000000", "unpaid"))
        gone = allocation_rows(self.pay["id"], deleted=True)
        self.assertEqual([r[2] for r in gone if r[0] == self.rid], ["1"], "a cancelled allocation is removed")

    def test_sum_control_and_outgoing(self):
        before = (allocation_rows(self.pay["id"]), counts())
        cases = [
            ({"allocationList": [row(self.inv, "600"), row(self.inv2, "400.01")]}, "financeOverAllocation"),
            ({"amount": "599.99"}, "financeAmountBelowAllocated"),
            ({"direction": "outgoing"}, "financeOutgoingAllocation"),
        ]
        for data, expected in cases:
            result = c("dir").put(f"Payment/{self.pay['id']}", data)
            self.assertEqual((result[0], label(result)), (400, expected), data)
            self.assertNotIn("599", json.dumps(result[1]), "no amount in the refusal")
        self.assertEqual((allocation_rows(self.pay["id"]), counts()), before)
        # Switching to outgoing together with clearing the table is allowed; an outgoing payment has no rows.
        out = ok(self, c("dir").put(f"Payment/{self.pay['id']}", {"direction": "outgoing", "allocationList": []}))
        self.assertEqual((out["direction"], out["allocationList"]), ("outgoing", []))
        self.assertEqual(settlement(self.inv)[2], "unpaid")
        self.assertEqual(label(c("dir").post("Payment", payment_data("5", [row(self.inv, "5")], direction="outgoing"))),
                         "financeOutgoingAllocation")

    def test_document_total_follows(self):
        items = get("Invoice", self.inv["id"])["itemList"]
        ok(self, c("dir").put(f"Invoice/{self.inv['id']}", {"itemList": [
            {"id": items[0]["id"], "productId": S["product"], "quantity": "1", "unitPrice": "600"}]}))
        self.assertEqual(settlement(self.inv), ("600.00000000", "0.00000000", "paid"), "the paid sum stays")
        ok(self, c("dir").put(f"Invoice/{self.inv['id']}", {"adjustment": "-100"}))
        self.assertEqual(settlement(self.inv), ("600.00000000", "-100.00000000", "overpaid"))


# ---------------------------------------------------------------------------------------------------- refusals
class RefusalTest(unittest.TestCase):
    def test_refusals_change_nothing(self):
        inv, small = invoice("1000"), invoice("77")
        before = (counts(), settlement(inv))
        cases = [
            (payment_data(777.5), "financeFloat"),
            (payment_data("777", [{"invoiceId": inv["id"], "amount": 777.5}]), "financeFloat"),
            (payment_data("777", [row(inv, "777,5")]), "financeNotDecimal"),
            (payment_data("777.005"), "financeTooManyDecimals"),
            (payment_data("777", [row(inv, "7.775")]), "financeTooManyDecimals"),
            # The core min:0 check answers first; the finance rule refuses it on every other path (ORM, import).
            (payment_data("-777"), "validationFailure"),
            (payment_data("777", [row(inv, "0")]), "financeAllocationNotPositive"),
            (payment_data("777", [{"amount": "1"}]), "financeAllocationTargetRequired"),
            (payment_data("777", [{"invoiceId": inv["id"], "salesOrderId": inv["id"], "amount": "1"}]),
             "financeAllocationTargetExclusive"),
            (payment_data("777", [{"invoiceId": "no-such-invoice", "amount": "1"}]), "financeAllocationUnknownTarget"),
            (payment_data("777", [row(inv, "700"), row(small, "77.01")]), "financeOverAllocation"),
            (payment_data("777", [row(inv, "777")], direction="outgoing"), "financeOutgoingAllocation"),
        ]
        for data, expected in cases:
            result = c("dir").post("Payment", data)
            self.assertEqual((result[0], label(result)), (400, expected), json.dumps(data, ensure_ascii=False))
            self.assertNotIn("777", json.dumps(result[1], ensure_ascii=False), f"{expected}: no value in the refusal")
        self.assertEqual((counts(), settlement(inv)), before, "nothing written, no number taken")
        pay = payment("10")
        foreign = c("dir").put(f"Payment/{pay['id']}", {"allocationList": [{"id": "not-a-row", "invoiceId": inv["id"],
                                                                             "amount": "1"}]})
        self.assertEqual(label(foreign), "financeUnknownAllocation")
        # A paid sum that does not fit DECIMAL(25,8) is refused, not clamped by the non-strict MySQL.
        huge = invoice("1")
        payment("50000000000000000.00", [row(huge, "50000000000000000.00")])
        before = (counts(), settlement(huge))
        over = c("dir").post("Payment", payment_data("50000000000000000.00", [row(huge, "50000000000000000.00")]))
        if over[0] == 200:
            S["created"].append(("Payment", over[1]["id"]))
        self.assertEqual((over[0], label(over)), (400, "financeSettlementTooLarge"))
        self.assertEqual((counts(), settlement(huge)), before)


# ---------------------------------------------------------------------------------------------------- history
class HistoryTest(unittest.TestCase):
    def test_payment_stream_and_document_audit(self):
        inv, inv2 = invoice("1000"), invoice("300")
        pay = payment("1000", [row(inv, "1000")])
        stream = ok(self, c("dir").get(f"Payment/{pay['id']}/stream"))["list"]
        self.assertEqual([n["type"] for n in stream], ["Update", "Create"], "creation and its rows")
        self.assertEqual([r["invoiceId"] for r in stream[0]["data"]["attributes"]["became"]["allocationList"]], [inv["id"]])
        rid = pay["allocationList"][0]["id"]
        ok(self, c("dir").put(f"Payment/{pay['id']}", {"status": "Canceled", "allocationList": [
            {"id": rid, "invoiceId": inv2["id"], "amount": "300"}]}))
        note = ok(self, c("dir").get(f"Payment/{pay['id']}/stream"))["list"][0]
        self.assertEqual((note["type"], set(note["data"]["fields"])), ("Update", {"status", "allocationList"}))
        attributes = note["data"]["attributes"]
        self.assertEqual(attributes["was"]["allocationList"][0]["invoiceId"], inv["id"])
        self.assertEqual(attributes["became"]["allocationList"][0]["invoiceId"], inv2["id"])
        self.assertEqual(note["createdById"], S["users"]["dir"])
        audit = ok(self, c("dir").get(f"Invoice/{inv['id']}/updateStream"))["list"]
        self.assertTrue(audit and set(audit[0]["data"]["fields"]) >= {"paidAmount", "balanceAmount", "settlementState"})
        self.assertEqual(audit[0]["createdById"], S["users"]["dir"])
        self.assertEqual(c("dep").get(f"Payment/{pay['id']}/stream")[0], 403)


# ---------------------------------------------------------------------------------------------------- removal
class RemovalTest(unittest.TestCase):
    def test_remove_payment(self):
        inv = invoice("1000")
        pay = must(c("dir").post("Payment", payment_data("700", [row(inv, "700")])))
        self.assertEqual(c("dir").delete(f"Payment/{pay['id']}")[0], 200)
        self.assertEqual(settlement(inv), ("0.00000000", "1000.00000000", "unpaid"))
        self.assertEqual([r[2] for r in allocation_rows(pay["id"], deleted=True)], ["1"])
        # The rows carry the payment they were removed with, so its restore is refused whatever the clock: the core
        # picks the rows to restore by modifiedAt, which it sets on the payment after the hooks that removed the rows.
        self.assertEqual(sql(f"SELECT removed_with FROM payment_allocation WHERE payment_id='{pay['id']}'"),
                         [[f"Payment:{pay['id']}"]])
        sql(f"UPDATE payment_allocation SET modified_at = modified_at - INTERVAL 5 SECOND WHERE payment_id='{pay['id']}'")
        restore = S["admin"].request("POST", "Payment/action/restoreDeleted", {"id": pay["id"]})
        self.assertEqual((restore[0], label(restore)), (409, "financeRestoreDenied"))
        self.assertEqual(sql(f"SELECT deleted FROM payment WHERE id='{pay['id']}'"), [["1"]], "nothing restored")
        # A row cancelled by an earlier save of the table does not hold the restore of its payment.
        kept = payment("50", [row(inv, "50")])
        ok(self, c("dir").put(f"Payment/{kept['id']}", {"allocationList": []}))
        sql(f"UPDATE payment_allocation SET modified_at = modified_at - INTERVAL 1 MINUTE WHERE payment_id='{kept['id']}'")
        self.assertEqual(c("dir").delete(f"Payment/{kept['id']}")[0], 200)
        self.assertEqual(S["admin"].request("POST", "Payment/action/restoreDeleted", {"id": kept["id"]})[0], 200)
        self.assertEqual((get("Payment", kept["id"])["allocationList"], settlement(inv)[2]), ([], "unpaid"))

    def test_remove_document_and_no_restore(self):
        inv = must(c("dir").post("Invoice", {"name": f"{TAG} removed", "accountId": S["account"], **DATES,
                                             "itemList": [{"productId": S["product"], "quantity": "1", "unitPrice": "100"}]}))
        inv2 = invoice("50")
        pay = payment("200", [row(inv, "100"), row(inv2, "50")])
        notes_before = notes(pay["id"])
        self.assertEqual(c("dir").delete(f"Invoice/{inv['id']}")[0], 200)
        got = get("Payment", pay["id"])
        self.assertEqual(([r["invoiceId"] for r in got["allocationList"]], got["unallocatedAmount"]),
                         ([inv2["id"]], "150.00000000"))
        self.assertEqual(settlement(inv2), ("50.00000000", "0.00000000", "paid"), "other documents are untouched")
        self.assertEqual(notes(pay["id"]), notes_before + 1)
        note = ok(self, c("dir").get(f"Payment/{pay['id']}/stream"))["list"][0]
        self.assertEqual(([r["invoiceId"] for r in note["data"]["attributes"]["was"]["allocationList"]],
                          note["data"]["attributes"]["became"]["allocationList"][0]["invoiceId"]),
                         ([inv["id"], inv2["id"]], inv2["id"]))
        # As for a payment: refused by the mark, also when the rows look older than the document's removal.
        self.assertEqual(sql(f"SELECT removed_with FROM payment_allocation WHERE invoice_id='{inv['id']}'"),
                         [[f"Invoice:{inv['id']}"]])
        sql(f"UPDATE payment_allocation SET modified_at = modified_at - INTERVAL 5 SECOND WHERE invoice_id='{inv['id']}'")
        restore = S["admin"].request("POST", "Invoice/action/restoreDeleted", {"id": inv["id"]})
        self.assertEqual((restore[0], label(restore)), (409, "financeRestoreDenied"))
        self.assertEqual(sql(f"SELECT deleted FROM invoice WHERE id='{inv['id']}'"), [["1"]], "nothing restored")
        # A document removed without allocations restores as before.
        plain = must(c("dir").post("Invoice", {"name": f"{TAG} plain", "accountId": S["account"], **DATES,
                                               "itemList": [{"productId": S["product"], "quantity": "1", "unitPrice": "1"}]}))
        self.assertEqual(c("dir").delete(f"Invoice/{plain['id']}")[0], 200)
        self.assertEqual(S["admin"].request("POST", "Invoice/action/restoreDeleted", {"id": plain["id"]})[0], 200)
        S["created"].append(("Invoice", plain["id"]))


# ---------------------------------------------------------------------------------------------------- concurrency
class ConcurrencyTest(unittest.TestCase):
    def hold(self, lock_sql, then_sql, call):
        """Another MySQL session holds a lock while `call` runs in a thread; then it runs `then_sql` and commits."""
        holder = subprocess.Popen(["sudo", "-n", "mysql", f"--socket={MYSQL_SOCKET}", "-N", "-B", "--unbuffered", DB_NAME],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        result = {}
        try:
            holder.stdin.write(f"START TRANSACTION; {lock_sql};\n")
            holder.stdin.flush()
            ready, _, _ = select.select([holder.stdout], [], [], 15)
            self.assertTrue(ready and holder.stdout.readline().strip(), "the locking session holds the row")
            worker = threading.Thread(target=lambda: result.update(r=call()))
            worker.start()
            worker.join(3)
            self.assertTrue(worker.is_alive(), "the save waits for the lock")
            holder.stdin.write(f"{then_sql}; COMMIT;\n")
            holder.stdin.close()
            holder.wait(15)
            worker.join(30)
        finally:
            if holder.poll() is None:
                holder.kill()
                holder.wait(5)
            for stream in (holder.stdin, holder.stdout, holder.stderr):
                stream.close()
        saved = ok(self, result["r"])
        S["created"].append(("Payment", saved["id"]))
        return saved

    def test_settlement_reads_what_was_committed(self):
        """A payment save that waited for the ledger settles the invoice with an allocation another transaction
        committed meanwhile (a locking read: never the transaction's older snapshot)."""
        inv = invoice("1000")
        other = payment("300")
        rid = secrets.token_hex(8)
        self.hold("SELECT entity_type FROM next_number WHERE entity_type='Payment' AND field_name='number' FOR UPDATE",
                  "INSERT INTO payment_allocation (id, deleted, name, amount, amount_currency, `order`, source, "
                  f"source_conflict, payment_id, invoice_id) VALUES ('{rid}', 0, 'x', 300, 'RUB', 1, 'manual', 0, "
                  f"'{other['id']}', '{inv['id']}')",
                  lambda: c("dir").post("Payment", payment_data("200", [row(inv, "200")])))
        self.assertEqual(settlement(inv), ("500.00000000", "500.00000000", "partial"))

    def test_removed_payment_takes_rows_committed_meanwhile(self):
        """A payment removal that waited for the ledger removes a row another transaction committed meanwhile (a locking
        read, not the core cascade's snapshot), and the invoice is settled without it."""
        inv = invoice("1000")
        pay = payment("500", [row(inv, "100")])
        rid = secrets.token_hex(8)
        result = self.hold_raw(
            "SELECT entity_type FROM next_number WHERE entity_type='Payment' AND field_name='number' FOR UPDATE",
            "INSERT INTO payment_allocation (id, deleted, name, amount, amount_currency, `order`, source, source_conflict, "
            f"payment_id, invoice_id) VALUES ('{rid}', 0, 'x', 300, 'RUB', 2, 'manual', 0, '{pay['id']}', '{invoice('50')['id']}')",
            lambda: c("dir").delete(f"Payment/{pay['id']}"))
        self.assertEqual(result[0], 200)
        self.assertEqual(sql(f"SELECT COUNT(*) FROM payment_allocation WHERE payment_id='{pay['id']}' AND deleted=0"), [["0"]])
        self.assertEqual(settlement(inv)[2], "unpaid")

    def test_removed_document_takes_rows_committed_meanwhile(self):
        inv = must(c("dir").post("Invoice", {"name": f"{TAG} removed", "accountId": S["account"], **DATES,
                                             "itemList": [{"productId": S["product"], "quantity": "1", "unitPrice": "100"}]}))
        pay = payment("100")
        rid = secrets.token_hex(8)
        result = self.hold_raw(
            "SELECT entity_type FROM next_number WHERE entity_type='Payment' AND field_name='number' FOR UPDATE",
            "INSERT INTO payment_allocation (id, deleted, name, amount, amount_currency, `order`, source, source_conflict, "
            f"payment_id, invoice_id) VALUES ('{rid}', 0, 'x', 100, 'RUB', 1, 'manual', 0, '{pay['id']}', '{inv['id']}')",
            lambda: c("dir").delete(f"Invoice/{inv['id']}"))
        self.assertEqual(result[0], 200)
        self.assertEqual(sql(f"SELECT deleted FROM payment_allocation WHERE id='{rid}'"), [["1"]])
        self.assertEqual(get("Payment", pay["id"])["unallocatedAmount"], "100.00000000")
        note = ok(self, c("dir").get(f"Payment/{pay['id']}/stream"))["list"][0]
        self.assertEqual([r["invoiceId"] for r in note["data"]["attributes"]["was"]["allocationList"]], [inv["id"]])

    def test_document_removal_never_takes_a_row_moved_meanwhile(self):
        """While an invoice removal waits for the ledger, another save moves its row to another invoice: the moved
        row is never removed with the old invoice. Whether the core cascade still sees the row depends on when the
        transaction's snapshot was taken: either it does not (the removal succeeds) or the guard judges the row by its
        current locked state and the removal fails as a conflict (409, nothing changes)."""
        a, b = invoice("1000"), invoice("1000")
        pay = payment("100", [row(a, "100")])
        rid = pay["allocationList"][0]["id"]
        result = self.hold_raw(
            "SELECT entity_type FROM next_number WHERE entity_type='Payment' AND field_name='number' FOR UPDATE",
            f"UPDATE payment_allocation SET invoice_id='{b['id']}' WHERE id='{rid}'",
            lambda: c("dir").delete(f"Invoice/{a['id']}"))
        self.assertIn(result[0], (200, 409))
        if result[0] == 409:
            self.assertEqual(label(result), "financeAllocationChanged")
        self.assertEqual(sql(f"SELECT deleted FROM invoice WHERE id='{a['id']}'"), [["1" if result[0] == 200 else "0"]])
        self.assertEqual(sql(f"SELECT invoice_id, deleted FROM payment_allocation WHERE id='{rid}'"), [[b["id"], "0"]],
                         "the moved row stays on the other invoice")

    def test_cascade_judges_a_row_by_its_current_state(self):
        """The guard of the core cascade: a stale copy of a row (its old invoice is gone) whose current row was moved
        to a live invoice is refused as a conflict; a row whose current owner is gone is removed; a direct removal
        with live owners is forbidden."""
        gone, live = invoice("10"), invoice("10")
        pay = payment("10", [row(live, "10")])
        rid = pay["allocationList"][0]["id"]
        self.assertEqual(c("dir").delete(f"Invoice/{gone['id']}")[0], 200)
        stale = import_save("PaymentAllocation", {"invoiceId": gone["id"]}, rid, op="remove", imported=False)
        self.assertEqual((stale["ok"], stale["error"]), (False, "Espo\\Core\\Exceptions\\Conflict"))
        direct = import_save("PaymentAllocation", {}, rid, op="remove", imported=False)
        self.assertEqual((direct["ok"], direct["error"]), (False, "Espo\\Core\\Exceptions\\Forbidden"))
        self.assertEqual(sql(f"SELECT invoice_id, deleted FROM payment_allocation WHERE id='{rid}'"), [[live["id"], "0"]])

    def test_document_removal_records_a_payment_committed_meanwhile(self):
        """A payment and its row committed while an invoice removal waits: the row is removed and recorded in that
        payment's history (a locking read of the payment, not the older snapshot)."""
        inv = must(c("dir").post("Invoice", {"name": f"{TAG} removed", "accountId": S["account"], **DATES,
                                             "itemList": [{"productId": S["product"], "quantity": "1", "unitPrice": "100"}]}))
        pid, rid = secrets.token_hex(8), secrets.token_hex(8)
        S["created"].append(("Payment", pid))
        result = self.hold_raw(
            "SELECT entity_type FROM next_number WHERE entity_type='Payment' AND field_name='number' FOR UPDATE",
            "INSERT INTO payment (id, deleted, name, number, amount, amount_currency, date_paid, direction, status, "
            f"is_foreign_currency_account, assigned_user_id) VALUES ('{pid}', 0, '{TAG}', '{TAG}', 100, 'RUB', "
            f"'2026-10-02', 'incoming', 'Executed', 0, '{S['users']['dir']}'); "
            "INSERT INTO payment_allocation (id, deleted, name, amount, amount_currency, `order`, source, source_conflict, "
            f"payment_id, invoice_id) VALUES ('{rid}', 0, 'x', 100, 'RUB', 1, 'manual', 0, '{pid}', '{inv['id']}')",
            lambda: c("dir").delete(f"Invoice/{inv['id']}"))
        self.assertEqual(result[0], 200)
        self.assertEqual(sql(f"SELECT deleted FROM payment_allocation WHERE id='{rid}'"), [["1"]])
        self.assertEqual(notes(pid), 1, "the removal is in the payment's history")

    def test_reimported_total_keeps_the_committed_paid_sum(self):
        """The importer re-saves an invoice with another total while a payment changes its paid sum: the balance is
        derived from the locked row, not from the copy the importer loaded."""
        inv = invoice("1000")
        payment("100", [row(inv, "100")])
        self.hold_raw(f"SELECT id FROM invoice WHERE id='{inv['id']}' FOR UPDATE",
                      f"UPDATE invoice SET paid_amount=300, balance_amount=700, settlement_state='partial' "
                      f"WHERE id='{inv['id']}'",
                      lambda: import_save("Invoice", {"grandTotal": "600.00", "subtotal": "600.00",
                                                      "preTaxTotal": "600.00"}, inv["id"]))
        self.assertEqual(settlement(inv), ("300.00000000", "300.00000000", "partial"))

    def test_imported_row_is_rebased_on_the_locked_row(self):
        """The importer changes the amount of a row that another save moved to another invoice meanwhile: the row
        stays on the new invoice with the new amount and both invoices are settled."""
        a, b = invoice("1000"), invoice("1000")
        pay = payment("500", [row(a, "100")])
        rid = pay["allocationList"][0]["id"]
        result = self.hold_raw(
            "SELECT entity_type FROM next_number WHERE entity_type='Payment' AND field_name='number' FOR UPDATE",
            f"UPDATE payment_allocation SET invoice_id='{b['id']}' WHERE id='{rid}'",
            lambda: import_save("PaymentAllocation", {"amount": "200"}, rid))
        self.assertTrue(result["ok"], result)
        self.assertEqual(sql(f"SELECT invoice_id, amount, name FROM payment_allocation WHERE id='{rid}'"),
                         [[b["id"], "200.00000000", f"{pay['number']} → {b['number']}"]], "checked as the row on B")
        self.assertEqual((settlement(a)[2], settlement(b)[0]), ("unpaid", "200.00000000"))

    def hold_raw(self, lock_sql, then_sql, call):
        """As hold(), returning the raw result of `call` (removals, the import fixture)."""
        holder = subprocess.Popen(["sudo", "-n", "mysql", f"--socket={MYSQL_SOCKET}", "-N", "-B", "--unbuffered", DB_NAME],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        result = {}
        try:
            holder.stdin.write(f"START TRANSACTION; {lock_sql};\n")
            holder.stdin.flush()
            ready, _, _ = select.select([holder.stdout], [], [], 15)
            self.assertTrue(ready and holder.stdout.readline().strip(), "the locking session holds the row")
            worker = threading.Thread(target=lambda: result.update(r=call()))
            worker.start()
            worker.join(3)
            self.assertTrue(worker.is_alive(), "the write waits for the lock")
            holder.stdin.write(f"{then_sql}; COMMIT;\n")
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

    def test_settlement_uses_the_committed_total(self):
        inv = invoice("1000")
        self.hold(f"SELECT id FROM invoice WHERE id='{inv['id']}' FOR UPDATE",
                  f"UPDATE invoice SET grand_total=400 WHERE id='{inv['id']}'",
                  lambda: c("dir").post("Payment", payment_data("500", [row(inv, "500")])))
        self.assertEqual(settlement(inv), ("500.00000000", "-100.00000000", "overpaid"))


# ---------------------------------------------------------------------------------------------------- access
class AccessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inv = invoice("100")
        cls.pay = payment("100", [row(cls.inv, "100")])
        cls.rid = cls.pay["allocationList"][0]["id"]

    def test_only_the_director_sees_payments(self):
        for user in ("dep", "sales", "cust", "norole"):
            for scope in ("Payment", "PaymentAllocation"):
                self.assertEqual(c(user).get(scope)[0], 403, f"{user} list {scope}")
            self.assertEqual(c(user).get(f"Payment/{self.pay['id']}")[0], 403, user)
            self.assertEqual(c(user).post("Payment", payment_data("1"))[0], 403, user)
            self.assertEqual(c(user).request("POST", "FinanceDocument/Payment/calculate",
                                             {"attributes": {"amount": "1"}})[0], 403, user)
            self.assertEqual(c(user).get(f"FinanceDocument/Invoice/{self.inv['id']}/convertTo/Payment")[0], 403, user)
        self.assertEqual(c("dir").get(f"PaymentAllocation/{self.rid}")[0], 200)
        tabs = ok(self, S["admin"].get("Settings"))["tabList"]
        self.assertEqual(tabs[tabs.index("Invoice") + 1], "Payment", "the Payments tab follows the Invoices tab")

    def test_rows_are_never_written_directly(self):
        before = allocation_rows(self.pay["id"])
        for client in (S["admin"], c("dir")):
            self.assertEqual(client.post("PaymentAllocation", {"paymentId": self.pay["id"], "invoiceId": self.inv["id"],
                                                               "amount": "1"})[0], 403)
            self.assertEqual(client.put(f"PaymentAllocation/{self.rid}", {"amount": "5"})[0], 403)
            self.assertEqual(client.delete(f"PaymentAllocation/{self.rid}")[0], 403)
            for link_path in (f"Invoice/{self.inv['id']}/paymentAllocations", f"Payment/{self.pay['id']}/paymentAllocations"):
                self.assertEqual(client.request("POST", link_path, {"id": self.rid})[0], 403, link_path)
                self.assertEqual(client.request("DELETE", link_path, {"id": self.rid})[0], 403, link_path)
            self.assertEqual(client.request("POST", f"Account/{S['account2']}/cPayments", {"id": self.pay["id"]})[0], 403)
            self.assertIn(client.post("MassAction", {"entityType": "PaymentAllocation", "action": "update",
                                                     "params": {"ids": [self.rid]}, "data": {"amount": "9"}})[0],
                          (400, 403))
        self.assertEqual(allocation_rows(self.pay["id"]), before)
        # Settlement fields of a document are not writable through the API.
        ok(self, c("dir").put(f"Invoice/{self.inv['id']}", {"paidAmount": "1", "settlementState": "unpaid"}))
        self.assertEqual(settlement(self.inv), ("100.00000000", "0.00000000", "paid"))

    def test_rows_follow_their_payment(self):
        mine = invoice("40", client=c("own"))
        own = payment("50", [row(mine, "40")], user="own")
        listed = {r["id"] for r in ok(self, c("own").get("PaymentAllocation", maxSize=200))["list"]}
        self.assertEqual(listed, {own["allocationList"][0]["id"]}, "only the rows of the user's own payments")
        self.assertEqual(c("own").get(f"PaymentAllocation/{self.rid}")[0], 403)
        # A document the user may not read is refused like a missing one.
        refused = c("own").put(f"Payment/{own['id']}", {"allocationList": [row(mine, "40"), row(self.inv, "10")]})
        self.assertEqual(label(refused), "financeAllocationUnknownTarget")
        # A row to such a document (given by the director) keeps it: neither its amount nor its removal is allowed.
        theirs, mine2 = invoice("30"), invoice("10", client=c("own"))
        table = ok(self, c("dir").put(f"Payment/{own['id']}", {"allocationList": [
            row(mine, "40", id=own["allocationList"][0]["id"]), row(theirs, "10")]}))["allocationList"]
        before = (allocation_rows(own["id"]), settlement(theirs))
        kept, other = ({"id": r["id"], "invoiceId": r["invoiceId"], "amount": r["amount"]} for r in table)
        for rows in ([kept, {**other, "amount": "5"}], [kept], [kept, {**other, "invoiceId": mine2["id"]}]):
            refused = c("own").put(f"Payment/{own['id']}", {"allocationList": rows})
            self.assertEqual((refused[0], label(refused)), (400, "financeAllocationUnknownTarget"), rows)
        self.assertEqual((allocation_rows(own["id"]), settlement(theirs)), before)
        ok(self, c("own").put(f"Payment/{own['id']}", {"allocationList": [other, kept]}))
        self.assertEqual(settlement(theirs), before[1], "renumbering changes no document")

    def test_no_csv_import_of_finance_records(self):
        # A real CSV upload: the core reads the file before it creates the import record that the guard refuses.
        attachment = ok(self, c("dir").request("POST", "Import/file", "synthetic description\n"))["attachmentId"]
        for entity in ("Payment", "Invoice"):
            result = c("dir").request("POST", "Import", {"entityType": entity, "attributeList": ["description"],
                                                          "attachmentId": attachment, "delimiter": ",",
                                                          "textQualifier": "\"", "headerRow": False})
            self.assertEqual(result[0], 403, entity)
        self.assertEqual(int(sql("SELECT COUNT(*) FROM import WHERE entity_type IN ('Payment','Invoice') "
                                 "AND deleted=0")[0][0]), 0)


# ---------------------------------------------------------------------------------------------------- prefill
class PrefillTest(unittest.TestCase):
    def test_add_payment_from_a_document(self):
        before = counts()
        inv, so = invoice("1234.5"), sales_order("80")
        before = counts()
        for document in (inv, so):
            entity = "SalesOrder" if document is so else "Invoice"
            attributes = ok(self, c("dir").get(f"FinanceDocument/{entity}/{document['id']}/convertTo/Payment"))
            self.assertEqual((attributes["payerType"], attributes["payerId"]), ("Account", S["account"]))
            self.assertEqual(attributes["amount"], {"Invoice": "1234.50", "SalesOrder": "80.00"}[entity])
            [line] = attributes["allocationList"]
            self.assertEqual((line["id"], line[{"Invoice": "invoiceId", "SalesOrder": "salesOrderId"}[entity]],
                              line["amount"]), (None, document["id"], attributes["amount"]))
            saved = create("Payment", {**attributes, "datePaid": "2026-10-02", "assignedUserId": S["users"]["dir"]}, c("dir"))
            self.assertEqual(settlement(document)[2], "paid")
            self.assertEqual(saved["allocationList"][0]["amount"], attributes["amount"])
        self.assertEqual(counts()[2], before[2] + 2, "numbers are taken by the saves only")
        free = invoice("0")
        self.assertEqual(ok(self, c("dir").get(f"FinanceDocument/Invoice/{free['id']}/convertTo/Payment"))["allocationList"], [])


# ---------------------------------------------------------------------------------------------------- import path
class ImportPathTest(unittest.TestCase):
    def test_imported_allocations_and_settle(self):
        inv, inv2 = invoice("1000"), invoice("100")
        vt = VT_BASE + secrets.randbelow(10_000_000)
        pay = import_save("Payment", {"vtigerId": vt, "number": str(vt), "datePaid": "2018-05-01", "direction": "incoming",
                                      "status": "", "amount": "1000.00000000", "assignedUserId": S["users"]["dir"],
                                      "vtigerData": {"spcompany": "По умолчанию", "related_to": vt}})
        self.assertTrue(pay["ok"], pay)
        S["created"].append(("Payment", pay["id"]))
        quiet = f"SELECT COUNT(*) FROM note WHERE parent_id IN ('{pay['id']}','{inv['id']}') AND deleted=0"
        self.assertEqual(sql(quiet), [["0"]], "an import writes no stream or audit notes")
        self.assertEqual(sql(f"SELECT COUNT(*) FROM notification WHERE related_id='{pay['id']}'"), [["0"]],
                         "nor assignment notifications")
        stored = sql(f"SELECT number, status, legal_entity_id IS NOT NULL FROM payment WHERE id='{pay['id']}'")
        self.assertEqual(stored, [[str(vt), "", "1"]], "the source number and the empty status are kept")
        alloc = import_save("PaymentAllocation", {"paymentId": pay["id"], "invoiceId": inv["id"], "amount": "1000",
                                                  "source": "relatedTo", "sourceConflict": True})
        self.assertTrue(alloc["ok"], alloc)
        self.assertEqual(settlement(inv), ("1000.00000000", "0.00000000", "paid"), "empty status counts (Q-37)")
        self.assertEqual(sql(quiet), [["0"]], "an imported row settles its document silently")
        refused = [
            ({"paymentId": pay["id"], "invoiceId": inv2["id"], "amount": "0.01"}, "exceed"),
            ({"paymentId": pay["id"], "invoiceId": inv["id"], "amount": "1"}, "already has a row"),
            ({"paymentId": pay["id"], "amount": "1"}, "rejected allocation"),
        ]
        for attributes, reason in refused:
            result = import_save("PaymentAllocation", attributes)
            self.assertFalse(result["ok"], attributes)
            self.assertIn(reason, result["message"])
            self.assertNotIn("1000", result["message"], "no value in the message")
        unknown = import_save("Payment", {"vtigerId": vt + 1, "number": str(vt + 1), "datePaid": "2018-05-01",
                                          "direction": "incoming", "amount": "5", "assignedUserId": S["users"]["dir"],
                                          "vtigerData": {"spcompany": "Other company"}})
        self.assertFalse(unknown["ok"])
        self.assertNotIn("Other company", unknown["message"])
        self.assertEqual(sql(f"SELECT COUNT(*) FROM payment WHERE vtiger_id={vt + 1}"), [["0"]])
        # An import write without SaveOption::SILENT would fill the stream, the audit and the notifications: refused.
        loud = import_save("Payment", {"vtigerId": vt + 2, "number": str(vt + 2), "datePaid": "2018-05-01",
                                       "direction": "incoming", "amount": "5", "assignedUserId": S["users"]["dir"],
                                       "vtigerData": {"spcompany": "По умолчанию"}}, silent=False)
        self.assertEqual((loud["ok"], "must be silent" in loud.get("message", "")), (False, True), loud)
        self.assertEqual(sql(f"SELECT COUNT(*) FROM payment WHERE vtiger_id={vt + 2}"), [["0"]])
        loud = import_save("PaymentAllocation", {}, alloc["id"], op="remove", silent=False)
        self.assertFalse(loud["ok"], loud)
        self.assertEqual(sql(f"SELECT deleted FROM payment_allocation WHERE id='{alloc['id']}'"), [["0"]])
        # A write past the hooks is repaired by the settle command, which prints counts only.
        sql(f"UPDATE invoice SET paid_amount=1, settlement_state='partial' WHERE id='{inv['id']}'")
        dry = espo_console("itvolga-finance-settle", "--entity=Invoice", f"--id={inv['id']}", "--dry-run")
        self.assertEqual(dry.strip(), "[dry-run] Invoice would change: 1")
        self.assertEqual(settlement(inv)[0], "1.00000000", "dry run writes nothing")
        out = espo_console("itvolga-finance-settle", "--entity=Invoice", f"--id={inv['id']},{inv2['id']}")
        self.assertEqual(out.strip().splitlines(), ["Invoice changed: 1", "Invoice unchanged: 1"])
        self.assertEqual(settlement(inv), ("1000.00000000", "0.00000000", "paid"))
        # Removing an imported row (the importer) settles the document as well.
        removed = import_save("PaymentAllocation", {}, alloc["id"], op="remove")
        self.assertTrue(removed["ok"], removed)
        self.assertEqual(settlement(inv)[2], "unpaid")


if __name__ == "__main__":
    unittest.main()
