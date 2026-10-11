"""Acceptance tests of the import of base entities (stage 06.2, docs/migration/import.md) on the stand.

A synthetic mini-Vtiger (real column types, synthetic values, keys in a random block ≥ 900 000 000) is built in a
temporary database of the stand MySQL and imported by the same code as a real run (importer.execute with
`source_db`); EspoCRM records are checked through SQL and the private run reports. Cleanup removes only the records
whose ids this test recorded (never a list from the API). No production data.

    task test:stage06.2
"""
import json
import secrets
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "import"))
sys.path.insert(0, str(REPO / "tests" / "stage03"))
import importer  # noqa: E402
import spec  # noqa: E402
import transforms as T  # noqa: E402
import verify  # noqa: E402
from common import Mysql  # noqa: E402
from espo import Client, admin_credentials  # noqa: E402

HEX = secrets.token_hex(3)
VT = 900_000_000 + secrets.randbelow(89_000_000) // 1000 * 1000
KEYS = (VT, VT + 999)
PREFIX = f"SYNTH-imp-{HEX}"
ADMIN_NAME = f"synth-imp-{HEX}-admin"
CLASH_NAME = f"synth-imp-{HEX}-clash"


def phone(*parts):
    return "".join(parts)  # built at run time: no phone-shaped literal in Git


A1, A2, A3, C1, C2, L1, O1, P1, T1, H1, E1, E2, E3, E4, N1, N2, N3, F1 = (
    VT + 101, VT + 102, VT + 103, VT + 201, VT + 202, VT + 301, VT + 401, VT + 501, VT + 502, VT + 601, VT + 701,
    VT + 702, VT + 703, VT + 704, VT + 801, VT + 802, VT + 803, VT + 990)
U_ADMIN, U_SALES, U_DEPUTY, U_CLASH, U_GONE, G_SALES = VT + 1, VT + 2, VT + 3, VT + 4, VT + 5, VT + 900
C3, INV, DOC, E5 = VT + 203, VT + 961, VT + 962, VT + 705
SECRET = f"pw-{secrets.token_hex(6)}"

