"""Stage 03 acceptance tests on the local stand with synthetic data only.

Run: task test:stage03   (or: python3 -m unittest discover -s tests/stage03 -v)

Covers: the model against docs/migration/field-map.csv and relations.csv, every created field type, the value
dictionary, roles of D-22 with Vtiger sharing (hierarchy/group teams), ContactAccess protection (D-06),
read-only archive fields and the read-only PBX history. Every record and user is created by the test run
(names start with SYNTH-<run id>) and deleted at the end.
"""
import base64
import csv
import json
import secrets
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/model"))
import model_check  # noqa: E402
from espo import REPO, Client, admin_credentials, espo_console, sql  # noqa: E402

RUN = secrets.token_hex(3)
TAG = f"SYNTH-{RUN}"
PASSWORD_PLAIN = f"synth-{secrets.token_hex(6)}"
ROLES = ["Директор", "Заместитель директора", "Менеджер по продажам", "Менеджер клиентов", "Доступы"]
VT_BASE = 900_000_000 + secrets.randbelow(90_000_000)

S = {}  # shared fixtures: clients, ids


def vt_id(n):
    return VT_BASE + n


def ok(test, result, codes=(200,)):
    status, payload, _ = result
    test.assertIn(status, codes, f"unexpected HTTP {status}: {json.dumps(payload, ensure_ascii=False)[:300]}")
    return payload


def setUpModule():
    admin = Client(*admin_credentials())
    S["admin"] = admin
    status, roles, _ = admin.get("Role", maxSize=50)
    assert status == 200, "admin API login failed"
    role_ids = {r["name"]: r["id"] for r in roles["list"]}
    missing = [r for r in ROLES if r not in role_ids]
    assert not missing, f"roles missing (run task espo -- itvolga-setup-acl): {missing}"
    teams = {t["name"]: t["id"] for t in admin.get("Team", maxSize=50)[1]["list"]}
    S["teams"] = teams
    users = {
        "dir": (["Директор"], []),
        "dep1": (["Заместитель директора"], ["Отдел Поддержки"]),
        "dep2": (["Заместитель директора"], ["Отдел Поддержки"]),
        "sales": (["Менеджер по продажам"], []),
        "cust": (["Менеджер клиентов"], []),
        "access": (["Заместитель директора", "Доступы"], []),
        "norole": ([], []),
    }
    S["user_ids"], S["clients"] = {}, {}
    for key, (roles_, teams_) in users.items():
        password = secrets.token_urlsafe(18) + "Aa1!"
        payload = ok_setup(admin.post("User", {
            "userName": f"synth-{RUN}-{key}", "lastName": f"{TAG} {key}", "type": "regular", "isActive": True,
            "password": password, "passwordConfirm": password, "rolesIds": [role_ids[r] for r in roles_],
            "teamsIds": [teams[t] for t in teams_], "sendAccessInfo": False}))
        S["user_ids"][key] = payload["id"]
        S["clients"][key] = Client(f"synth-{RUN}-{key}", password)
    # hierarchy team membership is derived from roles by the setup command (production path)
    espo_console("itvolga-setup-acl")
    S["created"] = []


def ok_setup(result):
    status, payload, _ = result
    if status not in (200, 201):
        raise AssertionError(f"setup failed: HTTP {status} {json.dumps(payload, ensure_ascii=False)[:300]}")
    return payload


def tearDownModule():
    admin = S.get("admin")
    if not admin:
        return
    for entity, rid in reversed(S.get("created", [])):
        admin.delete(f"{entity}/{rid}")
    for rid in S.get("user_ids", {}).values():
        admin.delete(f"User/{rid}")


def create(entity, data, client=None, register=True):
    client = client or S["admin"]
    status, payload, _ = client.post(entity, data)
    if status == 200 and register:
        S["created"].append((entity, payload["id"]))
    return status, payload


def uid(key):
    return S["user_ids"][key]


def c(key):
    return S["clients"][key]


