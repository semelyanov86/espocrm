"""Stage 05.1 acceptance tests: access to reports and to the data a report shows (D-87, D-89, D-99), synthetic data.

  task test:stage05.1   (python3 -m unittest discover -s tests/stage05_1 -v)

Visibility: a matrix of users (owner, another director, a listed user, a member of a listed team, a «Доступы»-only user
who is also a member of that team, the deputy, the administrator) × reports (private, public, shared with a user and a
team, shared with the «Доступы» user): `GET Report` lists a report ⇔ `GET Report/:id` gives 200 ⇔ its run is not
refused (when the user reads the entity). Editing and deleting are for the owner and administrators; only an
administrator gives a report to another owner; the «Доступы» role reads but does not create.

Data: an entity the user may not read is refused with 403 and is absent from the catalog; a field closed by the field
ACL (Invoice.grandTotal) is refused with 403 wherever a report uses it — columns, groups, aggregates, sorting, totals,
calculations, conditions, HAVING, quick filters, a one-off run and a drill-down — when saving and when running a report
someone else saved; a closed link (Invoice.account) and a closed field of a related entity likewise; related records
the user may not read (contacts of «read own») add no rows and do not match conditions, in reports and in the core list
with the where item `itvolgaRelated`. ContactAccess is reported only with «Доступы», and its password never appears.
"""
import json
import unittest

from fixture import READ, World, all_of, cond, drill_down, espo_console, label, list_ids, run, sql

S = {}
USERS = ("owner", "admin", "dir2", "listed", "member", "access", "deputy", "readall")
READS_ACCOUNT = {"owner", "admin", "dir2", "listed", "member", "deputy", "readall"}


def setUpModule():
    w = World()
    unittest.addModuleCleanup(w.cleanup)
    S["w"] = w
    team = w.team("team")
    S["team"] = team
    w.user("owner", roles=["Директор"])
    w.user("dir2", roles=["Директор"])
    w.user("listed", roles=["Директор"])
    w.user("member", roles=["Директор"], teams=[team])
    w.user("access", roles=["Доступы"], teams=[team])
    w.user("deputy", roles=["Заместитель директора"])
    w.user("both", roles=["Директор", "Доступы"])

    finance = {"Invoice": READ, "InvoiceItem": {"read": "all"}, "Account": READ, "Contact": READ, "Product": READ}
    w.user("nototal", role_ids=[w.role("nototal", finance, {"Invoice": {"grandTotal": {"read": "no", "edit": "no"}}})])
    w.user("noaccount", role_ids=[w.role("noaccount", finance, {"Invoice": {"account": {"read": "no", "edit": "no"}}})])
    w.user("noinn", role_ids=[w.role("noinn", finance, {"Account": {"cInn": {"read": "no", "edit": "no"}}})])
    own_contacts = {"Account": READ, "Contact": {"create": "no", "read": "own", "edit": "no", "delete": "no"}}
    w.user("own", role_ids=[w.role("own", own_contacts)])
    # Read level `all`: shared reports of any list, never private ones (only the mandatory filter keeps them out).
    w.user("readall", role_ids=[w.role("readall", {
        "Report": {"create": "yes", "read": "all", "edit": "own", "delete": "own"}, "Account": READ})])
    w.user("nostart", role_ids=[w.role("nostart", {"Task": READ},
                                       {"Task": {"dateStart": {"read": "no", "edit": "no"}}})])
    espo_console("clear-cache")

    S["account"] = w.create("Account", {"name": f"{w.tag} acl", "cInn": "77-SYNTH-ACL"}, by="owner")["id"]
    product = w.create("Product", {"name": f"{w.tag} acl", "type": "service"}, by="owner")["id"]
    S["invoice"] = w.create("Invoice", {
        "name": f"{w.tag} acl", "accountId": S["account"], "dateInvoiced": "2026-10-01", "dateDue": "2026-10-15",
        "assignedUserId": w.uid["owner"], "itemList": [{"productId": product, "quantity": "1", "unitPrice": "100"}]},
        by="owner")["id"]


def W():
    return S["w"]


def account_report(name, **extra):
    return W().report("owner", name, entityType="Account", columns=["name"], filters=all_of(W().name_filter()),
                      **extra)["id"]