COLUMNS = {
    "vtiger_crmentity": "crmid INT PRIMARY KEY, smcreatorid INT, smownerid INT, modifiedby INT, setype VARCHAR(100), "
                        "description MEDIUMTEXT, createdtime DATETIME, modifiedtime DATETIME, deleted INT, "
                        "source VARCHAR(100), label VARCHAR(255)",
    "vtiger_account": "accountid INT PRIMARY KEY, account_no VARCHAR(100), accountname VARCHAR(100), account_type "
                      "VARCHAR(200), industry VARCHAR(200), rating VARCHAR(200), ownership VARCHAR(50), siccode VARCHAR(50), "
                      "tickersymbol VARCHAR(30), phone VARCHAR(30), otherphone VARCHAR(30), email1 VARCHAR(100), "
                      "email2 VARCHAR(100), website VARCHAR(100), fax VARCHAR(30), employees INT, inn VARCHAR(30), "
                      "kpp VARCHAR(30), isconvertedfromlead VARCHAR(3)",
    "vtiger_accountscf": "accountid INT PRIMARY KEY, vk_url VARCHAR(155), cf_1109 VARCHAR(25), cf_1111 VARCHAR(255), "
                         "cf_1113 VARCHAR(25), cf_1115 VARCHAR(10)",
    "vtiger_accountbillads": "accountaddressid INT PRIMARY KEY, bill_city VARCHAR(30), bill_code VARCHAR(30), "
                             "bill_country VARCHAR(30), bill_state VARCHAR(30), bill_street VARCHAR(250)",
    "vtiger_accountshipads": "accountaddressid INT PRIMARY KEY, ship_city VARCHAR(30), ship_code VARCHAR(30), "
                             "ship_country VARCHAR(30), ship_state VARCHAR(30), ship_pobox VARCHAR(30), ship_street VARCHAR(250)",
    "vtiger_contactdetails": "contactid INT PRIMARY KEY, contact_no VARCHAR(100), accountid INT, salutation VARCHAR(200), "
                             "firstname VARCHAR(40), lastname VARCHAR(80), email VARCHAR(100), phone VARCHAR(50), "
                             "mobile VARCHAR(50), title VARCHAR(50), department VARCHAR(30), fax VARCHAR(50), "
                             "secondaryemail VARCHAR(100), imagename VARCHAR(150), isconvertedfromlead VARCHAR(3)",
    "vtiger_contactaddress": "contactaddressid INT PRIMARY KEY, mailingcity VARCHAR(40), mailingstreet VARCHAR(250), "
                             "mailingcountry VARCHAR(40), othercountry VARCHAR(30), mailingstate VARCHAR(30), "
                             "othercity VARCHAR(40), otherstate VARCHAR(50), mailingzip VARCHAR(30), otherzip VARCHAR(30), "
                             "otherstreet VARCHAR(250)",
    "vtiger_contactsubdetails": "contactsubscriptionid INT PRIMARY KEY, homephone VARCHAR(50), otherphone VARCHAR(50), "
                                "birthday DATE, leadsource VARCHAR(200)",
    "vtiger_contactscf": "contactid INT PRIMARY KEY, vk_url VARCHAR(155), cf_1322 VARCHAR(20), cf_1324 VARCHAR(20), "
                         "cf_1326 VARCHAR(190), cf_1328 VARCHAR(50), cf_1372 VARCHAR(3), cf_1374 VARCHAR(3), "
                         "cf_1376 VARCHAR(3), cf_1378 VARCHAR(3)",
    "vtiger_customerdetails": "customerid INT PRIMARY KEY, portal VARCHAR(3), support_start_date DATE, support_end_date DATE",
    "vtiger_leaddetails": "leadid INT PRIMARY KEY, lead_no VARCHAR(100), email VARCHAR(100), firstname VARCHAR(40), "
                          "salutation VARCHAR(200), lastname VARCHAR(80), company VARCHAR(100), annualrevenue DECIMAL(25,8), "
                          "industry VARCHAR(200), rating VARCHAR(200), leadstatus VARCHAR(200), leadsource VARCHAR(200), "
                          "converted INT, designation VARCHAR(50), noofemployees INT, secondaryemail VARCHAR(100)",
    "vtiger_leadaddress": "leadaddressid INT PRIMARY KEY, city VARCHAR(30), code VARCHAR(30), state VARCHAR(30), "
                          "country VARCHAR(30), phone VARCHAR(50), mobile VARCHAR(50), fax VARCHAR(50), lane VARCHAR(250)",
    "vtiger_leadsubdetails": "leadsubscriptionid INT PRIMARY KEY, website VARCHAR(255)",
    "vtiger_leadscf": "leadid INT PRIMARY KEY, vk_url VARCHAR(155), cf_1107 VARCHAR(255), cf_1165 INT",
    "vtiger_potential": "potentialid INT PRIMARY KEY, potential_no VARCHAR(100), related_to INT, potentialname VARCHAR(120), "
                        "amount DECIMAL(25,8), closingdate DATE, nextstep VARCHAR(100), probability DECIMAL(7,3), "
                        "sales_stage VARCHAR(200), potentialtype VARCHAR(200), leadsource VARCHAR(200), "
                        "isconvertedfromlead VARCHAR(3), contact_id INT, spcompany VARCHAR(200), converted INT",
    "vtiger_troubletickets": "ticketid INT PRIMARY KEY, ticket_no VARCHAR(100), parent_id VARCHAR(100), product_id "
                             "VARCHAR(100), priority VARCHAR(200), severity VARCHAR(200), status VARCHAR(200), "
                             "category VARCHAR(200), title VARCHAR(255), solution TEXT, hours DECIMAL(25,8), "
                             "days DECIMAL(25,8), contact_id INT",
    "vtiger_ticketcf": "ticketid INT PRIMARY KEY, from_portal VARCHAR(3)",
    "vtiger_project": "projectid INT PRIMARY KEY, projectname VARCHAR(255), project_no VARCHAR(100), startdate DATE, "
                      "targetenddate DATE, actualenddate DATE, targetbudget VARCHAR(255), projecturl VARCHAR(255), "
                      "projectstatus VARCHAR(100), projectpriority VARCHAR(100), projecttype VARCHAR(100), "
                      "progress VARCHAR(100), linktoaccountscontacts VARCHAR(100), isconvertedfrompotential INT, "
                      "potentialid VARCHAR(100)",
    "vtiger_projecttask": "projecttaskid INT PRIMARY KEY, projecttaskname VARCHAR(255), projecttask_no VARCHAR(100), "
                          "projecttasktype VARCHAR(100), projecttaskpriority VARCHAR(100), projecttaskprogress VARCHAR(100), "
                          "projecttaskhours INT, startdate DATE, enddate DATE, projectid VARCHAR(100), "
                          "projecttasknumber INT, projecttaskstatus VARCHAR(100)",
    "vtiger_projecttaskcf": "projecttaskid INT PRIMARY KEY, cf_1320 VARCHAR(255), cf_1354 VARCHAR(3)",
    "vtiger_modcomments": "modcommentsid INT PRIMARY KEY, commentcontent TEXT, related_to INT, parent_comments INT, "
                          "customer INT, userid INT, filename VARCHAR(255)",
    "vtiger_modcommentscf": "modcommentsid INT PRIMARY KEY",
    "vtiger_activity": "activityid INT PRIMARY KEY, subject VARCHAR(255), activitytype VARCHAR(200), date_start DATE, "
                       "due_date DATE, time_start VARCHAR(50), time_end VARCHAR(50), duration_hours VARCHAR(200), "
                       "duration_minutes VARCHAR(200), status VARCHAR(200), eventstatus VARCHAR(200), priority VARCHAR(200)",
    "vtiger_users": "id INT PRIMARY KEY, user_name VARCHAR(255), user_password VARCHAR(200), first_name VARCHAR(30), "
                    "last_name VARCHAR(30), is_admin VARCHAR(3), currency_id INT, date_entered TIMESTAMP NULL, "
                    "title VARCHAR(50), department VARCHAR(50), phone_mobile VARCHAR(50), phone_work VARCHAR(50), "
                    "email1 VARCHAR(100), status VARCHAR(25), signature TEXT, date_format VARCHAR(200), "
                    "hour_format VARCHAR(30), imagename VARCHAR(250), language VARCHAR(36), time_zone VARCHAR(200), "
                    "phone_crm_extension VARCHAR(100), dayoftheweek VARCHAR(100), deleted INT",
    "vtiger_user2role": "userid INT PRIMARY KEY, roleid VARCHAR(255)",
    "vtiger_users2group": "groupid INT, userid INT",
    "vtiger_groups": "groupid INT PRIMARY KEY, groupname VARCHAR(100)",
    "vtiger_crmentityrel": "crmid INT, module VARCHAR(100), relcrmid INT, relmodule VARCHAR(100)",
    "vtiger_contpotentialrel": "contactid INT, potentialid INT",
    "vtiger_seactivityrel": "crmid INT, activityid INT",
    "vtiger_cntactivityrel": "contactid INT, activityid INT",
    "vtiger_salesmanactivityrel": "smid INT, activityid INT",
    "vtiger_freetagged_objects": "tag_id INT, tagger_id INT, object_id INT, module VARCHAR(100)",
    "vtiger_freetags": "id INT PRIMARY KEY, tag VARCHAR(50)",
    "vtiger_senotesrel": "crmid INT, notesid INT",
    "vtiger_seattachmentsrel": "crmid INT, attachmentsid INT",
}


def q(value):
    if value is None:
        return "NULL"
    return "_utf8mb4 X'" + str(value).encode("utf-8").hex() + "'"


def insert(table, **values):
    return f"INSERT INTO `{table}` ({', '.join(values)}) VALUES ({', '.join(q(v) for v in values.values())});"


