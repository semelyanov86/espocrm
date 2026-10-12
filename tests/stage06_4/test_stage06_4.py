"""Acceptance tests of the delta (stage 06.4, docs/migration/import.md «Дельта»): records and relations gone from the
source, activities that changed their type, finance records deleted in the source and back, the mass-removal rail, the
check-only preview, interruption and recovery, the whole-source column ledger and the tax measures — on the stand, with
the synthetic mini-Vtiger and files of stage 06.3 (its fixture, key block and cleanup) plus the records below. Pure
checks of the planner, the ledger and the snapshot difference run without the stand. No production data.

    task test:stage06.4
"""
import gzip
import hashlib
import json
import os
import secrets
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from decimal import Decimal
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "import"))
sys.path.insert(0, str(REPO / "scripts" / "snapshot"))
sys.path.insert(0, str(REPO / "tests" / "stage06_3"))
import importer  # noqa: E402
import ledger  # noqa: E402
import removals  # noqa: E402
import spec  # noqa: E402
import test_stage06_3 as t3  # noqa: E402
from common import SnapshotError, write_private  # noqa: E402
from test_stage06_3 import (A1, ACT1, ADMIN_NAME, AT2, AT3, C1, D1, D2, D3, EM1, I1, I2, KEYS, L4, L5, L6, N1, O1,  # noqa
                            PAY1, PAY4, PREFIX, Q1, SO1, U_ADMIN, U_SALES, VT, entity, insert, one, sql)

A2, A3, C3, U3, CL1, N2 = VT + 102, VT + 103, VT + 203, VT + 3, VT + 961, VT + 912
L8, L9 = VT + 608, VT + 609
WRITER = "command.php itvolga-import"


def extras():
    """Records of the 06.4 scenarios, added to the 06.3 fixture before the first import."""
    return [
        insert("vtiger_users", id=U3, user_name=f"synth-fin-{t3.HEX}-gone", last_name=f"{PREFIX} gone", is_admin="off",
               status="Active", currency_id=1, deleted=0),
        insert("vtiger_user2role", userid=U3, roleid="H4"),
        entity(A2, "Accounts"),
        insert("vtiger_account", accountid=A2, account_no="КОНТР_2", accountname=f"{PREFIX} A2"),
        insert("vtiger_accountscf", accountid=A2), insert("vtiger_accountbillads", accountaddressid=A2),
        insert("vtiger_accountshipads", accountaddressid=A2),
        insert("vtiger_crmentityrel", crmid=A2, module="Accounts", relcrmid=C1, relmodule="Contacts"),
        entity(A3, "Accounts"),
        insert("vtiger_account", accountid=A3, account_no="КОНТР_3", accountname=f"{PREFIX} A3"),
        insert("vtiger_accountscf", accountid=A3), insert("vtiger_accountbillads", accountaddressid=A3),
        insert("vtiger_accountshipads", accountaddressid=A3),
        entity(C3, "Contacts"),
        insert("vtiger_contactdetails", contactid=C3, contact_no=f"КОНТАКТ_{C3}", accountid=A1, lastname=f"{PREFIX} C3"),
        insert("vtiger_contactaddress", contactaddressid=C3), insert("vtiger_contactsubdetails", contactsubscriptionid=C3),
        insert("vtiger_contactscf", contactid=C3, cf_1322="synth-access-id"),
        insert("vtiger_customerdetails", customerid=C3),
        insert("vtiger_contpotentialrel", contactid=C1, potentialid=O1),
        entity(CL1, "Calendar"),
        insert("vtiger_activity", activityid=CL1, subject=f"{PREFIX} CL1", activitytype="Call", date_start="2020-03-01",
               time_start="12:00", due_date="2020-03-01", time_end="12:30", eventstatus="Held"),
        insert("vtiger_seactivityrel", crmid=O1, activityid=CL1),
        insert("vtiger_cntactivityrel", contactid=C1, activityid=CL1),
        insert("vtiger_salesmanactivityrel", smid=U_ADMIN, activityid=CL1),
        entity(N2, "ModComments", created="2023-07-02 12:00:00"),
        insert("vtiger_modcomments", modcommentsid=N2, commentcontent=f"{PREFIX} N2", related_to=CL1, userid=U_SALES,
               customer=0),
        insert("vtiger_modcommentscf", modcommentsid=N2),
    ]


def stored(attachment_id):
    """The attachment's file is in the stand's upload storage."""
    res = subprocess.run(["sudo", "-n", "test", "-e", str(REPO / "data" / "upload" / attachment_id)], check=False)
    return res.returncode == 0


def writers_alive():
    return subprocess.run(["pgrep", "-f", WRITER], capture_output=True, check=False).returncode == 0