class Case(unittest.TestCase):
    def ok(self, result):
        status, payload, _ = result
        self.assertEqual(200, status, f"HTTP {status}: {payload}")
        return payload

    def assertRefusedList(self, result):
        """A core list refused for a closed field or link: the record service turns a Forbidden of the select
        builder into 400 (Record\\Service::find), so either code counts — what matters is that no records come back."""
        self.assertIn(result[0], (400, 403))
        self.assertIsNone(result[1])

    def refused(self, result, status=403, key=None, msg=None):
        self.assertEqual(status, result[0], msg or f"expected HTTP {status}, got {result[0]}: {result[1]}")
        if key:
            self.assertEqual(key, label(result), msg)


class VisibilityTest(Case):
    @classmethod
    def setUpClass(cls):
        w = W()
        cls.reports = {
            "private": account_report("private"),
            "public": account_report("public", accessType="public"),
            "shared": account_report("shared", accessType="shared", sharedUsersIds=[w.uid["listed"]],
                                     sharedTeamsIds=[S["team"]]),
            "sharedAccess": account_report("shared access", accessType="shared", sharedUsersIds=[w.uid["access"]]),
        }
        cls.visible = {
            "private": {"owner", "admin"},
            "public": set(USERS),
            # The «Доступы» user is in the team too, but his read level is `own`: only a personal listing counts.
            "shared": {"owner", "admin", "listed", "member", "readall"},
            "sharedAccess": {"owner", "admin", "access", "readall"},
        }

    def listed_ids(self, client):
        params = {"where[0][type]": "startsWith", "where[0][attribute]": "name", "where[0][value]": W().tag,
                  "maxSize": 200, "select": "id,name"}
        return {r["id"] for r in self.ok(client.get("Report", **params))["list"]}

    def test_list_read_and_run_agree_with_the_sharing_rules(self):
        for user in USERS:
            client = W().client(user)
            in_list = self.listed_ids(client)
            for kind, rid in self.reports.items():
                with self.subTest(user=user, report=kind):
                    expected = user in self.visible[kind]
                    self.assertEqual(expected, rid in in_list, "list")
                    self.assertEqual(200 if expected else 403, client.get(f"Report/{rid}")[0], "read")
                    can_run = expected and user in READS_ACCOUNT
                    self.assertEqual(200 if can_run else 403, run(client, rid)[0], "run")

    def test_the_sharing_lists_change_only_through_the_report(self):
        """Link and unlink of the sharing relations bypass the save checks (a shared report with an empty list), so they
        are closed from both sides, for administrators too (external review W2, 2026-10-04)."""
        w = W()
        rid = account_report("links", accessType="shared", sharedUsersIds=[w.uid["listed"]])
        listed = w.uid["listed"]
        self.assertEqual(403, w.admin.request("DELETE", f"Report/{rid}/sharedUsers", {"id": listed})[0])
        self.assertEqual(403, w.admin.post(f"Report/{rid}/sharedTeams", {"id": S["team"]})[0])
        self.assertEqual(403, w.admin.post(f"User/{w.uid['dir2']}/cSharedReports", {"id": rid})[0])
        self.assertEqual(403, w.admin.post(f"Team/{S['team']}/cSharedReports", {"id": rid})[0])
        self.assertEqual([listed], self.ok(w.admin.get(f"Report/{rid}"))["sharedUsersIds"])
        # The report itself still changes its lists.
        self.ok(w.client("owner").put(f"Report/{rid}", {"sharedUsersIds": [w.uid["dir2"]]}))
        self.assertEqual([w.uid["dir2"]], self.ok(w.admin.get(f"Report/{rid}"))["sharedUsersIds"])

    def test_lists_of_a_report_count_only_while_it_is_shared(self):
        w = W()
        rid = account_report("switch", accessType="shared", sharedUsersIds=[w.uid["listed"]])
        listed = w.client("listed")
        self.ok(listed.get(f"Report/{rid}"))
        self.ok(w.client("owner").put(f"Report/{rid}", {"accessType": "private"}))
        self.assertEqual(403, listed.get(f"Report/{rid}")[0])
        self.assertEqual([], self.ok(w.admin.get(f"Report/{rid}")).get("sharedUsersIds"))
        self.refused(w.client("owner").put(f"Report/{rid}", {"accessType": "shared"}), 400, "sharedNeedsList")
        self.refused(w.try_report("owner", "nobody", entityType="Account", columns=["name"], accessType="shared"),
                     400, "sharedNeedsList")

    def test_only_the_owner_and_administrators_edit_and_delete(self):
        w = W()
        public, shared = self.reports["public"], self.reports["shared"]
        for user, rid in (("dir2", public), ("listed", shared), ("member", shared), ("access", public),
                          ("deputy", public)):
            with self.subTest(user=user):
                self.refused(w.client(user).put(f"Report/{rid}", {"description": "changed"}), 403)
                self.refused(w.client(user).delete(f"Report/{rid}"), 403)
        self.ok(w.client("owner").put(f"Report/{public}", {"description": "by the owner"}))
        self.ok(w.admin.put(f"Report/{public}", {"description": "by the administrator"}))
        doomed = account_report("doomed", accessType="public")
        self.ok(w.client("owner").delete(f"Report/{doomed}"))
        self.assertEqual(404, w.client("owner").get(f"Report/{doomed}")[0])
        self.assertNotIn(doomed, self.listed_ids(w.client("dir2")))

    def test_only_an_administrator_gives_a_report_to_another_owner(self):
        w = W()
        self.refused(w.try_report("owner", "for dir2", entityType="Account", columns=["name"],
                                  assignedUserId=w.uid["dir2"]), 403)
        rid = account_report("mine")
        self.refused(w.client("owner").put(f"Report/{rid}", {"assignedUserId": w.uid["dir2"]}), 403)
        self.assertEqual(w.uid["owner"], self.ok(w.admin.get(f"Report/{rid}"))["assignedUserId"])
        given = w.report("admin", "given", entityType="Account", columns=["name"], assignedUserId=w.uid["dir2"])
        self.ok(w.client("dir2").get(f"Report/{given['id']}"))
        self.ok(w.admin.put(f"Report/{rid}", {"assignedUserId": w.uid["dir2"]}))
        self.ok(w.client("dir2").get(f"Report/{rid}"))
        self.refused(w.client("owner").get(f"Report/{rid}"), 403)

    def test_the_access_role_reads_but_does_not_create(self):
        result = W().try_report("access", "attempt", entityType="ContactAccess", columns=["name"])
        self.refused(result, 403)