def entity(crmid, setype, owner=None, created="2020-03-01 12:00:00", modified="2023-07-01 12:00:00", deleted=0,
           creator=None):
    description = None if setype in ("ModComments", "Faq") else f"{PREFIX} описание"  # as in the source
    return insert("vtiger_crmentity", crmid=crmid, smcreatorid=creator or U_SALES, smownerid=owner or U_SALES,
                  modifiedby=U_DEPUTY, setype=setype, description=description, createdtime=created,
                  modifiedtime=modified, deleted=deleted, source="CRM", label="x")


def fixture_sql():
    s = [
        insert("vtiger_groups", groupid=G_SALES, groupname="Отдел Продаж"),
        insert("vtiger_users", id=U_ADMIN, user_name=ADMIN_NAME, user_password="-" * 12, first_name="Synth",  # never read by the import
               last_name=f"{PREFIX} admin", is_admin="on", currency_id=1, date_entered="2018-01-02 03:04:05",
               email1=f"{ADMIN_NAME}@example.com", status="Active", language="ru_ru", time_zone="Europe/Moscow",
               date_format="dd-mm-yyyy", hour_format="24", dayoftheweek="Monday", deleted=0),
        insert("vtiger_users", id=U_SALES, user_name=f"synth-imp-{HEX}-sales", first_name="Synth",
               last_name=f"{PREFIX} sales", is_admin="off", currency_id=1, date_entered="2018-01-02 03:04:05",
               phone_work=phone("8 (900) ", "000-55-66"), status="Active", phone_crm_extension="101", deleted=0),
        insert("vtiger_users", id=U_DEPUTY, user_name=f"synth-imp-{HEX}-deputy", first_name="Synth",
               last_name=f"{PREFIX} deputy", is_admin="1", currency_id=1, date_entered="2018-01-02 03:04:05",
               status="Inactive", department="Синт", deleted=0),
        insert("vtiger_users", id=U_GONE, user_name=f"synth-imp-{HEX}-gone", last_name=PREFIX, is_admin="off",
               status="Active", deleted=1),
        insert("vtiger_user2role", userid=U_ADMIN, roleid="H2"),
        insert("vtiger_user2role", userid=U_SALES, roleid="H4"),
        insert("vtiger_user2role", userid=U_DEPUTY, roleid="H3"),
        insert("vtiger_users2group", groupid=G_SALES, userid=U_SALES),
        # accounts: user-owned (hierarchy team via a sales manager), group-owned, deleted
        entity(A1, "Accounts"),
        insert("vtiger_account", accountid=A1, account_no="КОНТР_1", accountname=f"{PREFIX} A1", account_type="Клиент",
               ownership="синт", phone=phone("8 (900) ", "000-11-22"), email1=f"Synth-A1-{HEX}@Example.com",
               employees=0, isconvertedfromlead="1"),
        insert("vtiger_accountscf", accountid=A1, cf_1109="0"),
        insert("vtiger_accountbillads", accountaddressid=A1, bill_city="Синтград", bill_street="ул. Синтетическая"),
        insert("vtiger_accountshipads", accountaddressid=A1),
        entity(A2, "Accounts", owner=G_SALES, created="2026-07-01 12:00:00", modified="2026-07-02 12:00:00"),
        insert("vtiger_account", accountid=A2, account_no="КОНТР_2", accountname=f"{PREFIX} A2"),
        entity(A3, "Accounts", deleted=1),
        insert("vtiger_account", accountid=A3, account_no="КОНТР_3", accountname=f"{PREFIX} A3 deleted"),
        # contacts: with an account (title + access fields), without an account (title has no place)
        entity(C1, "Contacts"),
        insert("vtiger_contactdetails", contactid=C1, contact_no="КОНТАКТ_1", accountid=A1, firstname="Синт",
               lastname=f"{PREFIX} C1", title="Директор", mobile=phone("+7 900 ", "000 33 44"), salutation="Mr."),
        insert("vtiger_contactaddress", contactaddressid=C1),
        insert("vtiger_contactsubdetails", contactsubscriptionid=C1, leadsource="Cold Call"),
        insert("vtiger_contactscf", contactid=C1, cf_1322="synth-id", cf_1324=SECRET, cf_1372="1", cf_1374="0"),
        insert("vtiger_customerdetails", customerid=C1, portal="0"),
        entity(C2, "Contacts"),
        insert("vtiger_contactdetails", contactid=C2, contact_no="КОНТАКТ_2", accountid=0, lastname=f"{PREFIX} C2",
               title="Без контрагента", salutation="Господин"),
        insert("vtiger_contactaddress", contactaddressid=C2),
        insert("vtiger_contactsubdetails", contactsubscriptionid=C2),
        insert("vtiger_contactscf", contactid=C2),
        insert("vtiger_customerdetails", customerid=C2),
        # lead converted
        entity(L1, "Leads"),
        insert("vtiger_leaddetails", leadid=L1, lead_no="ОБР_1", lastname=f"{PREFIX} L1", leadstatus="Холодный",
               converted=1, annualrevenue="0.00000000"),
        insert("vtiger_leadaddress", leadaddressid=L1),
        insert("vtiger_leadsubdetails", leadsubscriptionid=L1),
        insert("vtiger_leadscf", leadid=L1),
        # opportunity: no probability (stays empty, D-38)
        entity(O1, "Potentials"),
        insert("vtiger_potential", potentialid=O1, potential_no="СДЕЛКА_1", related_to=A1, potentialname=f"{PREFIX} O1",
               amount="1500.50000000", sales_stage="Переговоры", contact_id=C1, converted=0),
        # project and task with a tag
        entity(P1, "Project"),
        insert("vtiger_project", projectid=P1, projectname=f"{PREFIX} P1", project_no="PROJ 1", targetbudget="1 200,50",
               linktoaccountscontacts=str(A1), projectstatus="Выполняется"),
        entity(T1, "ProjectTask", owner=G_SALES),
        insert("vtiger_projecttask", projecttaskid=T1, projecttaskname=f"{PREFIX} T1", projecttask_no="PT 1",
               projectid=str(P1), projecttaskstatus="Open", projecttaskhours=0),
        insert("vtiger_projecttaskcf", projecttaskid=T1, cf_1354="1"),
        insert("vtiger_freetags", id=VT + 991, tag="синт-тег"),
        insert("vtiger_freetagged_objects", tag_id=VT + 991, tagger_id=U_SALES, object_id=T1, module="ProjectTask"),
        # case
        entity(H1, "HelpDesk"),
        insert("vtiger_troubletickets", ticketid=H1, ticket_no="ЗАЯВКА_1", parent_id=str(A1), title=f"{PREFIX} H1",
               status="Open", priority="Высокий", hours="0.00000000", contact_id=C1),
        insert("vtiger_ticketcf", ticketid=H1, from_portal="0"),
        # activities: task, call, meeting (lead via crmentityrel), «Письмо»
        entity(E1, "Calendar"),
        insert("vtiger_activity", activityid=E1, subject=f"{PREFIX} E1", activitytype="Task", date_start="2023-07-01",
               time_start="12:00", due_date="2023-07-05", status="Completed", priority="Medium"),
        insert("vtiger_seactivityrel", crmid=A1, activityid=E1),
        entity(E5, "Calendar"),
        insert("vtiger_activity", activityid=E5, subject=f"{PREFIX} E5", activitytype="Task", status="Not Started"),
        insert("vtiger_seactivityrel", crmid=O1, activityid=E5),
        entity(E2, "Calendar"),
        insert("vtiger_activity", activityid=E2, subject=f"{PREFIX} E2", activitytype="Call", date_start="2020-03-01",
               time_start="12:00", due_date="2020-03-01", time_end="12:30", duration_hours="0",
               duration_minutes="30", eventstatus="Held"),
        insert("vtiger_cntactivityrel", contactid=C1, activityid=E2),
        insert("vtiger_salesmanactivityrel", smid=U_SALES, activityid=E2),
        entity(E3, "Calendar"),
        insert("vtiger_activity", activityid=E3, subject=f"{PREFIX} E3", activitytype="Meeting", eventstatus="Planned"),
        insert("vtiger_crmentityrel", crmid=L1, module="Leads", relcrmid=E3, relmodule="Calendar"),
        entity(E4, "Calendar"),
        insert("vtiger_activity", activityid=E4, subject=f"{PREFIX} E4", activitytype="Письмо", date_start="2023-07-01",
               time_start="12:00", due_date="2023-07-01", time_end="13:00", duration_hours="2", duration_minutes="0",
               eventstatus="Held", priority="High"),
        insert("vtiger_cntactivityrel", contactid=C1, activityid=E4),
        insert("vtiger_seactivityrel", crmid=O1, activityid=E4),
        # comments: on the opportunity (author = userid), on a FAQ (waits for stage 06.3)
        entity(N1, "ModComments", created="2023-07-01 12:00:00"),
        insert("vtiger_modcomments", modcommentsid=N1, commentcontent=f"{PREFIX} N1 <b>x</b>", related_to=O1,
               userid=U_DEPUTY, customer=0),
        insert("vtiger_modcommentscf", modcommentsid=N1),
        entity(F1, "Faq"),
        # links to records of stage 06.3 (an invoice, a document): pending, every row still accounted
        entity(INV, "Invoice"), insert("vtiger_crmentityrel", crmid=A1, module="Accounts", relcrmid=INV, relmodule="Invoice"),
        entity(DOC, "Documents"), insert("vtiger_senotesrel", crmid=A1, notesid=DOC),
        entity(N2, "ModComments"),
        insert("vtiger_modcomments", modcommentsid=N2, commentcontent=f"{PREFIX} N2", related_to=F1, userid=U_SALES),
        insert("vtiger_modcommentscf", modcommentsid=N2),
    ]
    return s