class Stage064(t3.Stage063):
    runs = []

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        t3.source_sql("\n".join(extras()))

    @classmethod
    def run_import(cls, check_only=False, only=t3.ONLY, files_root=None, **kw):
        rundir = t3.ROOT / f"run-{len(cls.runs)}"
        rundir.mkdir()
        report = importer.execute(rundir, source_db=t3.SOURCE, only=only, check_only=check_only, adopt=ADMIN_NAME,
                                  key_range=KEYS, effective_admin=U_ADMIN, files_root=files_root or cls.files, **kw)
        recs = [json.loads(line) for line in (rundir / "records.jsonl").read_text().splitlines()]
        cls.runs.append(recs)
        return report, {r["key"]: r for r in recs}, rundir

    @classmethod
    def cleanup(cls):
        """The 06.3 cleanup plus the tables of events (calls, meetings, their links and reminders)."""
        ids = set()
        for recs in cls.runs:
            ids |= {r["id"] for r in recs if r.get("id") and r["key"].split(":")[0] in ("Call", "Meeting")}
        for journal in t3.ROOT.glob("run-*/applied.jsonl"):
            for line in journal.read_text().splitlines():
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if rec["key"].split(":")[0] in ("Call", "Meeting"):
                    ids.add(rec["id"])
        ids |= {i for t, i in cls.created if t == "Reminder"}
        if ids:
            listed = ",".join("'" + i + "'" for i in sorted(ids))
            script = [f"DELETE FROM reminder WHERE entity_id IN ({listed}) OR id IN ({listed});"]
            for table, column in (("call_contact", "call_id"), ("call_user", "call_id"), ("call_lead", "call_id"),
                                  ("contact_meeting", "meeting_id"), ("meeting_user", "meeting_id"),
                                  ("lead_meeting", "meeting_id"), ("call", "id"), ("meeting", "id")):
                script.append(f"DELETE FROM `{table}` WHERE `{column}` IN ({listed});")
            t3.Mysql.stand(database="espocrm").lines("\n".join(script) + "\n", t3.ROOT / "cleanup.log")
        cls.created = [(t, i) for t, i in cls.created if t != "Reminder"]
        super().cleanup()

    def assertClean(self, report):
        self.assertEqual(report["problems"], {}, report.get("problem_columns"))
        self.assertFalse(any(report["silence"].values()), report["silence"])

    def unchanged(self, recs):
        """Records the run wrote (statuses of no write: unchanged, skipped, kept by a policy of the target)."""
        return {r["key"]: r["apply"] for r in recs.values()
                if r["apply"] not in ("unchanged", "skipped", "protected", "deleted_in_target", "kept", None)}

    # --- scenarios (in order) ----------------------------------------------------------------------------------

    def test_01_full_import(self):
        report, recs, _ = self.run_import()
        self.assertClean(report)
        self.assertEqual(report["ledger"]["status"], "pass", report["ledger"].get("problems"))
        self.assertEqual(report["aggregates"]["reader"]["unequal"], 0)
        self.assertEqual(report["aggregates"]["writer"]["unequal"], 0)
        o1, c1, cl1 = self.id_of("opportunity", O1), self.id_of("contact", C1), self.id_of("call", CL1)
        self.assertEqual(one(f"SELECT COUNT(*) FROM contact_opportunity WHERE opportunity_id='{o1}' AND contact_id='{c1}' "
                             f"AND deleted=0"), ["1"])
        self.assertEqual(one(f"SELECT COUNT(*) FROM account_contact WHERE contact_id='{c1}' AND deleted=0"), ["2"])
        self.assertEqual(one(f"SELECT COUNT(*) FROM call_user WHERE call_id='{cl1}' AND deleted=0"), ["2"])  # + assignee
        self.assertEqual(one(f"SELECT COUNT(*) FROM contact_access WHERE vtiger_id={C3} AND deleted=0"), ["1"])

    def test_02_rerun_writes_nothing(self):
        report, recs, _ = self.run_import()
        self.assertClean(report)
        self.assertEqual(self.unchanged(recs), {})
        self.assertEqual(report["removals"]["plan"]["operations"], 0)

    def test_03_owned_links_follow_the_source(self):
        o1, c1, c3, cl1 = (self.id_of(t, k) for t, k in (("opportunity", O1), ("contact", C1), ("contact", C3),
                                                         ("call", CL1)))
        d1, a2 = self.id_of("document", D1), self.id_of("account", A2)
        status, body, _ = self.client.post("Contact", {"lastName": f"{PREFIX} manual"})
        self.assertEqual(status, 200)
        self.created.append(("Contact", body["id"]))
        manual_contact = body["id"]
        status, body, _ = self.client.post("Account", {"name": f"{PREFIX} manual"})
        self.assertEqual(status, 200)
        self.created.append(("Account", body["id"]))
        manual_account = body["id"]
        for path, target in ((f"Opportunity/{o1}/contacts", c3), (f"Opportunity/{o1}/contacts", manual_contact),
                             (f"Document/{d1}/accounts", manual_account)):
            self.assertEqual(self.client.post(path, {"id": target})[0], 200)
        t3.source_sql(f"DELETE FROM vtiger_contpotentialrel WHERE contactid={C1} AND potentialid={O1};"
                      f"DELETE FROM vtiger_salesmanactivityrel WHERE smid={U_ADMIN} AND activityid={CL1};"
                      f"DELETE FROM vtiger_senotesrel WHERE crmid={ACT1} AND notesid={D1};"
                      f"DELETE FROM vtiger_crmentityrel WHERE crmid={A2} AND relcrmid={C1};")
        report, recs, _ = self.run_import()
        self.assertClean(report)
        live = "deleted=0"
        self.assertEqual(sql(f"SELECT contact_id FROM contact_opportunity WHERE opportunity_id='{o1}' AND {live}"),
                         [[manual_contact]])                                     # imported C1, C3 gone; manual stays
        self.assertEqual(sql(f"SELECT user_id FROM call_user WHERE call_id='{cl1}' AND {live}"),
                         [[one(f"SELECT id FROM user WHERE vtiger_id={U_SALES}")[0]]])   # the assignee stays
        self.assertEqual(one(f"SELECT COUNT(*) FROM act_document WHERE document_id='{d1}' AND {live}"), ["0"])
        self.assertEqual(one(f"SELECT COUNT(*) FROM account_document WHERE document_id='{d1}' AND "
                             f"account_id='{manual_account}' AND {live}"), ["1"])
        self.assertEqual(one(f"SELECT COUNT(*) FROM account_contact WHERE contact_id='{c1}' AND account_id='{a2}' "
                             f"AND {live}"), ["0"])
        links = report["removals"]["removed_links"]
        self.assertEqual(links.get("Opportunity.contacts"), 2)
        self.assertEqual(links.get("Call.users"), 1)
        self.assertEqual(links.get("Document.relate.cActs"), 1)
        self.assertEqual(recs[f"Opportunity:{O1}"]["check"], "equal")
        report, recs, _ = self.run_import()                                       # no churn (core-derived assignee)
        self.assertClean(report)
        self.assertEqual(self.unchanged(recs), {})

    def test_04_partial_run_keeps_links_of_types_outside_it(self):
        o1, c3 = self.id_of("opportunity", O1), self.id_of("contact", C3)
        self.assertEqual(self.client.post(f"Opportunity/{o1}/contacts", {"id": c3})[0], 200)
        report, recs, _ = self.run_import(only="Potentials")                     # Contact is not owned by the run
        self.assertClean(report)
        self.assertEqual(one(f"SELECT COUNT(*) FROM contact_opportunity WHERE opportunity_id='{o1}' AND contact_id='{c3}' "
                             f"AND deleted=0"), ["1"])
        report, recs, _ = self.run_import()
        self.assertClean(report)
        self.assertEqual(one(f"SELECT COUNT(*) FROM contact_opportunity WHERE opportunity_id='{o1}' AND contact_id='{c3}' "
                             f"AND deleted=0"), ["0"])

    def test_05_mass_removal_rail_refuses_before_any_write(self):
        d1 = self.id_of("document", D1)
        t3.source_sql(f"UPDATE vtiger_crmentity SET deleted=1 WHERE crmid={D1};")
        try:
            rundir = t3.ROOT / "run-rail"
            rundir.mkdir()
            with self.assertRaises(SnapshotError):
                importer.execute(rundir, source_db=t3.SOURCE, only=t3.ONLY, adopt=ADMIN_NAME, key_range=KEYS,
                                 effective_admin=U_ADMIN, files_root=self.files, rail={"floor": 0, "share": Decimal(0)})
            self.assertFalse((rundir / "applied.jsonl").exists())                # nothing written
            self.assertEqual(one(f"SELECT deleted FROM document WHERE id='{d1}'"), ["0"])
        finally:
            t3.source_sql(f"UPDATE vtiger_crmentity SET deleted=0 WHERE crmid={D1};")

    def test_06_records_gone_from_the_source_are_removed(self):
        ids = {k: self.id_of(t, k) for t, k in (("contact", C3), ("email", EM1), ("note", N1), ("document", D2))}
        a2 = self.id_of("account", A2)
        access = one(f"SELECT id FROM contact_access WHERE vtiger_id={C3} AND deleted=0")[0]
        files = {k: one(f"SELECT id FROM attachment WHERE vtiger_id={k}")[0] for k in (AT2, AT3)}
        self.assertTrue(all(stored(f) for f in files.values()))
        user = one(f"SELECT id FROM user WHERE vtiger_id={U3}")[0]
        t3.source_sql(f"UPDATE vtiger_crmentity SET deleted=1 WHERE crmid IN ({C3}, {EM1}, {N1}, {D2});"
                      f"DELETE FROM vtiger_crmentity WHERE crmid={A2};"                  # purged in Vtiger
                      f"UPDATE vtiger_users SET deleted=1 WHERE id={U3};")
        report, recs, _ = self.run_import(allow_mass_removal=True)               # Email: the only one goes
        self.assertClean(report)
        for key, eid in list(ids.items()) + [(A2, a2)]:
            self.assertEqual(one(f"SELECT deleted FROM {self.table_of(key)} WHERE id='{eid}'"), ["1"], key)
        self.assertEqual(one(f"SELECT deleted FROM contact_access WHERE id='{access}'"), ["1"])
        self.assertEqual(one(f"SELECT deleted, is_active FROM user WHERE id='{user}'"), ["0", "0"])   # deactivated
        for att in files.values():
            self.assertEqual(one(f"SELECT deleted FROM attachment WHERE id='{att}'"), ["1"])
            self.assertFalse(stored(att))                                         # the core hook removed the bytes
        self.assertEqual(recs[f"User:{U3}"]["apply"], "deactivated")
        self.assertEqual({recs[f"{t}:{k}"]["check"] for t, k in (("Contact", C3), ("ContactAccess", C3),
                                                                  ("Email", EM1), ("Note", N1), ("Account", A2))},
                         {"removed"})
        self.assertGreaterEqual(report["findings"].get("mass_removal_allowed", 0), 1)
        report, recs, _ = self.run_import()                                       # nothing left to remove
        self.assertClean(report)
        self.assertEqual(report["removals"]["plan"]["operations"], 0)
        self.assertEqual(self.unchanged(recs), {})

    def table_of(self, key):
        return {C3: "contact", EM1: "email", N1: "note", D2: "document", A2: "account"}[key]

    def test_07_stale_items_of_an_edited_invoice(self):
        old = {k: one(f"SELECT id FROM invoice_item WHERE vtiger_id={k}")[0] for k in (L4, L5)}
        t3.source_sql(f"UPDATE vtiger_inventoryproductrel SET lineitem_id={L8} WHERE lineitem_id={L4};"
                      f"UPDATE vtiger_inventoryproductrel SET lineitem_id={L9} WHERE lineitem_id={L5};")
        report, recs, _ = self.run_import()
        self.assertClean(report)
        self.assertEqual({recs[f"InvoiceItem:{k}"]["apply"] for k in (L8, L9)}, {"created"})
        for item in old.values():
            row = one(f"SELECT deleted, removed_by_edit, JSON_EXTRACT(vtiger_data, '$.deletedInSource') "
                      f"FROM invoice_item WHERE id='{item}'")
            self.assertEqual(row, ["1", "1", "true"])
        self.assertEqual(report["aggregates"]["writer"]["unequal"], 0)
        self.assertEqual(report["finance"]["settle_drift"], 0)
        invoice = self.id_of("invoice", I1)
        self.assertEqual(one(f"SELECT COUNT(*) FROM invoice_item WHERE invoice_id='{invoice}' AND deleted=0"), ["2"])

    def test_08_finance_deleted_in_the_source_and_back(self):
        invoice, payment = self.id_of("invoice", I2), self.id_of("payment", PAY4)
        allocation = one(f"SELECT id FROM payment_allocation WHERE vtiger_id={PAY4} AND deleted=0")[0]
        item = one(f"SELECT id FROM invoice_item WHERE vtiger_id={L6}")[0]
        t3.source_sql(f"UPDATE vtiger_crmentity SET deleted=1 WHERE crmid IN ({I2}, {PAY4});")
        report, recs, _ = self.run_import()
        self.assertClean(report)
        for table, eid in (("invoice", invoice), ("invoice_item", item), ("payment", payment),
                           ("payment_allocation", allocation)):
            self.assertEqual(one(f"SELECT deleted, JSON_EXTRACT(vtiger_data, '$.deletedInSource') FROM {table} "
                                 f"WHERE id='{eid}'"), ["1", "true"], table)
        self.assertEqual(report["finance"]["settle_drift"], 0)
        t3.source_sql(f"UPDATE vtiger_crmentity SET deleted=0 WHERE crmid IN ({I2}, {PAY4});")   # restored in Vtiger
        report, recs, _ = self.run_import()
        self.assertClean(report)
        for key, table, eid in ((f"Invoice:{I2}", "invoice", invoice), (f"InvoiceItem:{L6}", "invoice_item", item),
                                (f"Payment:{PAY4}", "payment", payment),
                                (f"PaymentAllocation:{PAY4}", "payment_allocation", allocation)):
            self.assertEqual(recs[key]["apply"], "restored", key)
            self.assertEqual(recs[key]["check"], "equal", key)
            self.assertEqual(one(f"SELECT deleted, JSON_EXTRACT(vtiger_data, '$.deletedInSource') IS NULL FROM {table} "
                                 f"WHERE id='{eid}'"), ["0", "1"], table)
        self.assertEqual(one(f"SELECT removed_by_edit FROM invoice_item WHERE id='{item}'"), ["0"])
        self.assertEqual(one(f"SELECT removed_with IS NULL FROM payment_allocation WHERE id='{allocation}'"), ["1"])
        act = self.id_of("act", ACT1)
        self.assertEqual(self.client.delete(f"Act/{act}")[0], 200)              # deleted in EspoCRM: D-148 holds
        report, recs, _ = self.run_import()
        self.assertClean(report)
        self.assertEqual(recs[f"Act:{ACT1}"]["check"], "deleted_in_target")
        self.assertEqual(one(f"SELECT deleted FROM act WHERE id='{act}'"), ["1"])

    def test_09_recalculated_document_is_kept(self):
        quote = self.id_of("quote", Q1)
        status, body, _ = self.client.get(f"Quote/{quote}")
        self.assertEqual(status, 200)
        items = body["itemList"]
        items[0]["quantity"] = "3"
        for item in items:
            item["taxRate"] = "0"
        self.assertEqual(self.client.put(f"Quote/{quote}", {"itemList": items})[0], 200)
        t3.source_sql(f"UPDATE vtiger_crmentity SET deleted=1 WHERE crmid={Q1};")
        try:
            report, recs, _ = self.run_import(allow_mass_removal=True)
            self.assertClean(report)
            self.assertEqual(recs[f"Quote:{Q1}"]["check"], "kept")
            self.assertEqual(one(f"SELECT deleted FROM quote WHERE id='{quote}'"), ["0"])
            self.assertGreaterEqual(report["findings"].get("kept_in_target:recalculated_in_target", 0), 1)
        finally:
            t3.source_sql(f"UPDATE vtiger_crmentity SET deleted=0 WHERE crmid={Q1};")

    def test_10_activity_type_change(self):
        call = self.id_of("call", CL1)
        user = one(f"SELECT id FROM user WHERE vtiger_id={U_SALES}")[0]
        rid = "synthimp" + t3.HEX + "r4"
        sql(f"INSERT INTO reminder (id, remind_at, start_at, type, seconds, entity_type, entity_id, user_id, deleted) "
            f"VALUES ('{rid}', '2030-01-01 08:00:00', '2030-01-01 09:00:00', 'Popup', 3600, 'Call', '{call}', '{user}', 0)")
        self.created.append(("Reminder", rid))
        status, body, _ = self.client.post("Note", {"type": "Post", "parentType": "Call", "parentId": call,
                                                    "post": f"{PREFIX} manual"})
        self.assertEqual(status, 200)
        self.created.append(("Note", body["id"]))
        t3.source_sql(f"UPDATE vtiger_activity SET activitytype='Meeting' WHERE activityid={CL1};")
        report, recs, _ = self.run_import()
        self.assertClean(report)
        meeting = self.id_of("meeting", CL1)
        self.assertEqual(recs[f"Meeting:{CL1}"]["apply"], "created")
        self.assertEqual(one(f"SELECT deleted FROM `call` WHERE id='{call}'"), ["1"])
        self.assertEqual(one(f"SELECT entity_type, entity_id FROM reminder WHERE id='{rid}'"), ["Meeting", meeting])
        self.assertEqual(one(f"SELECT parent_type, parent_id FROM note WHERE vtiger_id={N2}"), ["Meeting", meeting])
        self.assertEqual(report["findings"].get("retyped_notes_left"), 1)
        self.assertEqual(report["removals"]["retyped"], {"Call->Meeting": 1})
        t3.source_sql(f"UPDATE vtiger_activity SET activitytype='Call' WHERE activityid={CL1};")
        report, recs, _ = self.run_import()
        self.assertClean(report)
        self.assertEqual(recs[f"Call:{CL1}"]["apply"], "restored")
        self.assertEqual(self.id_of("call", CL1), call)                          # the same record comes back
        self.assertEqual(one(f"SELECT deleted FROM meeting WHERE id='{meeting}'"), ["1"])
        self.assertEqual(recs[f"Call:{CL1}"]["check"], "equal")

    def test_11_check_only_plans_without_writing(self):
        d3 = self.id_of("document", D3)
        t3.source_sql(f"UPDATE vtiger_crmentity SET deleted=1 WHERE crmid={D3};")
        report, recs, _ = self.run_import(check_only=True)
        self.assertEqual(report["problems"], {}, report.get("problem_columns"))
        self.assertEqual(report["findings"].get("would_remove"), 1)
        self.assertEqual(recs[f"Document:{D3}"]["check"], "live")
        self.assertEqual(one(f"SELECT deleted FROM document WHERE id='{d3}'"), ["0"])
        report, recs, _ = self.run_import()
        self.assertClean(report)
        self.assertEqual(one(f"SELECT deleted FROM document WHERE id='{d3}'"), ["1"])

    def driver(self, name):
        rundir = t3.ROOT / f"run-{name}"
        rundir.mkdir()
        params = {"rundir": str(rundir), "source": t3.SOURCE, "only": t3.ONLY, "adopt": ADMIN_NAME, "keys": list(KEYS),
                  "admin": U_ADMIN, "files": str(self.files), "category": t3.CATEGORY}
        proc = subprocess.Popen([sys.executable, str(Path(__file__).with_name("driver.py"))], stdin=subprocess.PIPE,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        proc.stdin.write(json.dumps(params).encode())
        proc.stdin.close()
        journal = rundir / "applied.jsonl"
        deadline = time.time() + 600
        while time.time() < deadline and proc.poll() is None:
            written = [json.loads(x) for x in (journal.read_text().splitlines() if journal.exists() else [])
                       if x.strip().endswith("}")]
            if sum(1 for e in written if e.get("status") == "updated") >= 3:
                return proc, rundir
            time.sleep(0.05)
        self.fail("the run ended before the interruption point")

    def touch_descriptions(self, text):
        """A change of every record with a description: the next run has dozens of writes to interrupt."""
        t3.source_sql(f"UPDATE vtiger_crmentity SET description='{text}' WHERE crmid BETWEEN {KEYS[0]} AND {KEYS[1]} "
                      f"AND setype IN ('Accounts', 'Contacts', 'Potentials', 'Vendors', 'Products', 'Services', "
                      f"'Quotes', 'SalesOrder', 'Invoice', 'Act');")

    def test_12_interruption_and_recovery(self):
        self.touch_descriptions("synth-a")
        proc, _ = self.driver("term")
        os.killpg(proc.pid, signal.SIGTERM)
        self.assertEqual(proc.wait(timeout=120), 130)
        time.sleep(1)
        self.assertFalse(writers_alive())
        part = f".itvolga-import-{secrets.token_hex(12)}.part"                    # as a killed writer leaves it
        t3.as_stand("touch", f"data/upload/{part}")
        report, recs, _ = self.run_import()                                      # converges
        self.assertClean(report)
        self.assertGreaterEqual(report["swept"], 1)
        self.assertFalse(stored(part))
        self.touch_descriptions("synth-b")
        proc, _ = self.driver("kill")
        os.killpg(proc.pid, signal.SIGKILL)                                       # the importer and the writer die
        subprocess.run(["sudo", "-n", "pkill", "-KILL", "-f", WRITER], check=False)
        proc.wait(timeout=60)
        report, recs, _ = self.run_import()
        self.assertClean(report)
        self.assertEqual({r["check"] for r in recs.values() if not r.get("removal") and not r["held"]} -
                         {"absent", "deleted_in_target", "protected"}, {"equal"})
        report, recs, _ = self.run_import()
        self.assertClean(report)
        self.assertEqual(self.unchanged(recs), {})

    def test_13_ledger_and_taxes(self):
        t3.source_sql("CREATE TABLE vtiger_synth_new (id INT, note VARCHAR(10)) ENGINE=InnoDB;"
                      "INSERT INTO vtiger_synth_new VALUES (1, 'x');")
        try:
            report, recs, _ = self.run_import(check_only=True)
            self.assertEqual(report["problems"].get("ledger_no_fate"), 2)       # a table Vtiger got after the audit
        finally:
            t3.source_sql("DROP TABLE vtiger_synth_new;")
        report, recs, _ = self.run_import()
        self.assertClean(report)
        self.assertEqual(report["ledger"]["status"], "pass")
        self.assertGreater(report["ledger"]["import"]["deleted"], 0)              # values of records deleted in Vtiger
        self.assertEqual(report["aggregates"]["reader"]["measures"], 112)
        self.assertEqual(report["aggregates"]["reader"]["unequal"], 0)
        self.assertEqual(report["aggregates"]["writer"]["unequal"], 0)


    def test_14_live_record_without_base_row_is_not_removed(self):
        """A live Vtiger record the reader cannot see (no base row) proves nothing: its type is not removed."""
        a3 = self.id_of("account", A3)
        t3.source_sql(f"DELETE FROM vtiger_account WHERE accountid={A3};")
        try:
            report, recs, _ = self.run_import()
            self.assertEqual(report["problems"].get("live_without_base_row"), 1)
            self.assertIn("Account", report["removals"]["blocked"])
            self.assertEqual(one(f"SELECT deleted FROM account WHERE id='{a3}'"), ["0"])
        finally:
            t3.source_sql(insert("vtiger_account", accountid=A3, account_no="КОНТР_3", accountname=f"{PREFIX} A3"))
        report, recs, _ = self.run_import()
        self.assertClean(report)

    def test_15_held_payment_keeps_its_allocation(self):
        allocation = one(f"SELECT id FROM payment_allocation WHERE vtiger_id={PAY1} AND deleted=0")[0]
        t3.source_sql(f"UPDATE sp_payments SET pay_type='Неизвестно' WHERE payid={PAY1};")   # a planning error
        try:
            report, recs, _ = self.run_import()
            self.assertEqual(recs[f"Payment:{PAY1}"]["held"], "error:enum_unmapped")
            self.assertEqual(report["removals"]["plan"]["operations"], 0)
            self.assertEqual(one(f"SELECT deleted FROM payment_allocation WHERE id='{allocation}'"), ["0"])
        finally:
            t3.source_sql(f"UPDATE sp_payments SET pay_type='Приход' WHERE payid={PAY1};")
        report, recs, _ = self.run_import()
        self.assertClean(report)

    def test_16_allocated_document_waits_and_a_manual_deletion_is_final(self):
        """A document an imported allocation outside the run points to stays (its hook would remove the allocation
        without the delta's mark); a delta tombstone restored and deleted by a user loses its mark (D-148)."""
        order = self.id_of("sales_order", SO1)
        allocation = one(f"SELECT id FROM payment_allocation WHERE vtiger_id={PAY4} AND deleted=0")[0]
        t3.source_sql(f"UPDATE vtiger_crmentity SET deleted=1 WHERE crmid={SO1};")
        report, recs, _ = self.run_import(only="SalesOrder", allow_mass_removal=True)
        self.assertEqual(report["problems"], {}, report.get("problem_columns"))
        self.assertEqual(recs[f"SalesOrder:{SO1}"]["check"], "kept")
        self.assertEqual(recs[f"SalesOrder:{SO1}"]["reason"], "allocated_in_target")
        report, recs, _ = self.run_import(allow_mass_removal=True)               # the allocation goes first
        self.assertClean(report)
        for table, eid in (("sales_order", order), ("payment_allocation", allocation)):
            self.assertEqual(one(f"SELECT deleted, JSON_EXTRACT(vtiger_data, '$.deletedInSource') FROM {table} "
                                 f"WHERE id='{eid}'"), ["1", "true"], table)
        sql(f"UPDATE sales_order SET deleted=0 WHERE id='{order}'")              # restored by a user (mark kept) …
        self.assertEqual(self.client.delete(f"SalesOrder/{order}")[0], 200)      # … and deleted by a user
        self.assertEqual(one(f"SELECT deleted, JSON_EXTRACT(vtiger_data, '$.deletedInSource') IS NULL FROM sales_order "
                             f"WHERE id='{order}'"), ["1", "1"])
        t3.source_sql(f"UPDATE vtiger_crmentity SET deleted=0 WHERE crmid={SO1};")
        report, recs, _ = self.run_import()
        self.assertClean(report)
        self.assertEqual(recs[f"SalesOrder:{SO1}"]["check"], "deleted_in_target")


class Pure(unittest.TestCase):
    """Planner, ledger and snapshot difference without the stand."""

    def plan(self, ops, held=()):
        return spec.Plan(list(ops), list(held), {})

    def test_removal_plan(self):
        ops = [spec.Op("Account", 10, "Accounts"), spec.Op("Meeting", 20, "Events"), spec.Op("InvoiceItem", 31, "Invoice")]
        held = [spec.Op("Account", 11, "Accounts")]
        inventory = {"Account": {"live": [10, 11, 12, 900000001]}, "Call": {"live": [20, 21]},
                     "InvoiceItem": {"live": [30, 31]}, "User": {"live": [5, 6], "inactive": [6]}}
        out = removals.plan_removals(self.plan(ops, held), inventory, ["Account", "Call", "InvoiceItem", "User"],
                                     (1, 899999999), rail={"floor": 25, "share": Decimal("0.05")})
        self.assertEqual([(o.entityType, o.vtigerId) for o in out.ops],
                         [("Call", 21), ("InvoiceItem", 30), ("Account", 12), ("User", 5)])  # reverse ORDER
        self.assertEqual(dict(out.retyped), {"Call": 1})                       # Call 20 is now a Meeting
        self.assertEqual(out.refused, ["Call", "User"])                         # nothing of the type left in the source
        out = removals.plan_removals(self.plan(ops, held), inventory, ["Account"], (1, 899999999),
                                     rail={"floor": 0, "share": Decimal(0)})
        self.assertEqual(out.refused, ["Account"])

    def test_owned_links_and_relations(self):
        doc = spec.Op("Document", 5, "Documents")
        doc.add_relate("accounts", ("Account", 7))
        contact = spec.Op("Contact", 6, "Contacts")
        spec.claim_links([doc, contact])
        payload = doc.payload()
        self.assertEqual(payload["relate"]["accounts"], {"items": [["Account", 7]], "owned": True})
        self.assertEqual(payload["relate"]["cActs"], {"items": [], "owned": True})     # an emptied relation still owned
        self.assertEqual(contact.payload()["linkMultiple"]["accounts"], {"items": [], "owned": True})
        self.assertEqual(spec.owned_types(["Products"]), [])                       # Product needs Services too
        self.assertIn("Product", spec.owned_types(["Products", "Services"]))

    def test_ledger(self):
        fields = [
            {"source_module": "", "source_table": "t_unread", "source_column": "a", "fate": "не переносится: x",
             "target_field": "—"},
            {"source_module": "PBXManager", "source_table": "t_pbx", "source_column": "k", "fate": "перенос",
             "target_field": "x"},
            {"source_module": "", "source_table": "t_pbx", "source_column": "b", "fate": "перенос", "target_field": "x"},
            {"source_module": "Campaigns", "source_table": "t_lost", "source_column": "c", "fate": "перенос",
             "target_field": "x"},
            {"source_module": "Accounts", "source_table": "t_read", "source_column": "v", "fate": "перенос",
             "target_field": "Account.v"},
        ]
        counts = {"vtiger7": {"t_unread": {"a": [3, None]}, "t_pbx": {"k": [1, 1], "b": [2, None]},
                              "t_lost": {"c": [1, None]}, "t_read": {"v": [5, None], "w": [0, None]},
                              "t_new": {"z": [1, None]}},
                  "asteriskcdrdb": {"cdr": {"src": [9, None]}}}
        census = {"Accounts": {"t_read.v": (3, 3)}}
        columns = [{"module": "Accounts", "column": "t_read.v", "category": "rule", "verified": 3, "mismatch": 0,
                    "unaccounted": 0}]
        out = ledger.build(counts, fields, census, {"Accounts": {"t_read.v": (1, 1)}}, columns, {"status": "fail"})
        rows = {(r["schema"], r["table"], r["column"]): r for r in out["rows"]}
        self.assertEqual(rows[("vtiger7", "t_read", "v")]["outside_scope"], 1)
        self.assertEqual(rows[("vtiger7", "t_pbx", "b")]["cls"], "pending:07.2")  # physical row of a pending table
        self.assertEqual(rows[("asteriskcdrdb", "cdr", "src")]["cls"], "pending:07.2")
        self.assertEqual(out["problems"], {"no_fate": ["vtiger7.t_new.z"], "transfer_unread": ["vtiger7.t_lost.c"],
                                           "maps_outdated": ["fail"]})
        out = ledger.build(counts, fields, {"Accounts": {"t_read.v": (9, 9)}}, {}, columns, None)
        self.assertIn("vtiger7.t_read.v", out["problems"]["counts_disagree"])

    def test_stop_group_does_not_hang_on_a_full_pipe(self):
        """A client that reads nothing while the feeder is blocked on a full pipe is still stopped."""
        import threading
        from common import stop_group
        proc = subprocess.Popen(["sleep", "60"], stdin=subprocess.PIPE, start_new_session=True)
        feeder = threading.Thread(target=lambda: _write_quietly(proc.stdin, b"x" * (16 << 20)), daemon=True)
        feeder.start()
        time.sleep(0.5)
        done = threading.Event()
        threading.Thread(target=lambda: (stop_group(proc, grace=1), done.set()), daemon=True).start()
        self.assertTrue(done.wait(20))
        self.assertIsNotNone(proc.poll())

    def test_snapshot_difference(self):
        import diff
        import verify
        root = Path(tempfile.mkdtemp(prefix="vtdiff-"))
        self.addCleanup(shutil.rmtree, root, True)

        def tok(v):
            return "N" if v is None else str(v).encode().hex().upper()

        def snap(name, crm, free):
            d = root / name
            for sub in ("db/vtiger7/rows", "db/vtiger7/ddl", "inventory"):
                (d / sub).mkdir(parents=True, mode=0o700, exist_ok=True)
                os.chmod(d / sub, 0o700)
            for p in (d, d / "db", d / "db/vtiger7"):
                os.chmod(p, 0o700)
            tables = {}
            for table, rows, ddl in (("vtiger_crmentity", crm, "PRIMARY KEY (`crmid`)"), ("t_free", free, "")):
                cols = ["crmid", "setype", "deleted"] if table == "vtiger_crmentity" else ["a"]
                lines = sorted("\t".join(tok(v) for v in r).encode() for r in rows)
                data = b"".join(line + b"\n" for line in lines)
                write_private(d / f"db/vtiger7/rows/{table}.hex.gz", gzip.compress(data, mtime=0))
                write_private(d / f"db/vtiger7/ddl/{table}.sql", f"CREATE TABLE `{table}` ({ddl})")
                tables[table] = {"columns": [{"name": c} for c in cols], "rows": len(rows),
                                 "lanes": [hashlib.sha256(data).hexdigest()],
                                 "rows_file": f"rows/{table}.hex.gz", "ddl_file": f"ddl/{table}.sql",
                                 "ddl_sha256": ddl}
            write_private(d / "db/vtiger7/tables.json", json.dumps(tables))
            write_private(d / "MANIFEST.json", json.dumps({"files": {}}))
            verify.write_seal(d)
            return d
        a = snap("A", [(1, "Accounts", 0), (2, "Contacts", 0), (3, "Contacts", 0), (4, "Leads", 1)], [("x",), ("x",)])
        b = snap("B", [(1, "Accounts", 1), (2, "Contacts", 0), (4, "Leads", 0), (5, "Accounts", 0)], [("x",), ("y",)])
        report = diff.compare(a, b)
        changed = report["schemas"]["vtiger7"]["changed"]
        self.assertEqual({k: changed["vtiger_crmentity"][k] for k in ("new", "changed", "deleted")},
                         {"new": 1, "changed": 2, "deleted": 1})
        self.assertEqual({k: changed["t_free"][k] for k in ("added", "removed", "changed")},
                         {"added": 1, "removed": 1, "changed": None})
        self.assertEqual(report["records"], {"Accounts": {"deleted": 1, "new": 1}, "Contacts": {"purged": 1},
                                             "Leads": {"restored": 1}})
        self.assertNotIn("Accounts\t", diff.render(report))


def _write_quietly(pipe, data):
    try:
        pipe.write(data)
    except (BrokenPipeError, OSError, ValueError):
        pass


def load_tests(loader, tests, pattern):
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(Pure))
    names = sorted(n for n in Stage064.__dict__ if n.startswith("test_"))
    suite.addTests(Stage064(n) for n in names)
    return suite