class EntityAccessTest(Case):
    def test_the_deputy_does_not_report_on_finance(self):
        w = W()
        rid = w.report("owner", "invoices", entityType="Invoice", columns=["name"], accessType="public",
                       filters=all_of(w.name_filter()))["id"]
        deputy = w.client("deputy")
        self.ok(deputy.get(f"Report/{rid}"))
        self.refused(run(deputy, rid), 403, "entityForbidden")
        self.assertEqual(403, drill_down(deputy, "Invoice", rid)[0])
        catalog = {e["entityType"] for e in self.ok(deputy.get("Report/catalog"))["list"]}
        self.assertTrue({"Account", "Contact", "Case"} <= catalog)
        self.assertFalse({"Invoice", "InvoiceItem", "Quote", "SalesOrder", "Act", "Payment", "ContactAccess"} & catalog)
        self.refused(deputy.get("Report/catalog/Invoice"), 403)
        self.refused(w.try_report("deputy", "own invoices", entityType="Invoice", columns=["name"]), 403,
                     "entityForbidden")
        self.ok(run(w.client("owner"), rid))

    def test_contact_access_needs_the_access_role(self):
        w = W()
        self.refused(w.try_report("owner", "accesses", entityType="ContactAccess", columns=["name"]), 403,
                     "entityForbidden")
        self.refused(w.client("owner").get("Report/catalog/ContactAccess"), 403)
        catalog = self.ok(w.client("owner").get("Report/catalog"))["list"]
        self.assertNotIn("ContactAccess", {e["entityType"] for e in catalog})
        rid = w.report("both", "accesses", entityType="ContactAccess", columns=["name"], accessType="public",
                       filters=all_of(w.name_filter()))["id"]
        self.assertEqual(0, self.ok(run(w.client("access"), rid))["recordCount"])
        self.ok(run(w.client("both"), rid))
        self.refused(run(w.client("owner"), rid), 403, "entityForbidden")
        self.refused(run(w.client("dir2"), rid), 403, "entityForbidden")
        # Related fields of ContactAccess need the role too.
        self.refused(w.try_report("owner", "contact accesses", entityType="Contact",
                                  columns=["name", "cContactAccesses.name"]), 403)

    def test_the_access_password_is_never_offered(self):
        w = W()
        for user in ("access", "both", "admin"):
            with self.subTest(user=user):
                catalog = self.ok(w.client(user).get("Report/catalog/ContactAccess"))
                self.assertNotIn("anydeskPassword", json.dumps(catalog))
                self.assertIn("name", [f["ref"] for f in catalog["fields"]])
        self.assertNotIn("anydeskPassword", json.dumps(self.ok(w.client("both").get("Report/catalog/Contact"))))
        for user in ("both", "admin"):
            for definition in ({"columns": ["name", "anydeskPassword"]},
                               {"columns": ["name"], "filters": all_of(cond("anydeskPassword", "isNotNull"))}):
                self.refused(w.try_report(user, "password", entityType="ContactAccess", **definition), 400,
                             "unknownField")
            self.refused(w.try_report(user, "password", entityType="Contact",
                                      columns=["name", "cContactAccesses.anydeskPassword"]), 400, "unknownField")