def source_sql(script):
    return Mysql.stand(database=SOURCE).lines("SET SESSION sql_log_bin=0;\n" + script + "\n", ROOT / "source.log")


def sql(query):
    return [line.decode("utf-8").split("\t") for line in
            Mysql.stand(database="espocrm").lines(query + "\n", ROOT / "stand.log")]


def one(query):
    rows = sql(query)
    return rows[0] if rows else None


class Stage062(unittest.TestCase):
    runs = []

    @classmethod
    def setUpClass(cls):
        global ROOT, SOURCE
        ROOT = Path(tempfile.mkdtemp(prefix="vtimp-test-"))
        cls.addClassCleanup(shutil.rmtree, ROOT, True)
        taken = one(f"SELECT COUNT(*) FROM account WHERE vtiger_id BETWEEN {KEYS[0]} AND {KEYS[1]}")
        assert taken == ["0"], "the random key block is in use: run again"
        cls.temp = verify.TempDatabases(ROOT, ROOT)
        SOURCE = cls.temp.create("vtiger7", "utf8mb4", "utf8mb4_0900_ai_ci")
        cls.addClassCleanup(cls.temp.drop_all)
        source_sql("\n".join(f"CREATE TABLE `{t}` ({c}) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;" for t, c in COLUMNS.items()))
        source_sql("\n".join(fixture_sql()))
        cls.preexisting = {t: {r[0] for r in sql(f"SELECT id FROM {t}")} for t in ("email_address", "phone_number")}
        cls.client = Client(*admin_credentials())
        cls.created = []  # (entity type, id) made by the test itself through the API
        cls.addClassCleanup(cls.cleanup)
        for name, user_type in ((ADMIN_NAME, "admin"), (CLASH_NAME, "regular")):
            status, body, _ = cls.client.post("User", {"userName": name, "lastName": PREFIX, "type": user_type,
                                                       "password": secrets.token_urlsafe(16)})
            assert status == 200, status
            cls.created.append(("User", body["id"]))

    @classmethod
    def run_import(cls, only=None, check_only=False):
        rundir = ROOT / f"run-{len(cls.runs)}"
        rundir.mkdir()
        report = importer.execute(rundir, source_db=SOURCE, only=only, check_only=check_only, adopt=ADMIN_NAME,
                                  key_range=KEYS, effective_admin=U_ADMIN)
        recs = [json.loads(line) for line in (rundir / "records.jsonl").read_text().splitlines()]
        cls.runs.append(recs)
        return report, {r["key"]: r for r in recs}

    @classmethod
    def cleanup(cls):
        """Hard delete of exactly the records of this test: ids from the run records and the API calls."""
        ids = {}
        for recs in cls.runs:
            for r in recs:
                if r.get("id"):
                    ids.setdefault(r["key"].split(":")[0], set()).add(r["id"])
        for etype, eid in cls.created:
            ids.setdefault(etype, set()).add(eid)
        tables = {"User": "user", "Account": "account", "Contact": "contact", "ContactAccess": "contact_access",
                  "Lead": "lead", "Opportunity": "opportunity", "Project": "project", "ProjectTask": "project_task",
                  "Case": "case", "Task": "task", "Call": "call", "Meeting": "meeting", "Note": "note"}
        junctions = ["DELETE FROM entity_team WHERE entity_id IN ({0})", "DELETE FROM entity_email_address WHERE entity_id IN ({0})",
                     "DELETE FROM entity_phone_number WHERE entity_id IN ({0})", "DELETE FROM account_contact WHERE contact_id IN ({0}) OR account_id IN ({0})",
                     "DELETE FROM contact_opportunity WHERE contact_id IN ({0}) OR opportunity_id IN ({0})",
                     "DELETE FROM call_user WHERE call_id IN ({0}) OR user_id IN ({0})", "DELETE FROM call_contact WHERE call_id IN ({0})",
                     "DELETE FROM meeting_user WHERE meeting_id IN ({0}) OR user_id IN ({0})", "DELETE FROM contact_meeting WHERE meeting_id IN ({0})",
                     "DELETE FROM lead_meeting WHERE meeting_id IN ({0})", "DELETE FROM call_lead WHERE call_id IN ({0})", "DELETE FROM case_contact WHERE case_id IN ({0})",
                     "DELETE FROM entity_collaborator WHERE entity_id IN ({0}) OR user_id IN ({0})",
                     "DELETE FROM role_user WHERE user_id IN ({0})", "DELETE FROM team_user WHERE user_id IN ({0})",
                     "DELETE FROM preferences WHERE id IN ({0})", "DELETE FROM stream_subscription WHERE entity_id IN ({0}) OR user_id IN ({0})",
                     "DELETE FROM notification WHERE user_id IN ({0}) OR related_id IN ({0})",
                     "DELETE FROM note WHERE parent_id IN ({0}) OR related_id IN ({0})",
                     "DELETE FROM reminder WHERE entity_id IN ({0})", "DELETE FROM array_value WHERE entity_id IN ({0})",
                     "DELETE FROM user_data WHERE id IN ({0})", "DELETE FROM auth_token WHERE user_id IN ({0})"]
        all_ids = ",".join("'" + i + "'" for s in ids.values() for i in sorted(s))
        if not all_ids:
            return
        # shared address/number rows: only those linked to this test's records, new since setUp and not used elsewhere
        shared = {}
        for table, link, column in (("email_address", "entity_email_address", "email_address_id"),
                                    ("phone_number", "entity_phone_number", "phone_number_id")):
            linked = {r[0] for r in sql(f"SELECT {column} FROM {link} WHERE entity_id IN ({all_ids})")}
            shared[(table, link, column)] = sorted(linked - cls.preexisting[table])
        script = [j.format(all_ids) + ";" for j in junctions]
        for (table, link, column), row_ids in shared.items():
            if row_ids:
                listed = ",".join("'" + i + "'" for i in row_ids)
                script.append(f"DELETE FROM {table} WHERE id IN ({listed}) AND id NOT IN (SELECT {column} FROM {link});")
        for etype, table in tables.items():
            if ids.get(etype):
                script.append(f"DELETE FROM `{table}` WHERE id IN ({','.join(chr(39) + i + chr(39) for i in sorted(ids[etype]))});")
        Mysql.stand(database="espocrm").lines("\n".join(script) + "\n", ROOT / "cleanup.log")

    def id_of(self, table, key):
        row = one(f"SELECT id FROM `{table}` WHERE vtiger_id = {key} AND deleted = 0")
        return row[0] if row else None

    # --- scenarios (run in order) ------------------------------------------------------------------

    def test_01_deferred_then_full(self):
        report, recs = self.run_import(only="Users,Contacts")
        self.assertEqual(recs[f"Contact:{C1}"]["apply"], "created")
        self.assertEqual(one(f"SELECT account_id IS NULL FROM contact WHERE vtiger_id = {C1}"), ["1"])  # deferred
        outcomes = [o for o in recs[f"Contact:{C1}"]["outcomes"] if o[1] == "vtiger_contactdetails.accountid"]
        self.assertEqual(outcomes[0][2], "deferred")
        report, recs = self.run_import()
        self.assertEqual(report["problems"], {}, report["problem_columns"])
        self.assertEqual(recs[f"Contact:{C1}"]["apply"], "updated")
        self.assertEqual(one(f"SELECT account_id FROM contact WHERE vtiger_id = {C1}"), [self.id_of("account", A1)])
        self.assertEqual(report["silence"], {k: 0 for k in importer.SILENCE})
        statuses = {r["check"] for r in recs.values() if not r["held"] and r["key"].split(":")[0] != "ContactAccess"}
        self.assertEqual(statuses, {"equal"})
        self.assertEqual(report["link_tables"]["vtiger_crmentityrel"], {"source_rows": 2, "accounted": 2})
        self.assertEqual(report["link_tables"]["vtiger_senotesrel"], {"source_rows": 1, "accounted": 1})

    def test_02_values(self):
        a1 = self.id_of("account", A1)
        self.assertEqual(one(f"SELECT created_at, modified_at, type, assigned_user_id IS NOT NULL FROM account WHERE id='{a1}'"),
                         ["2020-03-01 09:00:00", "2023-07-01 10:00:00", "Customer", "1"])  # D-30: Moscow, Berlin
        self.assertEqual(json.loads(one(f"SELECT vtiger_data FROM account WHERE id='{a1}'")[0]),
                         {"accounttype": "Клиент", "email1": f"Synth-A1-{HEX}@Example.com", "isconvertedfromlead": True,
                          "ownership": "синт", "phone": phone("8 (900) ", "000-11-22")})
        self.assertEqual(one(f"SELECT p.name, p.type FROM phone_number p JOIN entity_phone_number e ON e.phone_number_id=p.id "
                             f"WHERE e.entity_id='{a1}' AND e.deleted=0"), [phone("+7900", "0001122"), "Office"])
        self.assertEqual(one(f"SELECT c_employees IS NULL FROM account WHERE id='{a1}'"), ["1"])   # 0 = empty
        teams = {r[0] for r in sql(f"SELECT t.name FROM entity_team e JOIN team t ON t.id=e.team_id WHERE e.entity_id='{a1}' AND e.deleted=0")}
        self.assertEqual(teams, {"Подчинённые заместителей"})        # owner holds «Менеджер по продажам» (D-39)
        a2 = self.id_of("account", A2)
        self.assertEqual(one(f"SELECT assigned_user_id IS NULL, created_at FROM account WHERE id='{a2}'"),
                         ["1", "2026-07-01 12:00:00"])               # group owner; UTC epoch
        teams = {r[0] for r in sql(f"SELECT t.name FROM entity_team e JOIN team t ON t.id=e.team_id WHERE e.entity_id='{a2}' AND e.deleted=0")}
        self.assertEqual(teams, {"Отдел Продаж"})
        self.assertIsNone(self.id_of("account", A3))                    # deleted in Vtiger (D-07)
        c1, c2 = self.id_of("contact", C1), self.id_of("contact", C2)
        self.assertEqual(one(f"SELECT role FROM account_contact WHERE contact_id='{c1}' AND deleted=0"), ["Директор"])
        self.assertEqual(json.loads(one(f"SELECT vtiger_data FROM contact WHERE id='{c2}'")[0]),
                         {"salutationtype": "Господин", "title": "Без контрагента"})
        self.assertEqual(one(f"SELECT c_need_original_docs, c_send_news FROM contact WHERE id='{c1}'"), ["1", "0"])
        access = one(f"SELECT anydesk_id, has_anydesk_password, anydesk_password <> {Mysql_quote(SECRET)} FROM contact_access "
                     f"WHERE vtiger_id={C1} AND deleted=0")
        self.assertEqual(access, ["synth-id", "1", "1"])                 # encrypted, never the plain value
        self.assertIsNone(one(f"SELECT id FROM contact_access WHERE vtiger_id={C2}"))
        self.assertEqual(one(f"SELECT status, converted_at IS NULL FROM `lead` WHERE vtiger_id={L1}"), ["Converted", "1"])
        self.assertEqual(one(f"SELECT probability IS NULL, amount, stage, contact_id = '{c1}' FROM opportunity WHERE vtiger_id={O1}"),
                         ["1", "1500.50000000", "Negotiation or Review", "1"])
        self.assertEqual(one(f"SELECT budget, status FROM project WHERE vtiger_id={P1}"), ["1200.50", "Выполняется"])
        self.assertEqual(one(f"SELECT tags, show_in_stat, hours FROM project_task WHERE vtiger_id={T1}"),
                         ['["синт-тег"]', "1", "0"])
        self.assertEqual(one(f"SELECT status, priority, account_id IS NOT NULL, contact_id = '{c1}' FROM `case` WHERE vtiger_id={H1}"),
                         ["New", "High", "1", "1"])
        self.assertEqual(one(f"SELECT status, priority, date_completed IS NULL, date_end_date, date_end, parent_type FROM task "
                             f"WHERE vtiger_id={E1}"), ["Completed", "Normal", "1", "2023-07-05", "2023-07-05 21:00:00", "Account"])
        self.assertEqual(one(f"SELECT parent_type, contact_id = '{c1}' FROM task WHERE vtiger_id={E5}"),
                         ["Opportunity", "1"])                            # contact derived from the parent, as the core does
        self.assertEqual(one(f"SELECT date_start, date_end, direction IS NULL, status FROM `call` WHERE vtiger_id={E2}"),
                         ["2020-03-01 09:00:00", "2020-03-01 09:30:00", "1", "Held"])
        self.assertEqual(one(f"SELECT parent_type, date_start IS NULL FROM meeting WHERE vtiger_id={E3}"), ["Lead", "1"])
        e4 = one(f"SELECT c_task_type, contact_id = '{c1}', parent_type, vtiger_data FROM task WHERE vtiger_id={E4}")
        self.assertEqual(e4[:3], ["Письмо", "1", "Opportunity"])
        self.assertEqual(json.loads(e4[3]), {"duration_hours": "2", "duration_minutes": "0", "eventstatus": "Held",
                                             "taskpriority": "High"})   # 2 h disagree with the dates: kept
        self.assertEqual(one(f"SELECT COUNT(*) FROM reminder WHERE entity_id IN (SELECT id FROM `call` WHERE vtiger_id={E2})"), ["0"])
        n1 = one(f"SELECT type, parent_type, created_by_id = (SELECT id FROM user WHERE vtiger_id={U_DEPUTY}), created_at, "
                 f"modified_at FROM note WHERE vtiger_id={N1}")
        self.assertEqual(n1, ["Post", "Opportunity", "1", "2023-07-01 10:00:00", "2023-07-01 10:00:00"])
        self.assertIsNone(one(f"SELECT id FROM note WHERE vtiger_id={N2}"))   # FAQ comment waits for 06.3
        admin = one(f"SELECT vtiger_id, type FROM user WHERE user_name={Mysql_quote(ADMIN_NAME)} AND deleted=0")
        self.assertEqual(admin, [str(U_ADMIN), "admin"])                      # adopted, not duplicated
        deputy = one(f"SELECT type, is_active, password <> '' FROM user WHERE vtiger_id={U_DEPUTY}")
        self.assertEqual(deputy, ["regular", "0", "1"])                       # '1' is not an administrator (D-39)
        self.assertIsNone(one(f"SELECT id FROM user WHERE vtiger_id={U_GONE}"))   # deleted in Vtiger (D-07)

    def test_03_rerun_writes_nothing(self):
        before = self.fingerprint()
        report, recs = self.run_import()
        self.assertEqual({r["apply"] for r in recs.values() if not r["held"]} - {"skipped"}, {"unchanged"})
        self.assertEqual(self.fingerprint(), before)

    def test_04_source_wins_manual_links_stay(self):
        status, body, _ = self.client.post("Contact", {"lastName": f"{PREFIX} manual"})
        self.assertEqual(status, 200)
        self.created.append(("Contact", body["id"]))
        o1 = self.id_of("opportunity", O1)
        status, _, _ = self.client.post(f"Opportunity/{o1}/contacts", {"id": body["id"]})
        self.assertEqual(status, 200)
        source_sql(f"UPDATE vtiger_account SET accountname={q(PREFIX + ' A1 renamed')} WHERE accountid={A1};"
                   f"UPDATE vtiger_crmentity SET modifiedtime='2024-01-15 10:00:00' WHERE crmid={A1};")
        report, recs = self.run_import()
        self.assertEqual(recs[f"Account:{A1}"]["apply"], "updated")
        self.assertEqual(one(f"SELECT name, modified_at FROM account WHERE vtiger_id={A1}"),
                         [f"{PREFIX} A1 renamed", "2024-01-15 09:00:00"])
        self.assertEqual(one(f"SELECT COUNT(*) FROM contact_opportunity WHERE opportunity_id='{o1}' AND contact_id='{body['id']}' "
                             f"AND deleted=0"), ["1"])

    def test_05_soft_deleted_target_is_restored(self):
        a2 = self.id_of("account", A2)
        status, _, _ = self.client.delete(f"Account/{a2}")
        self.assertEqual(status, 200)
        report, recs = self.run_import()
        self.assertEqual(recs[f"Account:{A2}"]["apply"], "restored")
        self.assertEqual(self.id_of("account", A2), a2)

    def test_06_new_comment_is_silent_for_followers(self):
        o1 = self.id_of("opportunity", O1)
        status, _, _ = self.client.request("PUT", f"Opportunity/{o1}/subscription")
        self.assertEqual(status, 200)
        before = one("SELECT COUNT(*) FROM notification")[0]
        source_sql("\n".join([entity(N3, "ModComments", created="2024-02-01 10:00:00"),
                              insert("vtiger_modcomments", modcommentsid=N3, commentcontent=f"{PREFIX} N3",
                                     related_to=O1, userid=U_SALES),
                              insert("vtiger_modcommentscf", modcommentsid=N3)]))
        report, recs = self.run_import()
        self.assertEqual(recs[f"Note:{N3}"]["apply"], "created")
        self.assertEqual(one("SELECT COUNT(*) FROM notification")[0], before)
        self.assertEqual(one(f"SELECT stream_updated_at IS NULL FROM opportunity WHERE id='{o1}'"), ["1"])

    def test_07_username_clash_is_an_error(self):
        source_sql(insert("vtiger_users", id=U_CLASH, user_name=CLASH_NAME, last_name=PREFIX, is_admin="off",
                          status="Active", deleted=0))
        report, recs = self.run_import()
        self.assertEqual((recs[f"User:{U_CLASH}"]["apply"], recs[f"User:{U_CLASH}"]["error"]), ("error", "username_clash"))
        self.assertEqual(one(f"SELECT COUNT(*) FROM user WHERE user_name={Mysql_quote(CLASH_NAME)}"), ["1"])
        self.assertEqual(report["status"], "fail")
        source_sql(f"DELETE FROM vtiger_users WHERE id={U_CLASH};")


    def test_08_removed_activity_parent_is_cleared(self):
        source_sql(f"DELETE FROM vtiger_seactivityrel WHERE activityid={E4};")
        report, recs = self.run_import()
        self.assertEqual(recs[f"Task:{E4}"]["apply"], "updated")
        self.assertEqual(one(f"SELECT parent_id IS NULL, parent_type IS NULL FROM task WHERE vtiger_id={E4}"), ["1", "1"])

    def test_09_reminders_of_an_event_stay(self):
        e2 = self.id_of("call", E2)
        user = one(f"SELECT id FROM user WHERE vtiger_id={U_SALES}")[0]
        rid = "synthimp" + HEX + "r1"
        sql(f"INSERT INTO reminder (id, remind_at, start_at, type, seconds, entity_type, entity_id, user_id, deleted) "
            f"VALUES ('{rid}', '2030-01-01 08:00:00', '2030-01-01 09:00:00', 'Popup', 3600, 'Call', '{e2}', '{user}', 0)")
        self.created.append(("Reminder", rid))
        source_sql(f"UPDATE vtiger_activity SET date_start='2020-03-02', due_date='2020-03-02' WHERE activityid={E2};"
                   f"UPDATE vtiger_crmentity SET modifiedtime='2024-03-01 10:00:00' WHERE crmid={E2};")
        report, recs = self.run_import()
        self.assertEqual(recs[f"Call:{E2}"]["apply"], "updated")
        self.assertEqual(one(f"SELECT date_start FROM `call` WHERE id='{e2}'"), ["2020-03-02 09:00:00"])
        self.assertEqual(sql(f"SELECT id FROM reminder WHERE entity_id='{e2}' AND deleted=0"), [[rid]])

    def test_10_shared_email_flags_stay(self):
        address = f"synth-shared-{HEX}@example.com"
        status, body, _ = self.client.post("Lead", {"lastName": f"{PREFIX} shared", "emailAddressData": [
            {"emailAddress": address, "primary": True, "optOut": True, "invalid": False}]})
        self.assertEqual(status, 200)
        self.created.append(("Lead", body["id"]))
        source_sql("\n".join([entity(C3, "Contacts"),
                              insert("vtiger_contactdetails", contactid=C3, contact_no="КОНТАКТ_3", lastname=f"{PREFIX} C3",
                                     email=address),
                              insert("vtiger_contactaddress", contactaddressid=C3),
                              insert("vtiger_contactsubdetails", contactsubscriptionid=C3),
                              insert("vtiger_contactscf", contactid=C3), insert("vtiger_customerdetails", customerid=C3)]))
        report, recs = self.run_import()
        self.assertEqual(recs[f"Contact:{C3}"]["apply"], "created")
        self.assertEqual(one(f"SELECT opt_out FROM email_address WHERE lower={Mysql_quote(address)}"), ["1"])
        self.assertEqual(recs[f"Contact:{C3}"]["check"], "equal")

    def test_11_manual_contact_stays_when_the_source_primary_goes(self):
        status, body, _ = self.client.post("Contact", {"lastName": f"{PREFIX} manual primary"})
        self.assertEqual(status, 200)
        self.created.append(("Contact", body["id"]))
        h1 = self.id_of("case", H1)
        status, _, _ = self.client.put(f"Case/{h1}", {"contactId": body["id"]})   # a user makes it the primary
        self.assertEqual(status, 200)
        source_sql(f"UPDATE vtiger_troubletickets SET contact_id=0 WHERE ticketid={H1};")
        report, recs = self.run_import()
        self.assertEqual(recs[f"Case:{H1}"]["apply"], "updated")
        self.assertEqual(one(f"SELECT contact_id IS NULL FROM `case` WHERE id='{h1}'"), ["1"])     # source wins
        linked = {r[0] for r in sql(f"SELECT contact_id FROM case_contact WHERE case_id='{h1}' AND deleted=0")}
        self.assertIn(body["id"], linked)                                                          # manual link stays

    def test_12_partial_run_keeps_derived_task_contact(self):
        report, recs = self.run_import(only="Calendar")
        self.assertEqual(one(f"SELECT contact_id = (SELECT id FROM contact WHERE vtiger_id={C1}) FROM task "
                             f"WHERE vtiger_id={E5}"), ["1"])
        self.assertEqual(recs[f"Task:{E5}"]["apply"], "unchanged")

    def fingerprint(self):
        parts = []
        for table, key in (("account", A1), ("contact", C1), ("contact_access", C1), ("opportunity", O1),
                           ("note", N1), ("task", E4), ("call", E2), ("user", U_ADMIN)):
            extra = "anydesk_password" if table == "contact_access" else "IFNULL(vtiger_data, '')"
            parts.append(one(f"SELECT CONCAT_WS('|', id, modified_at, created_at, {extra}, deleted) FROM `{table}` "
                             f"WHERE vtiger_id={key}"))
        parts.append(one("SELECT COUNT(*) FROM entity_team WHERE deleted=0"))
        parts.append(one(f"SELECT MD5(data) FROM preferences WHERE id=(SELECT id FROM user WHERE vtiger_id={U_ADMIN})"))
        return parts


