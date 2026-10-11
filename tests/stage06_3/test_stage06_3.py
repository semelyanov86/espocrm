"""Acceptance tests of the import of finances, documents and files (stage 06.3, docs/migration/import.md) on the stand.

A synthetic mini-Vtiger (real column types, synthetic values, keys in a random block ≥ 900 000 000) and a synthetic
file part (files of the attachments, one over the 3 MiB frame) are imported by the same code as a real run
(importer.execute with `source_db` and `files_root`). The single legal entity and the numbering counters of the stand
are never written by the test (OrganizationDetails is not selected, the synthetic numbering table is empty). Checks go
through SQL, the run reports and the stand's own download entry point. Cleanup removes only the records and files whose
ids this test recorded. No production data.

    task test:stage06.3
"""
import fcntl
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from decimal import Decimal
from unittest import mock
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "import"))
sys.path.insert(0, str(REPO / "tests" / "stage03"))
sys.path.insert(0, str(REPO / "tests" / "stage06_2"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import importer  # noqa: E402
import spec  # noqa: E402
import spec_finance  # noqa: E402
import verify  # noqa: E402
from common import Mysql  # noqa: E402
from espo import Client, admin_credentials  # noqa: E402
from schema import ACTIVITY_EXTRA, COLUMNS_063  # noqa: E402
from test_stage06_2 import COLUMNS as COLUMNS_062  # noqa: E402

HEX = secrets.token_hex(3)
VT = 900_000_000 + secrets.randbelow(89_000_000) // 1000 * 1000
KEYS = (VT, VT + 999)
PREFIX = f"SYNTH-fin-{HEX}"
ADMIN_NAME = f"synth-fin-{HEX}-admin"
ONLY = ",".join(m for m in spec.SCOPE if m != "OrganizationDetails")  # never the real legal entity

U_ADMIN, U_SALES = VT + 1, VT + 2
A1, C1, C2, O1, V1, S1, P1 = VT + 101, VT + 201, VT + 202, VT + 401, VT + 301, VT + 311, VT + 312
Q1, SO1, ACT1, I1, I2, I3 = VT + 501, VT + 502, VT + 503, VT + 504, VT + 505, VT + 506  # I3: added by test_12
L1, L2, L3, L4, L5, L6, L7 = (VT + 601 + i for i in range(7))
PAY1, PAY2, PAY3, PAY4, PAY5 = (VT + 701 + i for i in range(5))
FD, D1, D2, D3 = VT + 801, VT + 811, VT + 812, VT + 813
AT1, AT2, AT3, AT_PHOTO, AT_AVATAR = VT + 821, VT + 822, VT + 823, VT + 824, VT + 825
F1, N1, EM1 = VT + 901, VT + 911, VT + 931
CS1, J1, M1, AS1, SC1 = VT + 951, VT + 952, VT + 953, VT + 954, VT + 955
FILES = {AT1: ("synth.pdf", "application/pdf", 3 * 1024 * 1024 + 4321),  # two frames
         AT2: ("note file.txt", "text/plain", 1000), AT3: ("mail.bin", "application/octet-stream", 2048),
         AT_PHOTO: ("photo.png", "image/png", 512), AT_AVATAR: ("avatar.png", "image/png", 256)}
TABLES = {"User": "user", "Account": "account", "Contact": "contact", "Opportunity": "opportunity", "Vendor": "vendor",
          "Product": "product", "Quote": "quote", "QuoteItem": "quote_item", "SalesOrder": "sales_order",
          "SalesOrderItem": "sales_order_item", "Act": "act", "ActItem": "act_item", "Invoice": "invoice",
          "InvoiceItem": "invoice_item", "Payment": "payment", "PaymentAllocation": "payment_allocation",
          "Document": "document", "DocumentFolder": "document_folder", "KnowledgeBaseArticle": "knowledge_base_article",
          "Email": "email", "Note": "note", "VtigerArchive": "vtiger_archive", "Attachment": "attachment",
          "ContactAccess": "contact_access"}
JUNCTIONS = ("entity_team", "entity_email_address", "entity_phone_number", "entity_user", "email_user",
             "email_email_address", "account_document", "act_document", "c_case_document",
             "c_knowledge_base_article_document", "c_opportunity_product", "contact_document", "document_lead",
             "document_opportunity", "invoice_document", "knowledge_base_article_knowledge_base_category",
             "payment_document", "project_document", "project_task_document", "quote_document",
             "sales_order_document", "vtiger_archive_document", "account_contact", "contact_opportunity", "role_user",
             "team_user", "stream_subscription", "notification", "array_value", "preferences", "user_data")


def q(value):
    if value is None:
        return "NULL"
    return "_utf8mb4 X'" + str(value).encode("utf-8").hex() + "'"


def insert(table, **values):
    return f"INSERT INTO `{table}` ({', '.join(values)}) VALUES ({', '.join(q(v) for v in values.values())});"


def entity(crmid, setype, owner=None, created="2020-03-01 12:00:00", modified="2023-07-01 12:00:00", deleted=0,
           description=None):
    return insert("vtiger_crmentity", crmid=crmid, smcreatorid=U_SALES, smownerid=owner or U_SALES, modifiedby=U_SALES,
                  setype=setype, description=description, createdtime=created, modifiedtime=modified,
                  deleted=deleted, source="CRM", label="x")


ADDRESS_KEYS = {"vtiger_quotesbillads": "quotebilladdressid", "vtiger_quotesshipads": "quoteshipaddressid",
                "vtiger_sobillads": "sobilladdressid", "vtiger_soshipads": "soshipaddressid",
                "vtiger_sp_actbillads": "actbilladdressid", "vtiger_sp_actshipads": "actshipaddressid",
                "vtiger_invoicebillads": "invoicebilladdressid", "vtiger_invoiceshipads": "invoiceshipaddressid"}


def document(module, key, base, extra, lines, bill, ship, cf=None):
    """A finance document: crmentity + header + addresses (+ cf) + lines [(lineitem, product, qty, price, more)]."""
    s = [entity(key, module), insert(base[0], **{base[1]: key}, **extra),
         insert(bill, **{ADDRESS_KEYS[bill]: key}, bill_city="Синтград"), insert(ship, **{ADDRESS_KEYS[ship]: key})]
    if cf:
        s.append(insert(cf[0], **{cf[1]: key}))
    for seq, (line, product, qty, price, more) in enumerate(lines, 1):
        values = {"id": key, "productid": product, "sequence_no": seq, "quantity": qty, "listprice": price,
                  "lineitem_id": line, "tax1": "0.000", "discount_amount": None, **more}
        s.append(insert("vtiger_inventoryproductrel", **values))
    return s


def header(number_col, number, **more):
    return {number_col: number, "subject": f"{PREFIX} {number}", "accountid": A1, "taxtype": "individual",
            "currency_id": 1, "conversion_rate": "1.000", "compound_taxes_info": "[]", "s_h_amount": "0.00000000",
            "adjustment": "0.00000000", "discount_amount": None, "spcompany": "Default", **more}


def fixture_sql():
    s = [
        insert("vtiger_users", id=U_ADMIN, user_name=ADMIN_NAME, last_name=f"{PREFIX} admin", is_admin="on",
               status="Active", currency_id=1, deleted=0),
        insert("vtiger_users", id=U_SALES, user_name=f"synth-fin-{HEX}-sales", last_name=f"{PREFIX} sales",
               is_admin="off", status="Active", currency_id=1, imagename="avatar.png", deleted=0),
        insert("vtiger_user2role", userid=U_ADMIN, roleid="H2"), insert("vtiger_user2role", userid=U_SALES, roleid="H4"),
        entity(A1, "Accounts"),
        insert("vtiger_account", accountid=A1, account_no="КОНТР_1", accountname=f"{PREFIX} A1"),
        insert("vtiger_accountscf", accountid=A1), insert("vtiger_accountbillads", accountaddressid=A1),
        insert("vtiger_accountshipads", accountaddressid=A1),
        *[x for cid, image in ((C1, "photo.png"), (C2, "lost.png")) for x in (
            entity(cid, "Contacts"),
            insert("vtiger_contactdetails", contactid=cid, contact_no=f"КОНТАКТ_{cid}", accountid=A1,
                   lastname=f"{PREFIX} C{cid}", imagename=image),
            insert("vtiger_contactaddress", contactaddressid=cid), insert("vtiger_contactsubdetails", contactsubscriptionid=cid),
            insert("vtiger_contactscf", contactid=cid), insert("vtiger_customerdetails", customerid=cid))],
        entity(O1, "Potentials"),
        insert("vtiger_potential", potentialid=O1, potential_no="СДЕЛКА_1", related_to=A1, potentialname=f"{PREFIX} O1"),
        # catalogues
        entity(V1, "Vendors"),
        insert("vtiger_vendor", vendorid=V1, vendor_no="ПОСТ_1", vendorname=f"{PREFIX} V1", website="https://example.com"),
        insert("vtiger_vendorcf", vendorid=V1, cf_1206="000"),
        entity(S1, "Services", description=f"{PREFIX} услуга"),
        insert("vtiger_service", serviceid=S1, service_no="СЕР_1", servicename=f"{PREFIX} S1", servicecategory="Поддержка",
               qty_per_unit="1.00", unit_price="1000.00000000", discontinued=1, service_usageunit="Часы", currency_id=1),
        insert("vtiger_servicecf", serviceid=S1, cf_billable_time_tracker="1"),
        entity(P1, "Products"),
        insert("vtiger_products", productid=P1, product_no="ТОВ_1", productname=f"{PREFIX} P1", productcode="P-1",
               discontinued=0, unit_price="30.00000000", usageunit="Each", currency_id=1),
        insert("vtiger_productcf", productid=P1),
        insert("vtiger_crmentityrel", crmid=O1, module="Potentials", relcrmid=S1, relmodule="Services"),
    ]
    s += document("Quotes", Q1, ("vtiger_quotes", "quoteid"),
                  header("quote_no", "ПРЕД_9001", potentialid=O1, quotestage="Принято", inventorymanager=U_SALES,
                         subtotal="200.00000000", pre_tax_total="200.00000000", total="200.00000000", region_id=None,
                         terms_conditions=f"{PREFIX} условия"),
                  [(L1, S1, "2.000", "100.00000000", {"tax1": "18.000", "margin": "0.00000000"})],
                  "vtiger_quotesbillads", "vtiger_quotesshipads", ("vtiger_quotescf", "quoteid"))
    s += document("SalesOrder", SO1, ("vtiger_salesorder", "salesorderid"),
                  header("salesorder_no", "ЗАКАЗ_9001", potentialid=O1, sostatus="Одобрено", subtotal="50.00000000",
                         pre_tax_total="50.00000000", total="50.00000000", region_id=0, enable_recurring=1),
                  [(L2, S1, "1.000", "50.00000000", {"margin": "50.00000000"})],
                  "vtiger_sobillads", "vtiger_soshipads", ("vtiger_salesordercf", "salesorderid"))
    s.append(insert("vtiger_invoice_recurring_info", salesorderid=SO1, recurring_frequency="Monthly"))
    s += document("Act", ACT1, ("vtiger_sp_act", "actid"),
                  header("act_no", "9001", sp_actstatus="Created", actdate="2024-01-11", subtotal="100.00000000",
                         pre_tax_total="100.00000000", total="100.00000000", region_id=0),
                  [(L3, S1, "1.000", "100.00000000", {"margin": "100.00000000"})],
                  "vtiger_sp_actbillads", "vtiger_sp_actshipads", ("vtiger_sp_actcf", "actid"))
    s += document("Invoice", I1, ("vtiger_invoice", "invoiceid"),
                  header("invoice_no", "С-9001", invoicestatus="Paid", invoicedate="2024-01-10", duedate="2024-01-20",
                         salesorderid=SO1, sp_act_id=ACT1, potential_id=str(O1), balance="140.00000000",
                         received="0.00000000", subtotal="140.00000000", pre_tax_total="140.00000000",
                         total="140.00000000", region_id=0, spcompany="По умолчанию", terms_conditions=f"{PREFIX} т"),
                  [(L4, S1, "1.500", "80.00000000", {"margin": "120.00000000", "comment": f"{PREFIX} часы"}),
                   (L5, P1, "1.000", "30.00000000", {"discount_amount": "10.00000000", "margin": "20.00000000"})],
                  "vtiger_invoicebillads", "vtiger_invoiceshipads", ("vtiger_invoicecf", "invoiceid"))
    # a rounding discrepancy: the exact line net is 0.4995, the stored totals 0.50 (TotalCheck::Rounded)
    s += document("Invoice", I2, ("vtiger_invoice", "invoiceid"),
                  header("invoice_no", "СЧЕТ_9002", invoicestatus="", invoicedate="2024-02-01", balance="0.50000000",
                         subtotal="0.50000000", pre_tax_total="0.50000000", total="0.50000000", region_id=0,
                         spcompany=""),
                  [(L6, S1, "1.500", "0.33300000", {"margin": "0.49950000"})],
                  "vtiger_invoicebillads", "vtiger_invoiceshipads", ("vtiger_invoicecf", "invoiceid"))
    s += [
        # payments: every D-11 category
        *[x for pay, ptype, related, amount, status, payer in (
            (PAY1, "Приход", I1, "140.00000000", "Executed", A1), (PAY2, "Приход", I1, "10.00000000", "", A1),
            (PAY3, "Expense", 0, "5.00000000", "Executed", V1), (PAY4, "Приход", SO1, "50.00000000", "Executed", A1),
            (PAY5, "Приход", 0, "1.00000000", "Executed", C1)) for x in (
            entity(pay, "SPPayments"),
            insert("sp_payments", payid=pay, pay_no=str(pay - VT), pay_date="2024-01-15", pay_type=ptype, payer=payer,
                   related_to=related, type_payment="Cashless Transfer", amount=amount, spstatus=status,
                   spcompany="", doc_no=0),
            insert("sp_paymentscf", payid=pay, cf_1380="0"))],
        insert("vtiger_crmentityrel", crmid=I1, module="Invoice", relcrmid=PAY1, relmodule="SPPayments"),  # same
        insert("vtiger_crmentityrel", crmid=I2, module="Invoice", relcrmid=PAY2, relmodule="SPPayments"),  # conflict
        insert("vtiger_crmentityrel", crmid=I2, module="Invoice", relcrmid=PAY3, relmodule="SPPayments"),  # Q-36
        insert("vtiger_crmentityrel", crmid=A1, module="Accounts", relcrmid=I1, relmodule="Invoice"),      # duplicate
        # documents: internal with a file, external URL, internal without a file (D-23)
        insert("vtiger_attachmentsfolder", folderid=FD, foldername=f"{PREFIX} папка", createdby=U_SALES, sequence=1),
        entity(D1, "Documents"),
        insert("vtiger_notes", notesid=D1, note_no="ДОК_1", title=f"{PREFIX} D1", filename=FILES[AT1][0], folderid=FD,
               filetype=FILES[AT1][1], filelocationtype="I", filestatus=1, filesize=FILES[AT1][2], filedownloadcount=3),
        insert("vtiger_notescf", notesid=D1),
        entity(D2, "Documents"),
        insert("vtiger_notes", notesid=D2, note_no="ДОК_2", title=f"{PREFIX} D2", filename="https://example.com/synth",
               folderid=FD, filelocationtype="E", filestatus=1, filesize=0),
        insert("vtiger_notescf", notesid=D2),
        entity(D3, "Documents"),
        insert("vtiger_notes", notesid=D3, note_no="ДОК_3", title=f"{PREFIX} D3", filename="gone.pdf", folderid=FD,
               filelocationtype="I", filestatus=0, filesize=10),
        insert("vtiger_notescf", notesid=D3),
        insert("vtiger_senotesrel", crmid=A1, notesid=D1), insert("vtiger_senotesrel", crmid=I1, notesid=D1),
        insert("vtiger_senotesrel", crmid=ACT1, notesid=D1), insert("vtiger_senotesrel", crmid=C1, notesid=D2),
        # knowledge base, a comment on it with a file
        entity(F1, "Faq"),
        insert("vtiger_faq", id=F1, faq_no="БЗ_1", product_id="0", question=f"{PREFIX} вопрос?", answer="<p>ответ</p>",
               category="General", status="Reviewed"),
        insert("vtiger_faqcf", faqid=F1),
        insert("vtiger_freetags", id=VT + 991, tag="synth-faq", raw_tag="synth-faq"),
        insert("vtiger_freetagged_objects", tag_id=VT + 991, tagger_id=U_SALES, object_id=F1, module="Faq"),
        entity(N1, "ModComments", created="2023-07-01 12:00:00"),
        insert("vtiger_modcomments", modcommentsid=N1, commentcontent=f"{PREFIX} N1", related_to=F1, userid=U_SALES,
               filename=str(AT2), customer=0),
        insert("vtiger_modcommentscf", modcommentsid=N1),
        # an archived e-mail with a file and a tracked recipient
        entity(EM1, "Emails", description="<p>письмо</p>"),
        insert("vtiger_activity", activityid=EM1, subject=f"{PREFIX} EM1", activitytype="Emails",
               date_start="2019-03-01", time_start="10:00", semodule="Potentials", notime="0", sendnotification="0",
               visibility="all"),
        insert("vtiger_emaildetails", emailid=EM1, from_email=f"synth-{HEX}@example.com",
               to_email=json.dumps([f"Synth-To-{HEX}@Example.com"]), cc_email="[]", bcc_email="[]",
               idlists=f"{O1}@-1|", email_flag="SENT"),
        insert("vtiger_seactivityrel", crmid=O1, activityid=EM1),
        insert("vtiger_email_track", crmid=O1, mailid=EM1, access_count=0, click_count=0),
        # archives
        entity(CS1, "Consignment"),
        insert("vtiger_sp_consignment", consignmentid=CS1, consignment_no="1", subject=f"{PREFIX} CS1", invoiceid=I1,
               accountid=A1, total="30.00000000", compound_taxes_info="[]"),
        insert("vtiger_sp_consignmentcf", consignmentid=CS1),
        insert("vtiger_sp_consignmentbillads", consignmentbilladdressid=CS1),
        insert("vtiger_sp_consignmentshipads", consignmentshipaddressid=CS1),
        insert("vtiger_inventoryproductrel", id=CS1, productid=P1, sequence_no=1, quantity="1.000",
               listprice="30.00000000", lineitem_id=L7, margin="30.00000000"),
        insert("vtiger_crmentityrel", crmid=I1, module="Invoice", relcrmid=CS1, relmodule="Consignment"),
        entity(J1, "Jivosite"), insert("vtiger_jivosite", jivositeid=J1, chatid=5, messages="1"),
        insert("vtiger_jivositecf", jivositeid=J1),
        entity(M1, "JVmes"), insert("vtiger_jvmes", jvmesid=M1, message=f"{PREFIX} привет", relatedjivo=str(J1)),
        insert("vtiger_jvmescf", jvmesid=M1),
        entity(AS1, "Assets"), insert("vtiger_assets", assetsid=AS1, asset_no="1", assetname=f"{PREFIX} AS1",
                                      account=A1, product=P1),
        insert("vtiger_assetscf", assetsid=AS1),
        entity(SC1, "ServiceContracts"),
        insert("vtiger_servicecontracts", servicecontractsid=SC1, subject=f"{PREFIX} SC1", contract_no="1",
               sc_related_to=A1),
        insert("vtiger_servicecontractscf", servicecontractsid=SC1),
    ]
    # files of the attachments
    for att, setype, owner, table in (
            (AT1, "Documents Attachment", D1, "vtiger_seattachmentsrel"),
            (AT2, "ModComments Attachment", N1, "vtiger_seattachmentsrel"),
            (AT3, "Emails Attachment", EM1, "vtiger_seattachmentsrel"),
            (AT_PHOTO, "Contacts Image", C1, "vtiger_seattachmentsrel"),
            (AT_AVATAR, "Users Image", U_SALES, "vtiger_salesmanattachmentsrel")):
        name, mime, _size = FILES[att]
        s += [entity(att, setype), insert("vtiger_attachments", attachmentsid=att, name=name, type=mime,
                                          path="storage/2020/January/week1/")]
        s.append(insert(table, **({"crmid": owner} if table == "vtiger_seattachmentsrel" else {"smid": owner}),
                        attachmentsid=att))
    return s


def source_sql(script):
    return Mysql.stand(database=SOURCE).lines("SET SESSION sql_log_bin=0;\n" + script + "\n", ROOT / "source.log")


def sql(query):
    return [line.decode("utf-8").split("\t") for line in
            Mysql.stand(database="espocrm").lines(query + "\n", ROOT / "stand.log")]


def one(query):
    rows = sql(query)
    return rows[0] if rows else None


def as_stand(*command):
    return subprocess.run(["bash", "-c", f'source {REPO}/scripts/stand/lib.sh && as_user "$ESPO_USER" "$@"', "-",
                           *command], cwd=REPO, capture_output=True, check=True).stdout


class Stage063(unittest.TestCase):
    runs = []

    @classmethod
    def setUpClass(cls):
        global ROOT, SOURCE
        lock = open(Path(tempfile.gettempdir()) / "itvolga-stage06_2-test.lock", "w")  # shared with 06.2 (same stand)
        fcntl.flock(lock, fcntl.LOCK_EX)
        cls.addClassCleanup(lock.close)
        ROOT = Path(tempfile.mkdtemp(prefix="vtimp063-test-"))
        cls.addClassCleanup(lambda: cls.cleaned and shutil.rmtree(ROOT, True))
        cls.cleaned = False
        taken = sum(int(one(f"SELECT COUNT(*) FROM `{t}` WHERE vtiger_id BETWEEN {KEYS[0]} AND {KEYS[1]}")[0])
                    for t in TABLES.values())
        assert taken == 0, "the random key block is in use: run again"
        cls.temp = verify.TempDatabases(ROOT, ROOT)
        SOURCE = cls.temp.create("vtiger7", "utf8mb4", "utf8mb4_0900_ai_ci")
        cls.addClassCleanup(cls.temp.drop_all)
        columns = {**COLUMNS_063, **COLUMNS_062}
        columns["vtiger_activity"] += ", " + ACTIVITY_EXTRA
        columns["vtiger_contactdetails"] += "" if "imagename" in columns["vtiger_contactdetails"] else ", imagename TEXT"
        columns["vtiger_freetags"] += ", raw_tag VARCHAR(50)"
        source_sql("\n".join(f"CREATE TABLE `{t}` ({c}) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;" for t, c in columns.items()))
        source_sql("\n".join(fixture_sql()))
        cls.files = ROOT / "files"
        cls.bytes = {}
        for att, (name, _mime, size) in FILES.items():
            path = cls.files / "storage/2020/January/week1" / f"{att}_{name}"
            path.parent.mkdir(parents=True, exist_ok=True)
            data = secrets.token_bytes(size)
            path.write_bytes(data)
            cls.bytes[att] = data
        cls.preexisting = {t: {r[0] for r in sql(f"SELECT id FROM {t}")}
                           for t in ("email_address", "phone_number", "knowledge_base_category")}
        cls.client = Client(*admin_credentials())
        cls.created = []
        cls.addClassCleanup(cls.cleanup)
        status, body, _ = cls.client.post("User", {"userName": ADMIN_NAME, "lastName": PREFIX, "type": "admin",
                                                   "password": secrets.token_urlsafe(16)})
        assert status == 200, status
        cls.created.append(("User", body["id"]))

    @classmethod
    def run_import(cls, check_only=False, only=ONLY, files_root=None):
        rundir = ROOT / f"run-{len(cls.runs)}"
        rundir.mkdir()
        report = importer.execute(rundir, source_db=SOURCE, only=only, check_only=check_only, adopt=ADMIN_NAME,
                                  key_range=KEYS, effective_admin=U_ADMIN, files_root=files_root or cls.files)
        recs = [json.loads(line) for line in (rundir / "records.jsonl").read_text().splitlines()]
        cls.runs.append(recs)
        return report, {r["key"]: r for r in recs}, rundir

    @classmethod
    def cleanup(cls):
        """Hard delete of exactly the records of this test (ids of the run records, the journals and the API calls),
        their junction rows and the stored files of their attachments."""
        ids = {}
        for recs in cls.runs:
            for r in recs:
                if r.get("id"):
                    ids.setdefault(r["key"].split(":")[0], set()).add(r["id"])
        for journal in ROOT.glob("run-*/applied.jsonl"):
            for line in journal.read_text().splitlines():
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                ids.setdefault(rec["key"].split(":")[0], set()).add(rec["id"])
        for etype, eid in cls.created:
            ids.setdefault(etype, set()).add(eid)
        categories = ids.pop("KnowledgeBaseCategory", set()) - cls.preexisting["knowledge_base_category"]
        all_ids = sorted({i for s in ids.values() for i in s} | categories)
        if not all_ids:
            cls.cleaned = True
            return
        listed = ",".join("'" + i + "'" for i in all_ids)
        # shared address/number rows: only those linked to this test's records, new since setUp, not used elsewhere
        shared = {}
        for table, links in (("email_address", (("entity_email_address", "entity_id"), ("email_email_address", "email_id"))),
                             ("phone_number", (("entity_phone_number", "entity_id"),))):
            linked = set()
            for link, owner in links:
                column = "email_address_id" if table == "email_address" else "phone_number_id"
                linked |= {r[0] for r in sql(f"SELECT {column} FROM {link} WHERE {owner} IN ({listed})")}
            shared[table] = sorted(linked - cls.preexisting[table])
        columns = {}
        for table, column in sql("SELECT table_name, column_name FROM information_schema.columns WHERE table_schema = "
                                 f"'espocrm' AND table_name IN ({','.join(chr(39) + t + chr(39) for t in JUNCTIONS)}) "
                                 "AND (column_name LIKE '%\\_id' OR column_name = 'id')"):
            columns.setdefault(table, []).append(column)
        script = []
        for table, cols in columns.items():
            cols = [c for c in cols if c != "id" or table in ("preferences", "user_data")]
            script.append(f"DELETE FROM `{table}` WHERE " + " OR ".join(f"`{c}` IN ({listed})" for c in cols) + ";")
        script.append(f"DELETE FROM note WHERE parent_id IN ({listed}) OR related_id IN ({listed});")
        for table, row_ids in shared.items():
            if row_ids:
                rows = ",".join("'" + i + "'" for i in row_ids)
                users = ("entity_email_address", "email_email_address") if table == "email_address" else (
                    "entity_phone_number",)
                column = "email_address_id" if table == "email_address" else "phone_number_id"
                script.append(f"DELETE FROM {table} WHERE id IN ({rows})" + "".join(
                    f" AND id NOT IN (SELECT {column} FROM {u})" for u in users) + ";")
        for etype, table in TABLES.items():
            if ids.get(etype):
                script.append(f"DELETE FROM `{table}` WHERE id IN ({','.join(chr(39) + i + chr(39) for i in sorted(ids[etype]))});")
        if categories:
            script.append(f"DELETE FROM knowledge_base_category_path WHERE ascendor_id IN ({listed}) OR descendor_id IN "
                          f"({listed}); DELETE FROM knowledge_base_category WHERE id IN ({listed});")
        Mysql.stand(database="espocrm").lines("\n".join(script) + "\n", ROOT / "cleanup.log")
        for att in sorted(ids.get("Attachment", ())):
            as_stand("rm", "-f", f"data/upload/{att}")
        cls.cleaned = True

    def id_of(self, table, key):
        row = one(f"SELECT id FROM `{table}` WHERE vtiger_id = {key} AND deleted = 0")
        return row[0] if row else None

    # --- scenarios (in order) ----------------------------------------------------------------------------------

    def test_00_dry_run_before_the_first_import(self):
        report, recs, _ = self.run_import(check_only=True)
        self.assertEqual(report["problems"], {}, report.get("problem_columns"))
        self.assertEqual({r["check"] for k, r in recs.items() if not r["held"]  # the category may exist (real import)
                          and not k.startswith("KnowledgeBaseCategory:")} - {"absent"}, {"missing"})

    def test_01_full_import(self):
        report, recs, rundir = self.run_import()
        self.assertEqual(report["problems"], {}, report.get("problem_columns"))
        self.assertEqual(report["status"], "findings")
        self.assertEqual({r["check"] for r in recs.values() if not r["held"]} - {"absent"}, {"equal"})
        self.assertEqual(set(report["silence"].values()), {0})
        f = report["findings"]
        self.assertEqual(f.get("discrepancy:invoice_act_total"), 1)       # I1 140 vs ACT1 100
        self.assertEqual(f.get("discrepancy:rounding"), 1)                # I2: 0.4995 → 0.50
        self.assertEqual(report["aggregates"]["writer"]["unequal"], 0)
        self.assertEqual(report["aggregates"]["reader"]["unequal"], 0)
        self.assertEqual(report["files"]["stored_and_downloaded"], 5)
        self.assertEqual(report["files"]["accepted_losses"], 2)            # C2 photo name, D3 without a file
        aggregates = json.loads((rundir / "aggregates.json").read_text())
        for side in ("reader", "writer"):                                  # D-11 in source SQL = plan = stand SQL
            measures = {r["measure"]: r for r in aggregates[side]}
            self.assertEqual(Decimal(measures["PaymentAllocation.invoice.amount"]["left"]), Decimal("150"), side)
            self.assertEqual(Decimal(measures["PaymentAllocation.salesOrder.count"]["left"]), 1, side)
        cats = report["finance"]["allocations"]
        for category in ("both_same_invoice:allocate", "conflict_rel_other_invoice:allocate", "rel_only:none",
                         "related_to_salesorder:allocate", "unallocated:none"):
            self.assertEqual(cats.get(category), 1, category)
        discrepancies = [json.loads(x) for x in (rundir / "discrepancies.jsonl").read_text().splitlines()]
        rounding = [d for d in discrepancies if d["kind"] == "rounding"]
        self.assertEqual(rounding[0]["reasons"], ["rounded_to_kopecks"])
        self.assertEqual(Decimal(rounding[0]["expected"]["subtotal"]), Decimal("0.4995"))

    def test_02_values(self):
        i1 = one(f"SELECT number, status, date_invoiced, subtotal, grand_total, balance_source, totals_check, "
                 f"source_formula, paid_amount, settlement_state, legal_entity_id, sales_order_id, act_id, "
                 f"opportunity_id, terms_and_conditions IS NOT NULL, subtotal_currency FROM invoice "
                 f"WHERE vtiger_id = {I1}")
        self.assertEqual(i1[:8], ["С-9001", "Paid", "2024-01-10", "140.00000000", "140.00000000", "140.00000000",
                                  "exact", "noLineTax"])
        self.assertEqual((i1[8], i1[9]), ("150.00000000", "overpaid"))   # 140 Executed + 10 without status (Q-37)
        default = one("SELECT id FROM legal_entity WHERE vtiger_company_key = 'Default' AND deleted = 0")[0]
        self.assertEqual(i1[10], default)                                   # «По умолчанию» → the single entity
        self.assertEqual((i1[11], i1[12], i1[13]), (self.id_of("sales_order", SO1), self.id_of("act", ACT1),
                                                     self.id_of("opportunity", O1)))
        self.assertEqual((i1[14], i1[15]), ("1", "RUB"))
        i2 = one(f"SELECT status, totals_check, expected_subtotal, number FROM invoice WHERE vtiger_id = {I2}")
        self.assertEqual(i2, ["NULL", "rounded", "0.49950000", "СЧЕТ_9002"])
        items = {int(r[0]): r[1:] for r in sql(
            f"SELECT vtiger_id, amount, margin, discount_amount, `order`, quantity, name FROM invoice_item "
            f"WHERE vtiger_id IN ({L4}, {L5}, {L6})")}
        self.assertEqual(items[L4][:5], ["120.00000000", "120.00000000", "NULL", "1", "1.500"])
        self.assertEqual(items[L5][:4], ["20.00000000", "20.00000000", "10.00000000", "2"])
        self.assertEqual(items[L6][0], "0.49950000")                          # exact net, never rounded
        self.assertEqual(items[L4][5], f"{PREFIX} S1")
        quote = one(f"SELECT status, source_formula, inventory_manager_id IS NOT NULL FROM quote WHERE vtiger_id = {Q1}")
        self.assertEqual(quote, ["Accepted", "lineTaxNotApplied", "1"])
        self.assertEqual(one(f"SELECT tax_rate FROM quote_item WHERE vtiger_id = {L1}")[0], "18.000")
        self.assertEqual(one(f"SELECT status, paid_amount, settlement_state FROM sales_order WHERE vtiger_id = {SO1}"),
                         ["Approved", "50.00000000", "paid"])
        allocations = {int(r[0]): r[1:] for r in sql(
            f"SELECT vtiger_id, invoice_id, sales_order_id, amount, source, source_conflict, vtiger_data "
            f"FROM payment_allocation WHERE vtiger_id BETWEEN {PAY1} AND {PAY5} AND deleted = 0")}
        self.assertEqual(set(allocations), {PAY1, PAY2, PAY4})
        self.assertEqual(allocations[PAY2][:5], [self.id_of("invoice", I1), "NULL", "10.00000000", "relatedTo", "1"])
        self.assertEqual(json.loads(allocations[PAY2][5])["conflictInvoiceIds"], [I2])
        self.assertEqual(allocations[PAY4][1], self.id_of("sales_order", SO1))
        pay3 = one(f"SELECT direction, vtiger_data, payer_type FROM payment WHERE vtiger_id = {PAY3}")
        self.assertEqual((pay3[0], json.loads(pay3[1])["invoiceLinks"], pay3[2]), ("outgoing", [I2], "Vendor"))
        # documents, files, knowledge base, e-mail, archives
        doc = self.id_of("document", D1)
        self.assertEqual(one(f"SELECT a.vtiger_id, a.related_type, a.field FROM document d JOIN attachment a ON a.id = "
                             f"d.file_id WHERE d.id = '{doc}'"), [str(AT1), "Document", "file"])
        for table, column, key in (("account_document", "account_id", ("account", A1)),
                                   ("invoice_document", "invoice_id", ("invoice", I1)),
                                   ("act_document", "act_id", ("act", ACT1))):
            self.assertEqual(one(f"SELECT COUNT(*) FROM {table} WHERE document_id = '{doc}' AND {column} = "
                                 f"'{self.id_of(*key)}' AND deleted = 0")[0], "1", table)
        self.assertEqual(one(f"SELECT c_external_url, file_id FROM document WHERE vtiger_id = {D2}"),
                         ["https://example.com/synth", "NULL"])
        self.assertEqual(one(f"SELECT file_id FROM document WHERE vtiger_id = {D3}")[0], "NULL")
        kb = self.id_of("knowledge_base_article", F1)
        self.assertEqual(one(f"SELECT c.name FROM knowledge_base_article_knowledge_base_category r JOIN "
                             f"knowledge_base_category c ON c.id = r.knowledge_base_category_id WHERE "
                             f"r.knowledge_base_article_id = '{kb}' AND r.deleted = 0")[0], "Общее")
        self.assertEqual(one(f"SELECT status, c_tags FROM knowledge_base_article WHERE id = '{kb}'"),
                         ["In Review", '["synth-faq"]'])
        note = one(f"SELECT id, parent_type, parent_id FROM note WHERE vtiger_id = {N1}")
        self.assertEqual(note[1:], ["KnowledgeBaseArticle", kb])
        self.assertEqual(one(f"SELECT parent_type, parent_id, field FROM attachment WHERE vtiger_id = {AT2}"),
                         ["Note", note[0], "attachments"])
        email = one(f"SELECT id, status, parent_type, parent_id, has_attachment, date_sent FROM email WHERE vtiger_id = {EM1}")
        self.assertEqual(email[1:5], ["Sent", "Opportunity", self.id_of("opportunity", O1), "1"])
        self.assertEqual(one(f"SELECT parent_id FROM attachment WHERE vtiger_id = {AT3}")[0], email[0])
        self.assertEqual(one(f"SELECT COUNT(*) FROM email_user WHERE email_id = '{email[0]}' AND is_read = 0")[0], "0")
        self.assertEqual(one(f"SELECT c_photo_id = (SELECT id FROM attachment WHERE vtiger_id = {AT_PHOTO}) FROM contact "
                             f"WHERE vtiger_id = {C1}")[0], "1")
        self.assertEqual(json.loads(one(f"SELECT vtiger_data FROM contact WHERE vtiger_id = {C2}")[0])["imagename"],
                         "lost.png")
        self.assertEqual(one(f"SELECT avatar_id = (SELECT id FROM attachment WHERE vtiger_id = {AT_AVATAR}) FROM user "
                             f"WHERE vtiger_id = {U_SALES}")[0], "1")
        cs = one(f"SELECT invoice_id, account_id, data FROM vtiger_archive WHERE vtiger_id = {CS1}")
        self.assertEqual(cs[:2], [self.id_of("invoice", I1), self.id_of("account", A1)])
        self.assertEqual(json.loads(cs[2])["lines"][0]["lineitem_id"], str(L7))
        self.assertEqual(one(f"SELECT parent_archive_id FROM vtiger_archive WHERE vtiger_id = {M1}")[0],
                         self.id_of("vtiger_archive", J1))
        self.assertEqual(one(f"SELECT type, unit, category, is_active FROM product WHERE vtiger_id = {S1}"),
                         ["service", "Hours", "Support", "1"])
        self.assertEqual(one(f"SELECT COUNT(*) FROM c_opportunity_product WHERE opportunity_id = '{self.id_of('opportunity', O1)}'"
                             f" AND product_id = '{self.id_of('product', S1)}' AND deleted = 0")[0], "1")
        stored = as_stand("sha256sum", f"data/upload/{one(f'SELECT id FROM attachment WHERE vtiger_id = {AT1}')[0]}")
        self.assertEqual(stored.split()[0].decode(), hashlib.sha256(self.bytes[AT1]).hexdigest())

    def test_03_rerun_writes_nothing(self):
        before = self.fingerprint()
        report, recs, _ = self.run_import()
        self.assertEqual(report["problems"], {})
        self.assertEqual({r["apply"] for r in recs.values() if not r["held"]} - {"skipped"}, {"unchanged"})
        self.assertEqual(self.fingerprint(), before)
        self.assertTrue(all("(unchanged)" in k for k in report["finance"]["verify"]), report["finance"]["verify"])

    def fingerprint(self):
        rows = []
        for etype, table in TABLES.items():
            rows += sql(f"SELECT '{table}', id, IFNULL(modified_at, ''), "
                        + ("IFNULL(version_number, '')" if etype in ("Quote", "SalesOrder", "Invoice", "Act", "Payment")
                           else "''") + f" FROM `{table}` WHERE vtiger_id BETWEEN {KEYS[0]} AND {KEYS[1]} ORDER BY id")
        files = as_stand("bash", "-c", "cd data/upload && stat -c '%n %s %Y' * | sort")
        return rows, hashlib.sha256(files).hexdigest()

    def test_04_recalculated_document_keeps_its_calculation(self):
        invoice = self.id_of("invoice", I1)
        status, body, _ = self.client.get(f"Invoice/{invoice}")
        self.assertEqual(status, 200)
        items = body["itemList"]
        items[0]["quantity"] = "2"                                             # a calculation edit (D-51)
        for item in items:
            item["taxRate"] = "0"
        status, _b, _ = self.client.put(f"Invoice/{invoice}", {"itemList": items})
        self.assertEqual(status, 200)
        recalculated = one(f"SELECT subtotal, vtiger_data FROM invoice WHERE id = '{invoice}'")
        self.assertIn("sourceTotals", json.loads(recalculated[1]))
        source_sql(f"UPDATE vtiger_invoice SET invoicestatus = 'Sent' WHERE invoiceid = {I1};")  # the source changes
        report, recs, _ = self.run_import()
        self.assertEqual(report["problems"], {}, report.get("problem_columns"))
        self.assertGreaterEqual(report["findings"].get("recalculated_in_target", 0), 1)
        after = one(f"SELECT status, subtotal, vtiger_data FROM invoice WHERE id = '{invoice}'")
        self.assertEqual(after[0], "Sent")                                     # source wins on the rest
        self.assertEqual(after[1], recalculated[0])                            # calculation stays as recalculated
        self.assertIn("sourceTotals", json.loads(after[2]))
        self.assertEqual(recs[f"InvoiceItem:{L4}"]["check"], "protected")

    def test_05_deleted_finance_record_is_not_restored(self):
        invoice = self.id_of("invoice", I2)
        status, _b, _ = self.client.delete(f"Invoice/{invoice}")
        self.assertEqual(status, 200)
        report, recs, _ = self.run_import()
        self.assertEqual(report["problems"], {}, report.get("problem_columns"))
        self.assertEqual(recs[f"Invoice:{I2}"]["check"], "deleted_in_target")
        self.assertEqual(recs[f"InvoiceItem:{L6}"]["check"], "deleted_in_target")
        self.assertEqual(one(f"SELECT deleted FROM invoice WHERE id = '{invoice}'")[0], "1")
        self.assertGreaterEqual(report["findings"].get("deleted_in_target", 0), 2)

    def test_06_corrupted_stored_file_is_found_and_repaired(self):
        att = one(f"SELECT id FROM attachment WHERE vtiger_id = {AT2}")[0]
        as_stand("bash", "-c", f"printf x >> data/upload/{att}")
        report, recs, _ = self.run_import(check_only=True)
        self.assertIn("file_check_differs", report["problems"])
        self.assertEqual(recs[f"Attachment:{AT2}"]["file"], "differs")
        report, recs, _ = self.run_import()
        self.assertEqual(report["problems"], {}, report.get("problem_columns"))
        stored = as_stand("sha256sum", f"data/upload/{att}").split()[0].decode()
        self.assertEqual(stored, hashlib.sha256(self.bytes[AT2]).hexdigest())

    def test_07_wrong_bytes_are_refused(self):
        op = spec.Op("Attachment", VT + 998, "Attachments", attributes={"name": "x", "type": "text/plain",
                                                                         "role": "Attachment"})
        op.owner = {"entityType": "Document", "key": D1, "field": "file"}
        op.file = {"size": FILES[AT2][2], "sha256": "0" * 64}
        op.file_ref = os.fsencode(f"storage/2020/January/week1/{AT2}_{FILES[AT2][0]}")
        results, _stray = importer.bridge([op], "apply", ADMIN_NAME, ROOT, files=importer.F.DirectoryFiles(self.files))
        if results[op.key].get("id"):                                          # a wrongly accepted file is cleaned too
            self.created.append(("Attachment", results[op.key]["id"]))
        self.assertEqual(results[op.key].get("error"), "file_hash")
        self.assertIsNone(one(f"SELECT id FROM attachment WHERE vtiger_id = {VT + 998}"))
        self.assertNotIn(b".itvolga-import-", as_stand("ls", "-a", "data/upload"))

    def test_08_allocation_parity_with_the_core(self):
        """The Python port of the D-11 rule answers as SourceAllocationResolver on every shape."""
        crm = {101: ("Invoice", False), 102: ("Invoice", False), 103: ("SalesOrder", False), 104: ("Invoice", True),
               105: ("Accounts", False)}
        cases = []
        for direction in ("incoming", "outgoing"):
            for related in (0, 101, 103, 104, 105):
                for links in ([], [101], [102], [101, 102]):
                    for amount in ("10.00", "0.00"):
                        cases.append({"id": len(cases) + 1, "direction": direction, "amount": amount,
                                      "relatedToId": related, "relatedToType": crm.get(related, ("", False))[0],
                                      "relatedToDeleted": crm.get(related, ("", False))[1], "linkedInvoiceIds": links})
        php = subprocess.run(["bash", "-c", f"source {REPO}/scripts/stand/lib.sh && echo $PHP_BIN"],
                             capture_output=True, text=True, check=True).stdout.strip()
        out = subprocess.run(["sudo", "-n", "-u", "espocrm", "env", f"ESPO_ROOT={REPO}", php, "--", json.dumps(cases)],
                             input=(Path(__file__).parent / "allocation_parity.php").read_text(), capture_output=True,
                             text=True, check=True).stdout
        core = json.loads(out.strip().splitlines()[-1])

        class Ctx:
            pass
        ctx = Ctx()
        ctx.crm = crm
        for case, expected in zip(cases, core):
            payment = spec.Op("Payment", case["id"], "SPPayments", attributes={"direction": case["direction"],
                                                                                "amount": case["amount"]})
            row = {"sp_payments.related_to": str(case["relatedToId"])}
            category, decision, target, conflicts, _reason = spec_finance.resolve_allocation(
                payment, row, case["linkedInvoiceIds"], ctx)
            self.assertEqual((category, decision), (expected["category"], expected["decision"]), case)
            if decision == "allocate":
                self.assertEqual(list(target), [expected["candidateType"], expected["candidateId"]], case)
                self.assertEqual(conflicts, expected["conflicts"], case)

    def test_09_recalculation_committed_during_the_import_is_kept(self):
        """A recalculation that commits while the import waits to write the same document keeps its calculation: the
        import locks the document before its first read (FinanceRules::lock), as DocumentProcessor does."""
        quote = self.id_of("quote", Q1)
        before = one(f"SELECT adjustment FROM quote WHERE id = '{quote}'")[0]
        source_sql(f"UPDATE vtiger_quotes SET adjustment = adjustment + 1, total = total + 1 WHERE quoteid = {Q1};")
        argv = Mysql.stand(database="espocrm").argv
        user = subprocess.Popen(argv[:4] + ["--unbuffered"] + argv[4:], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, bufsize=0)
        user.stdin.write(f"BEGIN; SELECT id FROM quote WHERE id = '{quote}' FOR UPDATE; UPDATE quote SET grand_total = "
                         f"4242.42, vtiger_data = JSON_SET(vtiger_data, '$.sourceTotals', JSON_OBJECT('synthetic', 1)) "
                         f"WHERE id = '{quote}'; SELECT 'locked';\n".encode())
        while user.stdout.readline().strip() != b"locked":
            pass
        result = {}
        run = threading.Thread(target=lambda: result.update(run=self.run_import()))
        run.start()
        waited, deadline = False, time.time() + 300
        while not waited and run.is_alive() and time.time() < deadline:   # the import waits for the user's lock
            waited = one("SELECT COUNT(*) FROM information_schema.innodb_trx WHERE trx_state = 'LOCK WAIT'")[0] != "0"
            time.sleep(0.2)
        user.stdin.write(b"COMMIT;\n")
        user.stdin.close()
        user.wait()
        user.stdout.close()
        run.join()
        self.assertTrue(waited)
        report, recs, _ = result["run"]
        self.assertEqual(report["problems"], {}, report.get("problem_columns"))
        after = one(f"SELECT grand_total, adjustment, vtiger_data FROM quote WHERE id = '{quote}'")
        self.assertEqual(Decimal(after[0]), Decimal("4242.42"))                # the recalculated total stays
        self.assertEqual(Decimal(after[1]), Decimal(before))                   # the source's new input does not
        self.assertIn("sourceTotals", json.loads(after[2]))
        self.assertTrue(recs[f"Quote:{Q1}"]["protected"])

    def test_10_finance_steps_touch_only_the_run(self):
        """Without the stand: the finance commands get the run's document ids (never an empty selection, which would
        mean every document), and the counters are raised in a run without documents too."""
        calls = []

        def command(args, _logdir, _name):
            calls.append(args)
            return []
        plan = spec.Plan([spec.Op("Payment", 1, "SPPayments"), spec.Op("Invoice", 2, "Invoice"),
                          spec.Op("PaymentAllocation", 1, "SPPayments")], [], {}, counters={"Payment": 2000})
        with mock.patch.object(importer, "espo_command", command), \
                mock.patch.object(importer, "stand_ids", lambda e, keys, _l: ["inv-2"] if e == "Invoice" else []), \
                mock.patch.object(importer, "allocation_targets", lambda _p, _l: {"so-9"}), \
                mock.patch.object(importer, "counters_below", lambda _c, _l: []):
            importer.finance_steps(plan, False, ROOT, {"inv-old"})
        self.assertEqual([c[0] for c in calls], ["itvolga-finance-verify", "itvolga-finance-settle",
                                                 "itvolga-finance-settle", "itvolga-setup-finance"])
        self.assertEqual(calls[0][1:3], ["--entity=Invoice", "--id=inv-2"])
        self.assertEqual({c[-1] for c in calls[1:3]}, {"--id=inv-2,inv-old,so-9"})
        calls.clear()
        plan = spec.Plan([spec.Op("Payment", 1, "SPPayments")], [], {}, counters={"Payment": 2000})
        with mock.patch.object(importer, "espo_command", command), \
                mock.patch.object(importer, "stand_ids", lambda e, keys, _l: []), \
                mock.patch.object(importer, "allocation_targets", lambda _p, _l: set()), \
                mock.patch.object(importer, "counters_below", lambda _c, _l: []):
            importer.finance_steps(plan, False, ROOT, set())
        self.assertEqual(calls, [["itvolga-setup-finance", "--next=Payment:2000"]])

    def test_11_line_amount_is_never_rounded(self):
        """The exact net of a line in an exact context: digits beyond the default 28 are not lost before the check."""
        line = spec_finance.LINE
        row = {line + "quantity": "1.001", line + "listprice": "1000000000000000000.00000001",
               line + "discount_amount": "1001000000000000000.00000000", line + "discount_percent": "0"}
        with self.assertRaises(spec.T.TransformError):
            spec_finance.exact_net(row)
        row.update({line + "quantity": "3.000", line + "listprice": "1234.56000000", line + "discount_amount": None,
                    line + "discount_percent": "12.5"})
        self.assertEqual(spec_finance.exact_net(row), "3240.72000000")

    def test_12_item_moved_out_of_a_recalculated_document_stays(self):
        """The source moves a line of the invoice recalculated in EspoCRM (test_04) to a new invoice: the line stays
        in its recalculated document (protected), the new invoice is imported."""
        source_sql("\n".join(document("Invoice", I3, ("vtiger_invoice", "invoiceid"),
                                       header("invoice_no", "С-9003", invoicestatus="Created", invoicedate="2024-03-01",
                                              balance="120.00000000", subtotal="120.00000000",
                                              pre_tax_total="120.00000000", total="120.00000000", region_id=0),
                                       [], "vtiger_invoicebillads", "vtiger_invoiceshipads",
                                       ("vtiger_invoicecf", "invoiceid")))
                   + f"\nUPDATE vtiger_inventoryproductrel SET id = {I3} WHERE lineitem_id = {L4};")
        report, recs, _ = self.run_import()
        self.assertEqual(report["problems"], {}, report.get("problem_columns"))
        self.assertEqual(recs[f"InvoiceItem:{L4}"]["check"], "protected")
        self.assertEqual(one(f"SELECT invoice_id FROM invoice_item WHERE vtiger_id = {L4}")[0], self.id_of("invoice", I1))
        self.assertIsNotNone(self.id_of("invoice", I3))

    def test_13_payment_only_run(self):
        """`--only SPPayments`: allocations wait for their documents, yet the allocation measures of the source and of
        the plan are equal (the waiting allocation carries its amount)."""
        report, recs, _ = self.run_import(only="SPPayments")
        self.assertEqual(report["problems"], {}, report.get("problem_columns"))
        self.assertEqual(report["aggregates"]["reader"]["unequal"], 0)
        self.assertTrue(recs[f"PaymentAllocation:{PAY1}"]["held"])

    def test_14_file_name_and_link_findings(self):
        """A photo whose name differs from its attachment's keeps the source name in vtigerData; an external link that
        is not a URL is kept too — both are findings (D-150, D-153)."""
        source_sql(f"UPDATE vtiger_contactdetails SET imagename = 'renamed.png' WHERE contactid = {C1};\n"
                   f"UPDATE vtiger_notes SET filename = 'not a link' WHERE notesid = {D2};")
        report, recs, _ = self.run_import()
        self.assertEqual(report["problems"], {}, report.get("problem_columns"))
        self.assertEqual(report["findings"].get("file_name_differs"), 1)
        self.assertEqual(report["findings"].get("external_url_invalid"), 1)
        data = json.loads(one(f"SELECT vtiger_data FROM contact WHERE vtiger_id = {C1}")[0])
        self.assertEqual(data["imagename"], "renamed.png")
        self.assertIsNotNone(one(f"SELECT c_photo_id FROM contact WHERE vtiger_id = {C1}")[0])

    def test_15_file_frames_and_unknown_currency(self):
        """Without the stand: a file always arrives in its declared number of frames (shorter — the writer refuses
        its size; longer — the run stops after them); an unknown currency holds the record."""
        root = Path(tempfile.mkdtemp(dir=ROOT))
        (root / "f").write_bytes(b"abcdefghij")
        files = importer.F.DirectoryFiles(root)
        frames = list(importer.F.chunk_lines(files, b"f", importer.F.CHUNK + 5))
        self.assertEqual(len(frames), 2)
        frames = importer.F.chunk_lines(files, b"f", 5)
        self.assertEqual(len(json.loads(next(frames))["data"]), 8)              # 5 bytes in base64
        with self.assertRaises(verify.SnapshotError):
            next(frames)
        with self.assertRaises(spec.T.TransformError):
            spec.Currency("vtiger_invoice.currency_id").apply(spec.Op("Invoice", 1, "Invoice"),
                                                              {"vtiger_invoice.currency_id": "2"}, None)


def load_tests(loader, tests, pattern):
    """Scenarios share the stand state: run them in their numbered order."""
    suite = unittest.TestSuite()
    for name in sorted(n for n in dir(Stage063) if n.startswith("test_")):
        suite.addTest(Stage063(name))
    return suite