# ---------------------------------------------------------------------------------------------------- model
class ModelTest(unittest.TestCase):
    def test_field_map_targets_exist_in_model(self):
        """Every transfer/archive row of field-map.csv and relations.csv resolves in the EspoCRM model."""
        model = model_check.Model(REPO)
        for name, checker in (("field-map.csv", model_check.check_field_row),
                              ("relations.csv", model_check.check_relation_row)):
            with open(REPO / "docs/migration" / name, encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
            failures = []
            ok_count = 0
            for row in rows:
                res, text = checker(model, row) if name == "relations.csv" else checker(model, row, row["max_len_live"] or None)
                if res is False:
                    failures.append(f"{row.get('source_column') or row.get('relation_id')}: {text}")
                ok_count += res is True
                # the committed espo_check column must be what the model gives today
                self.assertEqual(row["espo_check"], text, f"{name}: stale espo_check, rerun build_maps.py")
            self.assertEqual(failures, [], f"{name}: targets missing in the model")
            self.assertGreater(ok_count, 100 if name == "field-map.csv" else 50)

    def test_live_metadata_equals_repository_model(self):
        """The running stand serves the merged metadata of the repository (no drift, rebuild done)."""
        model = model_check.Model(REPO)
        live = ok(self, S["admin"].get("Metadata"))
        for entity in model_check.IMPORTED + ["ActionHistoryRecord"]:
            local_fields = model.entity_defs[entity]["fields"]
            live_fields = live["entityDefs"][entity]["fields"]
            for name, defs in local_fields.items():
                self.assertIn(name, live_fields, f"{entity}.{name} missing on the stand")
                for key in ("type", "maxLength", "options", "readOnly", "optionsReference"):
                    if key in defs:
                        self.assertEqual(live_fields[name].get(key), defs[key], f"{entity}.{name}.{key}")

    def test_imported_entities_have_unique_vtiger_id(self):
        tables = {"Case": "case", "KnowledgeBaseArticle": "knowledge_base_article", "DocumentFolder": "document_folder",
                  "ProjectTask": "project_task", "VtigerArchive": "vtiger_archive", "ContactAccess": "contact_access"}
        for entity in model_check.IMPORTED:
            table = tables.get(entity, entity.lower())
            rows = sql(f"SELECT non_unique FROM information_schema.statistics WHERE table_schema=DATABASE() "
                       f"AND table_name='{table}' AND column_name='vtiger_id'")
            self.assertEqual(rows, [["0"]], f"{entity}: unique index on vtiger_id")

    def test_money_is_decimal(self):
        rows = sql("SELECT table_name, column_name, data_type FROM information_schema.columns WHERE table_schema=DATABASE() "
                   "AND ((table_name='opportunity' AND column_name='amount') OR (table_name='lead' AND column_name="
                   "'opportunity_amount') OR (table_name='product' AND column_name='unit_price') OR "
                   "(table_name='project' AND column_name='budget'))")
        self.assertEqual(len(rows), 4)
        for table, column, data_type in rows:
            self.assertEqual(data_type, "decimal", f"{table}.{column}")

    def test_value_dictionary_matches_enum_options(self):
        """Every Vtiger value maps to an option of the EspoCRM enum (D-19 dictionary, Q-32)."""
        model = model_check.Model(REPO)
        live = ok(self, S["admin"].get("Metadata"))["entityDefs"]
        for entity, data in model.value_maps.items():
            for field, spec in data["fields"].items():
                options = model.options(entity, field)
                live_def = live[entity]["fields"][field]
                ref = live_def.get("optionsReference")
                live_options = live[ref.split(".")[0]]["fields"][ref.split(".")[1]]["options"] if ref else live_def["options"]
                self.assertEqual(live_options, options, f"{entity}.{field}: stand options differ")
                for source, mapping in spec["map"].items():
                    for value, key in mapping.items():
                        self.assertIn(key, options, f"{entity}.{field}: {source}={value!r} → {key!r} not an option")


# ---------------------------------------------------------------------------------------------------- field types
class FieldTypesTest(unittest.TestCase):
    def test_account_custom_fields_roundtrip(self):
        status, acc = create("Account", {
            "name": f"{TAG} Account types", "cShortName": "ООО Синт", "cEmployees": 1250, "cRating": "Active",
            "cInn": "77-SYNTH-01", "cKpp": "770-SYNTH", "cBankAccount": "40702-810-SYNTH-0001", "cBankName": "Банк Синт",
            "cCorrAccount": "30101-810-SYNTH-0001", "cBic": "04-SYNTH", "cVkUrl": "https://vk.com/synthetic",
            "industry": "Retail", "type": "Customer", "vtigerId": 1, "vtigerNo": "X-1",
            "billingAddressStreet": "ул. Синтетическая, 1", "billingAddressCity": "Город"})
        self.assertEqual(status, 200, acc)
        got = ok(self, S["admin"].get(f"Account/{acc['id']}"))
        for k in ("cShortName", "cEmployees", "cRating", "cInn", "cKpp", "cBankAccount", "cBankName", "cCorrAccount",
                  "cBic", "cVkUrl", "industry", "type"):
            self.assertEqual(got[k], acc[k], k)
        self.assertIsNone(got["vtigerId"], "vtigerId is read-only via API")
        self.assertIsNone(got["vtigerNo"], "vtigerNo is read-only via API")

    def test_enum_rejects_unknown_option_and_labels_follow_vtiger(self):
        status, _ = create("Account", {"name": f"{TAG} bad enum", "cRating": "No such rating"})
        self.assertEqual(status, 400)
        i18n = ok(self, S["admin"].get("I18n", default="false"))
        self.assertEqual(i18n["Account"]["options"]["industry"]["Retail"], "Недвижимость")
        self.assertEqual(i18n["Case"]["options"]["status"]["New"], "Открыто")

    def test_contact_fields_address_bool_date_image(self):
        att = ok(self, S["admin"].post("Attachment", {
            "name": "synthetic.png", "type": "image/png", "role": "Attachment", "relatedType": "Contact",
            "field": "cPhoto", "file": "data:image/png;base64," + base64.b64encode(
                bytes.fromhex("89504e470d0a1a0a0000000d4948445200000001000000010806000000"
                              "1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082")).decode()}))
        status, con = create("Contact", {
            "lastName": f"{TAG} Contact", "cLeadSource": "Web Site", "cDepartment": "Отдел синтетики",
            "cBirthday": "1990-02-03", "cSupportStartDate": "2024-01-01", "cSupportEndDate": "2024-12-31",
            "cNeedOriginalDocs": True, "cSendNews": False, "cPartnerAds": True, "cSendAlerts": True,
            "cOtherAddressStreet": "Другая, 2", "cOtherAddressCity": "Другой город", "cOtherAddressPostalCode": "000000",
            "salutationName": "Prof.", "cPhotoId": att["id"], "cVkUrl": "vk.com/synthetic"})
        self.assertEqual(status, 200, con)
        got = ok(self, S["admin"].get(f"Contact/{con['id']}"))
        for k in ("cLeadSource", "cDepartment", "cBirthday", "cSupportStartDate", "cSupportEndDate", "cNeedOriginalDocs",
                  "cSendNews", "cPartnerAds", "cSendAlerts", "cOtherAddressStreet", "cOtherAddressCity",
                  "cOtherAddressPostalCode", "salutationName", "cPhotoId", "cVkUrl"):
            self.assertEqual(got[k], con[k], k)

    def test_lead_opportunity_task_call_fields(self):
        status, lead = create("Lead", {"lastName": f"{TAG} Lead", "status": "Hot", "source": "Jivosite",
                                       "cPriority": "VIP", "cRating": "Acquired", "cJivositeId": 9774,
                                       "industry": "Типографии"})
        self.assertEqual(status, 200, lead)
        self.assertEqual(ok(self, S["admin"].get(f"Lead/{lead['id']}"))["cJivositeId"], 9774)
        status, prod = create("Product", {"name": f"{TAG} Service", "type": "service", "unitPrice": 1234.56,
                                          "unitPriceCurrency": "RUB", "unit": "Hours", "qtyPerUnit": 10000,
                                          "category": "Support", "isBillableTime": True, "code": "S1"})
        self.assertEqual(status, 200, prod)
        status, opp = create("Opportunity", {"name": f"{TAG} Opp", "stage": "Переговоры", "cOpportunityType": "New Business",
                                             "leadSource": "Cold Call", "closeDate": "2025-05-06", "amount": 100,
                                             "amountCurrency": "RUB", "cProductsIds": [prod["id"]]})
        self.assertEqual(status, 200, opp)
        self.assertEqual(ok(self, S["admin"].get(f"Opportunity/{opp['id']}"))["probability"], 80,
                         "probabilityMap follows Vtiger stages")
        related = ok(self, S["admin"].get(f"Opportunity/{opp['id']}/cProducts"))
        self.assertEqual([r["id"] for r in related["list"]], [prod["id"]])
        status, task = create("Task", {"name": f"{TAG} Письмо", "cTaskType": "Письмо", "status": "Planned",
                                       "priority": "", "parentType": "Lead", "parentId": lead["id"],
                                       "assignedUserId": uid("dir")})
        self.assertEqual(status, 200, task)
        status, call = create("Call", {"name": f"{TAG} Call", "status": "Held", "direction": "Inbound",
                                       "dateStart": "2024-07-30 10:00:00", "duration": 300, "cPhoneNumber": "SYNTH-0001",
                                       "assignedUserId": uid("dir")})
        self.assertEqual(status, 200, call)
        self.assertIsNone(ok(self, S["admin"].get(f"Call/{call['id']}"))["cPhoneNumber"],
                          "telephony history fields are read-only via API")

    def test_knowledge_base_name_500_and_case_fields(self):
        status, kb = create("KnowledgeBaseArticle", {"name": "Я" * 500, "status": "In Review", "cTags": ["синт", "тег"]})
        self.assertEqual(status, 200, kb)
        status, _ = create("KnowledgeBaseArticle", {"name": "Я" * 501})
        self.assertEqual(status, 400, "maxLength 500 is enforced")
        status, case = create("Case", {"name": f"{TAG} Case", "status": "Pending", "priority": "High",
                                       "type": "Big Problem", "cSeverity": "Minor", "cSolution": "Решение",
                                       "cTags": ["синт"], "cDocumentsIds": []})
        self.assertEqual(status, 200, case)

    def test_project_task_vendor_archive_types(self):
        status, vendor = create("Vendor", {"name": f"{TAG} Vendor", "inn": "1234-SYNTH-12", "website": "example.org",
                                           "emailAddress": "vendor@example.org"})
        self.assertEqual(status, 200, vendor)
        # Project/ProjectTask are read-only archives for every role; the admin (import) may write.
        status, proj = create("Project", {"name": f"{TAG} Project", "status": "completed", "type": "Административное",
                                          "priority": "Высокий", "progress": "100%", "budget": 100000.0,
                                          "budgetCurrency": "RUB", "dateStart": "2019-03-16", "dateEnd": "2023-06-01",
                                          "url": "https://example.org"})
        self.assertEqual(status, 200, proj)
        status, pt = create("ProjectTask", {"name": f"{TAG} PT", "projectId": proj["id"], "status": "Canceled",
                                            "priority": "normal", "type": "operative", "progress": "40%", "hours": 1500,
                                            "showInStat": True, "gitCommit": "https://git.example.org/c/abc",
                                            "tags": ["git"], "orderNumber": 2})
        self.assertEqual(status, 200, pt)
        self.assertEqual(ok(self, S["admin"].get(f"ProjectTask/{pt['id']}"))["hours"], 1500)
        status, _ = create("VtigerArchive", {"name": "x"})
        self.assertEqual(status, 403, "VtigerArchive has no create action (import only)")

    def test_vtiger_data_visible_to_admin_only(self):
        status, acc = create("Account", {"name": f"{TAG} vtigerData", "assignedUserId": uid("dir")})
        self.assertEqual(status, 200, acc)
        sql(f"UPDATE account SET vtiger_data='{{\"ownership\":\"synthetic\"}}', vtiger_id={vt_id(1)} WHERE id='{acc['id']}'")
        self.assertEqual(ok(self, S["admin"].get(f"Account/{acc['id']}"))["vtigerData"], {"ownership": "synthetic"})
        as_dir = ok(self, c("dir").get(f"Account/{acc['id']}"))
        self.assertNotIn("vtigerData", as_dir, "vtigerData is onlyAdmin")
        self.assertEqual(as_dir["vtigerId"], vt_id(1))
        ok(self, S["admin"].put(f"Account/{acc['id']}", {"vtigerData": {"x": 1}, "vtigerId": 5}))
        again = ok(self, S["admin"].get(f"Account/{acc['id']}"))
        self.assertEqual((again["vtigerData"], again["vtigerId"]), ({"ownership": "synthetic"}, vt_id(1)))

    def test_vtiger_id_is_unique(self):
        status, a1 = create("Lead", {"lastName": f"{TAG} dup 1"})
        status, a2 = create("Lead", {"lastName": f"{TAG} dup 2"})
        self.assertEqual(status, 200, a2)
        sql(f"UPDATE `lead` SET vtiger_id={vt_id(2)} WHERE id='{a1['id']}'")
        with self.assertRaises(Exception):
            sql(f"UPDATE `lead` SET vtiger_id={vt_id(2)} WHERE id='{a2['id']}'")


# ---------------------------------------------------------------------------------------------------- ACL
class AclTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        a = S["admin"]
        cls.acc_dir = ok_setup(a.post("Account", {"name": f"{TAG} acc dir", "assignedUserId": uid("dir")}))["id"]
        cls.acc_dep1 = ok_setup(a.post("Account", {"name": f"{TAG} acc dep1", "assignedUserId": uid("dep1")}))["id"]
        cls.con_dep1 = ok_setup(a.post("Contact", {"lastName": f"{TAG} con dep1", "assignedUserId": uid("dep1")}))["id"]
        cls.con_group = ok_setup(a.post("Contact", {"lastName": f"{TAG} con group",
                                                    "teamsIds": [S["teams"]["Отдел Поддержки"]]}))["id"]
        cls.case_cust = ok_setup(a.post("Case", {"name": f"{TAG} case cust", "assignedUserId": uid("cust")}))["id"]
        cls.task_sales = ok_setup(a.post("Task", {"name": f"{TAG} task sales", "assignedUserId": uid("sales")}))["id"]
        cls.lead = ok_setup(a.post("Lead", {"lastName": f"{TAG} lead", "assignedUserId": uid("dir")}))["id"]
        cls.opp = ok_setup(a.post("Opportunity", {"name": f"{TAG} opp", "stage": "Qualification",
                                                  "closeDate": "2025-01-01", "assignedUserId": uid("dir")}))["id"]
        cls.kb = ok_setup(a.post("KnowledgeBaseArticle", {"name": f"{TAG} kb", "assignedUserId": uid("dir")}))["id"]
        cls.proj = ok_setup(a.post("Project", {"name": f"{TAG} proj", "assignedUserId": uid("cust")}))["id"]
        cls.vendor = ok_setup(a.post("Vendor", {"name": f"{TAG} vendor"}))["id"]
        for entity, rid in (("Account", cls.acc_dir), ("Account", cls.acc_dep1), ("Contact", cls.con_dep1),
                            ("Contact", cls.con_group), ("Case", cls.case_cust), ("Task", cls.task_sales),
                            ("Lead", cls.lead), ("Opportunity", cls.opp), ("KnowledgeBaseArticle", cls.kb),
                            ("Project", cls.proj), ("Vendor", cls.vendor)):
            S["created"].append((entity, rid))

    def assertRead(self, user, entity, rid, allowed):
        status = c(user).get(f"{entity}/{rid}")[0]
        self.assertEqual(status, 200 if allowed else 403, f"{user} read {entity}: HTTP {status}")

    def test_director_reads_everything_but_contact_access(self):
        for entity, rid in (("Account", self.acc_dep1), ("Contact", self.con_dep1), ("Case", self.case_cust),
                            ("Lead", self.lead), ("Opportunity", self.opp), ("Vendor", self.vendor),
                            ("Project", self.proj)):
            self.assertRead("dir", entity, rid, True)
        self.assertEqual(c("dir").get("ContactAccess")[0], 403)

    def test_deputy_private_modules_follow_vtiger_sharing(self):
        self.assertRead("dep1", "Account", self.acc_dir, False)     # director's record: not visible (Private)
        self.assertRead("dep1", "Account", self.acc_dep1, True)     # own
        self.assertRead("dep2", "Account", self.acc_dep1, False)    # another deputy's account: no sharing rule
        self.assertRead("dep2", "Contact", self.con_dep1, True)     # sharing rule H3→H3 Contacts (read-write)
        self.assertEqual(c("dep2").put(f"Contact/{self.con_dep1}", {"title": "synthetic"})[0], 200)
        self.assertRead("dep1", "Contact", self.con_group, True)    # group «Отдел Поддержки»
        self.assertRead("cust", "Contact", self.con_group, False)
        self.assertRead("dep1", "Case", self.case_cust, True)       # subordinate (Менеджер клиентов)
        self.assertRead("dep1", "Task", self.task_sales, True)      # subordinate (Менеджер по продажам)
        self.assertRead("cust", "Task", self.task_sales, False)     # sibling roles do not see each other

    def test_hidden_modules_per_role(self):
        for user, entity, rid in (("dep1", "Lead", self.lead), ("dep1", "Opportunity", self.opp),
                                  ("dep1", "Vendor", self.vendor), ("sales", "Account", self.acc_dir),
                                  ("sales", "Case", self.case_cust), ("sales", "Opportunity", self.opp),
                                  ("cust", "Lead", self.lead), ("cust", "Account", self.acc_dir)):
            self.assertRead(user, entity, rid, False)
        self.assertRead("sales", "Lead", self.lead, True)            # Leads are Public in Vtiger
        self.assertRead("cust", "KnowledgeBaseArticle", self.kb, True)
        for user in ("dep1", "dep2", "sales", "cust", "access", "norole"):
            self.assertEqual(c(user).get("VtigerArchive")[0], 403, user)

    def test_standard_action_restrictions(self):
        self.assertEqual(c("dep1").delete(f"KnowledgeBaseArticle/{self.kb}")[0], 403)  # Faq delete denied
        self.assertRead("dep1", "Project", self.proj, True)                            # subordinate's project
        self.assertEqual(c("dep1").put(f"Project/{self.proj}", {"name": "x"})[0], 403)  # archive: read-only
        self.assertEqual(c("dir").post("Project", {"name": "x"})[0], 403)
        self.assertEqual(c("dir").post("ProjectTask", {"name": "x"})[0], 403)

    def test_user_without_roles_has_no_access(self):
        for entity in ("Account", "Contact", "Lead", "Case", "Task", "Product", "ContactAccess", "Project"):
            self.assertEqual(c("norole").get(entity)[0], 403, entity)

    def test_hierarchy_team_follows_assigned_user(self):
        team = S["teams"]["Подчинённые заместителей"]
        status, task = create("Task", {"name": f"{TAG} hierarchy", "assignedUserId": uid("sales")}, client=c("sales"))
        self.assertEqual(status, 200, task)
        self.assertIn(team, ok(self, S["admin"].get(f"Task/{task['id']}"))["teamsIds"])
        self.assertRead("dep1", "Task", task["id"], True)
        ok(self, S["admin"].put(f"Task/{task['id']}", {"assignedUserId": uid("dir")}))
        self.assertNotIn(team, ok(self, S["admin"].get(f"Task/{task['id']}"))["teamsIds"])
        self.assertRead("dep1", "Task", task["id"], False)

    def test_telephony_history_mass_actions_are_denied(self):
        a = S["admin"]
        pbx = ok(self, a.post("Call", {"name": f"{TAG} pbx mass", "status": "Held", "dateStart": "2020-02-01 10:00:00",
                                       "assignedUserId": uid("dep1")}))
        cal = ok(self, a.post("Call", {"name": f"{TAG} cal mass", "status": "Planned", "dateStart": "2020-02-01 11:00:00",
                                       "assignedUserId": uid("dep1")}))
        S["created"] += [("Call", pbx["id"]), ("Call", cal["id"])]
        sql(f"UPDATE `call` SET c_connector_call_id='998' WHERE id='{pbx['id']}'")
        result = ok(self, c("dep1").post("MassAction", {"entityType": "Call", "action": "update",
                                                        "params": {"ids": [pbx["id"], cal["id"]]},
                                                        "data": {"description": "mass"}}))
        self.assertEqual(result.get("count"), 1, "only the calendar call is updated")
        self.assertIsNone(ok(self, a.get(f"Call/{pbx['id']}"))["description"])
        ok(self, c("dep1").post("MassAction", {"entityType": "Call", "action": "delete", "params": {"ids": [pbx["id"]]}}))
        self.assertEqual(a.get(f"Call/{pbx['id']}")[0], 200, "history call survives mass delete")

    def test_hierarchy_team_cannot_be_removed_by_editing_teams(self):
        team = S["teams"]["Подчинённые заместителей"]
        status, task = create("Task", {"name": f"{TAG} keep team", "assignedUserId": uid("sales")}, client=c("sales"))
        self.assertEqual(status, 200, task)
        ok(self, c("sales").put(f"Task/{task['id']}", {"teamsIds": []}))
        self.assertIn(team, ok(self, S["admin"].get(f"Task/{task['id']}"))["teamsIds"])
        self.assertEqual(c("sales").request("DELETE", f"Task/{task['id']}/teams", {"id": team})[0], 403)
        self.assertRead("dep1", "Task", task["id"], True)

    def test_hierarchy_membership_follows_role_change_at_once(self):
        a = S["admin"]
        roles = {r["name"]: r["id"] for r in a.get("Role", maxSize=50)[1]["list"]}
        password = secrets.token_urlsafe(18) + "Aa1!"
        user = ok(self, a.post("User", {"userName": f"synth-{RUN}-member2", "lastName": f"{TAG} member2",
                                        "type": "regular", "password": password, "passwordConfirm": password,
                                        "rolesIds": [roles["Заместитель директора"]]}))
        S["user_ids"]["member2"] = user["id"]
        team = S["teams"]["Подчинённые заместителей"]

        def member():
            return any(u["id"] == user["id"] for u in ok(self, a.get(f"Team/{team}/users", maxSize=200))["list"])

        self.assertTrue(member(), "joins on creation, without the console command")
        ok(self, a.put(f"User/{user['id']}", {"rolesIds": []}))
        self.assertFalse(member(), "leaves as soon as the role is removed")

    def test_hierarchy_membership_follows_roles(self):
        """itvolga-setup-acl: holders of the superior role join hierarchy teams and leave them without it."""
        a = S["admin"]
        roles = {r["name"]: r["id"] for r in a.get("Role", maxSize=50)[1]["list"]}
        password = secrets.token_urlsafe(18) + "Aa1!"
        user = ok(self, a.post("User", {"userName": f"synth-{RUN}-member", "lastName": f"{TAG} member",
                                        "type": "regular", "password": password, "passwordConfirm": password,
                                        "rolesIds": [roles["Заместитель директора"]]}))
        S["user_ids"]["member"] = user["id"]
        team = S["teams"]["Подчинённые заместителей"]

        def member():
            return any(u["id"] == user["id"] for u in ok(self, a.get(f"Team/{team}/users", maxSize=200))["list"])

        espo_console("itvolga-setup-acl")
        self.assertTrue(member())
        ok(self, a.put(f"User/{user['id']}", {"rolesIds": []}))
        espo_console("itvolga-setup-acl")
        self.assertFalse(member())

    def test_telephony_history_is_read_only(self):
        status, call = create("Call", {"name": f"{TAG} pbx", "status": "Held", "dateStart": "2020-01-01 10:00:00",
                                       "assignedUserId": uid("dep1")})
        status2, cal = create("Call", {"name": f"{TAG} calendar call", "status": "Planned",
                                       "dateStart": "2020-01-01 11:00:00", "assignedUserId": uid("dep1")})
        sql(f"UPDATE `call` SET c_connector_call_id='999' WHERE id='{call['id']}'")
        self.assertEqual(c("dep1").put(f"Call/{call['id']}", {"description": "x"})[0], 403)
        self.assertEqual(c("dep1").delete(f"Call/{call['id']}")[0], 403)
        self.assertEqual(c("dep1").put(f"Call/{cal['id']}", {"description": "x"})[0], 200)
        self.assertEqual(S["admin"].put(f"Call/{call['id']}", {"description": "admin"})[0], 200)


# ---------------------------------------------------------------------------------------------------- attachments
class AttachmentAccessTest(unittest.TestCase):
    """Files follow the access to their record (Vtiger: attachments are visible with the record)."""
    PNG = base64.b64encode(bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360000002000154a2"
        "4f5d0000000049454e44ae426082")).decode()

    @classmethod
    def upload(cls, related_type, field, role="Attachment", name="synthetic.png"):
        return ok_setup(S["admin"].post("Attachment", {
            "name": name, "type": "image/png", "role": role, "relatedType": related_type, "field": field,
            "file": "data:image/png;base64," + cls.PNG}))["id"]

    @classmethod
    def setUpClass(cls):
        a = S["admin"]
        cls.doc_file = cls.upload("Document", "file")
        doc = ok_setup(a.post("Document", {"name": f"{TAG} doc", "fileId": cls.doc_file, "status": "Active",
                                           "assignedUserId": uid("dir")}))
        cls.acc = ok_setup(a.post("Account", {"name": f"{TAG} acc with note", "assignedUserId": uid("dir")}))["id"]
        cls.note_file = cls.upload("Note", "attachments")
        note = ok_setup(a.post("Note", {"type": "Post", "parentType": "Account", "parentId": cls.acc,
                                        "post": f"{TAG} comment", "attachmentsIds": [cls.note_file]}))
        cls.photo = cls.upload("Contact", "cPhoto")
        con = ok_setup(a.post("Contact", {"lastName": f"{TAG} photo", "cPhotoId": cls.photo,
                                          "assignedUserId": uid("dep1")}))
        for entity, rid in (("Document", doc["id"]), ("Note", note["id"]), ("Account", cls.acc), ("Contact", con["id"])):
            S["created"].append((entity, rid))

    def download(self, user, attachment_id):
        return c(user).get(f"Attachment/file/{attachment_id}")[0]

    def test_document_file_follows_document_access(self):
        self.assertEqual(self.download("dir", self.doc_file), 200)
        self.assertEqual(self.download("dep1", self.doc_file), 403)   # director's document (Private)
        self.assertEqual(self.download("sales", self.doc_file), 403)  # no Documents at all
        self.assertEqual(self.download("norole", self.doc_file), 403)

    def test_comment_attachment_follows_parent_record(self):
        self.assertEqual(self.download("dir", self.note_file), 200)
        self.assertEqual(self.download("dep1", self.note_file), 403)  # parent account is not visible

    def test_contact_photo_follows_contact_access(self):
        self.assertEqual(self.download("dep1", self.photo), 200)
        self.assertEqual(self.download("dep2", self.photo), 200)      # sharing rule H3→H3 for Contacts
        self.assertEqual(self.download("cust", self.photo), 403)      # no Contacts for Менеджер клиентов