def Mysql_quote(value):
    return "_utf8mb4 X'" + value.encode("utf-8").hex() + "'"


class Pure(unittest.TestCase):
    def test_epochs(self):
        self.assertEqual(T.vt_datetime("2022-10-31 23:30:00"), "2022-10-31 20:30:00")   # Moscow
        self.assertEqual(T.vt_datetime("2022-11-01 00:30:00"), "2022-10-31 23:30:00")   # Berlin, CET
        self.assertEqual(T.vt_datetime("2026-06-12 12:00:00"), "2026-06-12 10:00:00")   # Berlin, CEST
        self.assertEqual(T.vt_datetime("2026-06-13 00:00:00"), "2026-06-13 00:00:00")   # UTC
        flags = {}
        T.vt_datetime("2023-03-26 02:30:00", flags)
        T.vt_datetime("2023-10-29 02:30:00", flags)
        self.assertEqual(flags, {"dst_gap": 1, "dst_fold": 1})

    def test_phones(self):
        cases = {phone("8 (900) ", "123-45-67"): (phone("+7900", "1234567"), "ru11"),
                 phone("(8452) ", "12-34-56"): (phone("+7845", "2123456"), "ru10"),
                 phone("12-34", "-56"): (phone("12-34", "-56"), "local"),
                 "101": ("101", "short"),
                 phone("8 900 ", "123 45 67, ", "8 900 ", "123 45 68"): (phone("8 900 ", "123 45 67, ", "8 900 ", "123 45 68"), "multi"),
                 phone("+49 (30) ", "1234567"): (phone("+4930", "1234567"), "plus")}
        for raw, want in cases.items():
            self.assertEqual(T.phone(raw), want)

    def test_decimal_and_maps(self):
        self.assertEqual(T.decimal("1200.5", 2), "1200.50")
        with self.assertRaises(T.TransformError):
            T.decimal("1.005", 2)
        maps = T.ValueMaps()
        self.assertEqual(maps.lookup("Opportunity", "stage", "Potentials.sales_stage", "Переговоры"), "Negotiation or Review")
        with self.assertRaises(T.TransformError):
            maps.lookup("Opportunity", "stage", "Potentials.sales_stage", "no such stage")

    def test_coverage_of_committed_maps(self):
        fields, relations = spec.load_maps(REPO)
        self.assertEqual(spec.check_coverage(fields, relations), [])

    def test_error_outcomes_fail_the_run(self):
        op = spec.Op("Account", 5, "Accounts")
        op.column("vtiger_crmentity.smownerid", "error:owner_unknown")
        plan = spec.Plan([op], [], spec.Counter())
        census = {"Accounts": {"vtiger_crmentity.smownerid": (1, 1)}}
        report = importer.reconcile(plan, {}, {op.key: {"status": "equal"}}, census, [], (1, 10), False, {})
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["problems"].get("error_outcomes"), 1)

    def test_real_import_refuses_synthetic_keys(self):
        data = {k: [] for k in list(spec.SOURCES) + list(spec.TABLES)}
        data.update(crm={}, activity_type={})
        data["vtiger_users"] = [{"vtiger_users.id": str(spec.SYNTHETIC_KEY_MIN + 5), "vtiger_users.user_name": "x",
                                 "vtiger_users.status": "Active"}]
        with self.assertRaises(T.TransformError):
            spec.build(data)


if __name__ == "__main__":
    unittest.main()