class FieldAccessTest(Case):
    """Invoice.grandTotal closed by the field ACL of the user «nototal»."""

    USES = {
        "columns": {"columns": ["name", "grandTotal"]},
        "sorting": {"columns": ["name", "grandTotal"], "sorting": [{"column": "grandTotal", "direction": "desc"}]},
        "groups": {"type": "summaries", "groups": [{"field": "grandTotal"}], "aggregates": [{"function": "COUNT"}]},
        "aggregates": {"type": "summaries", "groups": [{"field": "status"}],
                       "aggregates": [{"function": "SUM", "field": "grandTotal"}]},
        "totals": {"columns": ["name", "grandTotal"], "totals": [{"column": "grandTotal", "functions": ["SUM"]}]},
        "calculations": {"columns": ["name", "grandTotal"],
                         "calculations": [{"label": "x", "expression": "{grandTotal} * 2", "functions": ["SUM"]}]},
        "filters": {"columns": ["name"], "filters": all_of(cond("grandTotal", "greaterThan", "0"))},
        "nestedFilters": {"columns": ["name"], "filters": {"type": "and", "items": [
            {"type": "or", "items": [cond("name", "isNotNull"), cond("grandTotal", "isNull")]}]}},
        "havingFilters": {"type": "summaries", "groups": [{"field": "status"}],
                          "aggregates": [{"function": "COUNT"}, {"function": "SUM", "field": "grandTotal"}],
                          "havingFilters": [{"aggregate": "SUM:grandTotal", "operator": "greaterThan", "value": "0"}]},
        "quickFilters": {"columns": ["name"], "quickFilters": ["grandTotal"]},
    }

    def test_saving_a_report_with_a_closed_field_is_refused_wherever_it_is_used(self):
        for use, definition in self.USES.items():
            with self.subTest(use=use):
                self.refused(W().try_report("nototal", f"uses {use}", entityType="Invoice", **definition), 403,
                             "fieldForbidden")
        # The same field reached through a link of another entity.
        self.refused(W().try_report("nototal", "via link", entityType="Account",
                                    columns=["name", "cInvoices.grandTotal"]), 403, "fieldForbidden")
        self.ok(W().try_report("nototal", "allowed", entityType="Invoice", columns=["name", "subtotal"]))

    def test_running_a_report_with_a_closed_field_is_refused(self):
        w = W()
        for use, definition in self.USES.items():
            with self.subTest(use=use):
                result = w.try_report("owner", f"public {use}", entityType="Invoice", accessType="public",
                                      **definition)
                if use == "quickFilters":  # a money field is no quick filter for anybody
                    self.refused(result, 400, "fieldNotForQuickFilter")
                    continue
                rid = self.ok(result)["id"]
                self.ok(run(w.client("owner"), rid))
                self.refused(run(w.client("nototal"), rid), 403, "fieldForbidden")
                self.assertRefusedList(drill_down(w.client("nototal"), "Invoice", rid))

    def test_one_off_conditions_with_a_closed_field_are_refused(self):
        w = W()
        rid = w.report("owner", "public names", entityType="Invoice", columns=["name"], accessType="public",
                       filters=all_of(w.name_filter()))["id"]
        nototal = w.client("nototal")
        self.assertEqual(1, self.ok(run(nototal, rid))["recordCount"])
        closed = all_of(w.name_filter(), cond("grandTotal", "greaterThan", "0"))
        self.refused(run(nototal, rid, filters=closed), 403, "fieldForbidden")
        self.assertRefusedList(drill_down(nototal, "Invoice", rid, filters=closed))
        self.ok(run(w.client("owner"), rid, filters=closed))

    def test_any_save_of_a_report_with_a_closed_field_is_refused(self):
        """The owner lost access to a field the report uses: changing only the description or the folder is refused
        too — every save is checked with the acting user's ACL (external review B5, 2026-10-04)."""
        w = W()
        rid = w.report("admin", "closed later", entityType="Invoice", columns=["name", "grandTotal"],
                       assignedUserId=w.uid["nototal"])["id"]
        nototal = w.client("nototal")
        self.refused(nototal.put(f"Report/{rid}", {"description": "x"}), 403, "fieldForbidden")
        self.ok(w.admin.put(f"Report/{rid}", {"description": "x"}))

    def test_a_closed_link_and_a_closed_related_field(self):
        w = W()
        for user, definition, key in (
                ("noaccount", {"columns": ["name", "account.name"]}, "linkForbidden"),
                ("noaccount", {"columns": ["name", "account"]}, "fieldForbidden"),
                ("noaccount", {"columns": ["name"], "filters": all_of(cond("account.name", "isNotNull"))},
                 "linkForbidden"),
                ("noinn", {"columns": ["name", "account.cInn"]}, "fieldForbidden"),
                ("noinn", {"columns": ["name"], "filters": all_of(cond("account.cInn", "equals", "77-SYNTH-ACL"))},
                 "fieldForbidden")):
            with self.subTest(user=user, definition=definition):
                self.refused(w.try_report(user, "closed", entityType="Invoice", **definition), 403, key)
                rid = w.report("owner", "public closed", entityType="Invoice", accessType="public",
                               **definition)["id"]
                self.ok(run(w.client("owner"), rid))
                self.refused(run(w.client(user), rid), 403, key)
        # The core list refuses a related condition over the closed link as well.
        where = [{"type": "itvolgaRelated", "attribute": "id",
                  "value": {"link": "account", "where": [{"type": "isNotNull", "attribute": "name"}]}}]
        self.assertRefusedList(list_ids(w.client("noaccount"), "Invoice", where))
        self.assertEqual(200, list_ids(w.client("owner"), "Invoice", where)[0])