# ---------------------------------------------------------------------------------------------------- ContactAccess
class ContactAccessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        a = S["admin"]
        cls.contact = ok_setup(a.post("Contact", {"lastName": f"{TAG} access contact", "assignedUserId": uid("access")}))["id"]
        S["created"].append(("Contact", cls.contact))
        status, rec, _ = c("access").post("ContactAccess", {
            "contactId": cls.contact, "anydeskId": "123 456 789", "anydeskPassword": PASSWORD_PLAIN,
            "hostname": "synthetic-pc", "ipAddress": "ip-synthetic"})
        assert status == 200, f"ContactAccess create failed: HTTP {status}"
        cls.rec = rec
        S["created"].append(("ContactAccess", rec["id"]))

    def test_password_never_returned_and_encrypted_at_rest(self):
        self.assertNotIn("anydeskPassword", self.rec)
        got = ok(self, c("access").get(f"ContactAccess/{self.rec['id']}"))
        self.assertNotIn("anydeskPassword", got)
        self.assertTrue(got["hasAnydeskPassword"])
        self.assertEqual(got["name"], f"Доступ: {TAG} access contact")
        listed = ok(self, c("access").get("ContactAccess", select="id,anydeskPassword,name"))
        self.assertTrue(all("anydeskPassword" not in r for r in listed["list"]))
        stored = sql(f"SELECT anydesk_password FROM contact_access WHERE id='{self.rec['id']}'")[0][0]
        self.assertNotEqual(stored, PASSWORD_PLAIN)
        self.assertNotIn(PASSWORD_PLAIN, stored)
        self.assertGreaterEqual(len(base64.b64decode(stored)), 32, "AES-256-CBC ciphertext + IV")

    def test_reveal_returns_plain_value_and_is_logged(self):
        before = int(sql(f"SELECT COUNT(*) FROM action_history_record WHERE action='reveal' AND target_id='{self.rec['id']}'")[0][0])
        status, payload, headers = c("access").post(f"ContactAccess/{self.rec['id']}/password")
        self.assertEqual((status, payload["password"]), (200, PASSWORD_PLAIN))
        self.assertIn("no-store", headers.get("Cache-Control", ""))
        rows = sql(f"SELECT user_id, target_type FROM action_history_record WHERE action='reveal' "
                   f"AND target_id='{self.rec['id']}' ORDER BY number DESC")
        self.assertEqual(len(rows), before + 1)
        self.assertEqual(rows[0], [uid("access"), "ContactAccess"])
        # the admin bypasses ACL, the reveal is still logged
        self.assertEqual(S["admin"].post(f"ContactAccess/{self.rec['id']}/password")[0], 200)
        self.assertEqual(len(sql(f"SELECT 1 FROM action_history_record WHERE action='reveal' AND target_id='{self.rec['id']}'")),
                         before + 2)

    def test_other_users_have_no_access(self):
        for user in ("dir", "dep1", "dep2", "sales", "cust", "norole"):
            self.assertEqual(c(user).get(f"ContactAccess/{self.rec['id']}")[0], 403, user)
            self.assertEqual(c(user).post(f"ContactAccess/{self.rec['id']}/password")[0], 403, user)
            self.assertEqual(c(user).get(f"Contact/{self.contact}/cContactAccesses")[0], 403, user)

    def test_export_mass_update_search_and_stream_are_closed(self):
        status = c("access").post("Export", {"entityType": "ContactAccess", "ids": [self.rec["id"]], "format": "csv"})[0]
        self.assertEqual(status, 403, "export disabled for ContactAccess")
        status = c("access").post("MassAction", {"entityType": "ContactAccess", "action": "update",
                                                 "params": {"ids": [self.rec["id"]]}, "data": {"hostname": "x"}})[0]
        self.assertIn(status, (400, 403), "mass actions disabled")
        status = c("access").get("ContactAccess", **{"where[0][type]": "equals", "where[0][attribute]": "anydeskPassword",
                                                      "where[0][value]": PASSWORD_PLAIN})[0]
        self.assertIn(status, (400, 403), "no filtering by the password")
        found = ok(self, c("access").get("ContactAccess", q=PASSWORD_PLAIN))
        self.assertEqual(found["list"], [], "text search does not look into the password")
        notes = sql(f"SELECT COUNT(*) FROM note WHERE (parent_id='{self.contact}' AND related_type='ContactAccess') "
                    f"OR parent_type='ContactAccess' OR related_id='{self.rec['id']}'")
        self.assertEqual(notes, [["0"]], "no stream notes about ContactAccess")
        audit = sql(f"SELECT COUNT(*) FROM note WHERE post LIKE '%{PASSWORD_PLAIN}%' OR data LIKE '%{PASSWORD_PLAIN}%'")
        self.assertEqual(audit, [["0"]])

    def test_change_clear_and_length_limit(self):
        status, rec = create("ContactAccess", {"contactId": self.contact, "anydeskPassword": "first"}, client=c("access"))
        self.assertEqual(status, 200, rec)
        ok(self, c("access").put(f"ContactAccess/{rec['id']}", {"anydeskPassword": "second"}))
        self.assertEqual(c("access").post(f"ContactAccess/{rec['id']}/password")[1]["password"], "second")
        ok(self, c("access").put(f"ContactAccess/{rec['id']}", {"hostname": "renamed"}))  # other field: password kept
        self.assertEqual(c("access").post(f"ContactAccess/{rec['id']}/password")[1]["password"], "second")
        ok(self, c("access").put(f"ContactAccess/{rec['id']}", {"anydeskPassword": ""}))
        got = ok(self, c("access").get(f"ContactAccess/{rec['id']}"))
        self.assertFalse(got["hasAnydeskPassword"])
        self.assertIsNone(c("access").post(f"ContactAccess/{rec['id']}/password")[1]["password"])
        self.assertEqual(c("access").put(f"ContactAccess/{rec['id']}", {"anydeskPassword": "x" * 101})[0], 400)

    def test_long_multibyte_and_spaced_passwords_roundtrip(self):
        for value in ("Ж" * 100, "  spaced value  ", "𝔘" * 100):
            status, rec = create("ContactAccess", {"contactId": self.contact, "anydeskPassword": value}, client=c("access"))
            self.assertEqual(status, 200, rec)
            self.assertEqual(c("access").post(f"ContactAccess/{rec['id']}/password")[1]["password"], value)

    def test_encryption_runs_after_before_save_formula(self):
        order = lambda path, rx: int(__import__("re").search(rx, Path(path).read_text()).group(1))  # noqa: E731
        ours = order(REPO / "custom/Espo/Modules/Itvolga/Hooks/ContactAccess/ProtectPassword.php", r"\$order = (\d+)")
        formula = order(REPO / "application/Espo/Hooks/Common/Formula.php", r"\$order = (\d+)")
        self.assertGreater(ours, formula)

    def test_no_webhooks_for_contact_access(self):
        status, payload, _ = S["admin"].post("Webhook", {"event": "ContactAccess.create", "url": "https://example.org/x",
                                                          "isActive": False})
        if status in (200, 201):
            S["admin"].delete(f"Webhook/{payload['id']}")
        self.assertEqual(status, 403)
        live = ok(self, S["admin"].get("Metadata"))
        self.assertFalse(live["scopes"]["ContactAccess"].get("object"), "no webhook events, no related stream notes")

    def test_read_is_audited(self):
        c("access").get(f"ContactAccess/{self.rec['id']}")
        rows = sql(f"SELECT COUNT(*) FROM action_history_record WHERE action='read' AND target_id='{self.rec['id']}' "
                   f"AND user_id='{uid('access')}'")
        self.assertGreaterEqual(int(rows[0][0]), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