class RelatedRecordAccessTest(Case):
    """«own»: reads every account but only its own contacts; an account has a visible and a hidden contact."""

    @classmethod
    def setUpClass(cls):
        w = W()
        cls.ar1 = w.create("Account", {"name": f"{w.tag} rel-1"})["id"]
        cls.ar2 = w.create("Account", {"name": f"{w.tag} rel-2"})["id"]
        for key, account, owner in (("own", cls.ar1, "own"), ("other", cls.ar1, "owner"), ("other2", cls.ar2, "owner")):
            w.create("Contact", {"firstName": "Пётр", "lastName": f"{w.tag} {key}", "accountId": account,
                                 "assignedUserId": w.uid[owner]})
        cls.report = w.report("own", "contacts", entityType="Account", columns=["name", "contacts.lastName"],
                              sorting=[{"column": "name"}], rowLimit=None,
                              filters=all_of(cond("name", "startsWith", f"{w.tag} rel")))["id"]

    def rows(self, user, **body):
        result = self.ok(run(W().client(user), self.report, noLimit=True, **body))
        tag = W().tag + " "
        return result, [(r["cells"][0]["v"].removeprefix(tag), (r["cells"][1]["v"] or "").removeprefix(tag) or None)
                        for r in result["rows"]]

    def test_hidden_related_records_add_no_rows(self):
        result, rows = self.rows("own")
        self.assertEqual([("rel-1", "own"), ("rel-2", None)], rows)
        self.assertEqual((2, 2), (result["recordCount"], result["rowCount"]))
        result, rows = self.rows("admin")
        self.assertEqual([("rel-1", "other"), ("rel-1", "own"), ("rel-2", "other2")], sorted(rows))
        self.assertEqual((2, 3), (result["recordCount"], result["rowCount"]))

    def test_hidden_related_records_do_not_match_conditions(self):
        tag = W().tag
        other = all_of(cond("name", "startsWith", f"{tag} rel"), cond("contacts.lastName", "equals", f"{tag} other"))
        own = all_of(cond("name", "startsWith", f"{tag} rel"), cond("contacts.lastName", "equals", f"{tag} own"))
        self.assertEqual([], self.rows("own", filters=other)[1])
        self.assertEqual([("rel-1", "own")], self.rows("own", filters=own)[1])
        self.assertEqual({("rel-1", "other"), ("rel-1", "own")}, set(self.rows("admin", filters=other)[1]))

    def test_core_list_with_a_related_condition(self):
        tag = W().tag

        def where(last_name):
            return [{"type": "itvolgaRelated", "attribute": "id",
                     "value": {"link": "contacts", "where": [{"type": "equals", "attribute": "lastName",
                                                              "value": f"{tag} {last_name}"}]}}]

        own = W().client("own")
        self.assertEqual((200, set()), list_ids(own, "Account", where("other")))
        self.assertEqual((200, {self.ar1}), list_ids(own, "Account", where("own")))
        self.assertEqual((200, {self.ar1}), list_ids(W().admin, "Account", where("other")))
        self.assertEqual((200, {self.ar2}), list_ids(W().admin, "Account", where("other2")))
        bad = [{"type": "itvolgaRelated", "attribute": "id", "value": {"link": "noSuchLink", "where": [
            {"type": "isNotNull", "attribute": "id"}]}}]
        self.assertEqual(400, list_ids(own, "Account", bad)[0])


class AdminRelatedRecordTest(Case):
    """The system user is hidden from administrators too (core mandatory filter): a record it created shows its name in
    the link column, like core lists, but none of its fields (review finding of 2026-10-04: the readable-id subquery
    was skipped for administrators)."""

    def test_fields_of_the_system_user_stay_hidden(self):
        w = W()
        system = sql("SELECT id FROM user WHERE type='system' AND deleted=0")[0][0]
        account = w.create("Account", {"name": f"{w.tag} by system"})["id"]
        sql(f"UPDATE account SET created_by_id='{system}' WHERE id='{account}'")
        report = w.report("admin", "system creator", entityType="Account",
                          columns=["name", "createdBy", "createdBy.userName"],
                          filters=all_of(cond("name", "equals", f"{w.tag} by system")))["id"]
        rows = self.ok(run(w.admin, report))["rows"]
        self.assertEqual(1, len(rows))
        self.assertEqual(system, rows[0]["cells"][1]["id"])
        self.assertIsNone(rows[0]["cells"][2]["v"])


class FieldCompareAccessTest(Case):
    """Task.dateStart closed for «nostart»: comparing it with another date is refused on either side, and so is its
    utility attribute dateStartDate (review finding of 2026-10-04: the right operand was not checked)."""

    @staticmethod
    def compare(left, right):
        return [{"type": "itvolgaFieldCompare", "attribute": left,
                 "value": {"operator": "lessThan", "attribute": right}}]

    def test_a_closed_field_on_either_side_is_refused(self):
        nostart = W().client("nostart")
        # The core where check answers 400 for a closed attribute; either way the list is refused.
        self.assertIn(list_ids(nostart, "Task", self.compare("dateStart", "dateEnd"))[0], (400, 403))
        self.assertIn(list_ids(nostart, "Task", self.compare("dateEnd", "dateStart"))[0], (400, 403))
        self.assertEqual(200, list_ids(W().admin, "Task", self.compare("dateEnd", "dateStart"))[0])

    def test_utility_attributes_are_refused(self):
        for client in (W().client("nostart"), W().admin):
            for left, right in (("dateEndDate", "dateStartDate"), ("dateEnd", "dateStartDate")):
                with self.subTest(left=left, right=right):
                    self.assertIn(list_ids(client, "Task", self.compare(left, right))[0], (400, 403))


if __name__ == "__main__":
    unittest.main()
