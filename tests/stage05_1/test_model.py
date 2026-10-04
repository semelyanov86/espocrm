"""Stage 05.1 acceptance tests: report folders, definition checks on save, the stored form and the standard reports.

  task test:stage05.1   (python3 -m unittest discover -s tests/stage05_1 -v)

Folders (D-88): the system folder «Общие» (seedKey general) is never deleted, a folder holding reports is not deleted,
names are unique (case-insensitive), folders are flat, a report moves between folders and lands in «Общие» without
one, `GET Report/folderCounts` counts only the reports the user may read. Definitions (D-101): refused saves give 400
with the translation key of Report.messages; the type and the main entity never change; the stored definition is the
canonical form. Standard reports (D-100): every seedKey of `app.itvolgaReports` exists once, runs as the administrator,
`itvolga-setup-reports` is idempotent, never overwrites a report a user changed and never brings back a deleted one
(the tests restore what they change, so the stand stays as it was).
"""
import json
import unittest

from fixture import REPO, World, all_of, cond, espo_console, label, must, run, sql

S = {}
MODULE = REPO / "custom/Espo/Modules/Itvolga/Resources"
REGISTRY = json.loads((MODULE / "metadata/app/itvolgaReports.json").read_text(encoding="utf-8"))


def setUpModule():
    w = World()
    unittest.addModuleCleanup(w.cleanup)
    S["w"] = w
    w.user("dir", roles=["Директор"])
    w.user("dir2", roles=["Директор"])
    w.user("access", roles=["Доступы"])
    S["general"] = sql("SELECT id FROM report_folder WHERE seed_key='general' AND deleted=0")[0][0]


def W():
    return S["w"]


def folder(name, by="dir"):
    w = W()
    return w.create("ReportFolder", {"name": f"{w.tag} {name}", "assignedUserId": w.uid.get(by)}, by=by)["id"]


def setup_reports():
    return espo_console("itvolga-setup-reports").strip()


class Case(unittest.TestCase):
    def ok(self, result):
        status, payload, _ = result
        self.assertEqual(200, status, f"HTTP {status}: {payload}")
        return payload

    def refused(self, result, status, key=None):
        self.assertEqual(status, result[0], f"expected HTTP {status}, got {result[0]}: {result[1]}")
        if key:
            self.assertEqual(key, label(result))


class FolderTest(Case):
    def test_deleted_folders_are_not_restored(self):
        """The row a removed standard folder leaves is not restored past the name check (external review B9)."""
        w = W()
        fid = folder("tombstone")
        sql(f"UPDATE report_folder SET seed_key='{w.tag}-tomb' WHERE id='{fid}'")
        try:
            self.ok(w.admin.delete(f"ReportFolder/{fid}"))
            w.forget("ReportFolder", fid)
            self.assertEqual([["1"]], sql(f"SELECT deleted FROM report_folder WHERE id='{fid}'"))
            self.refused(w.admin.post("ReportFolder/action/restoreDeleted", {"id": fid}), 403, "folderRestoreDisabled")
            self.assertEqual([["1"]], sql(f"SELECT deleted FROM report_folder WHERE id='{fid}'"))
        finally:
            sql(f"DELETE FROM report_folder WHERE id='{fid}' AND deleted=1")

    def test_a_restored_report_of_a_removed_folder_goes_to_general(self):
        """Delete a report, then its emptied folder, then restore the report: it lands in «Общие» (review W7)."""
        w = W()
        fid = folder("gone")
        report = w.report("dir", "restored", entityType="Account", columns=["name"], folderId=fid)
        self.ok(w.client("dir").delete(f"Report/{report['id']}"))
        self.ok(w.client("dir").delete(f"ReportFolder/{fid}"))
        w.forget("ReportFolder", fid)
        self.ok(w.admin.post("Report/action/restoreDeleted", {"id": report["id"]}))
        general = sql("SELECT id FROM report_folder WHERE is_system=1 AND deleted=0")[0][0]
        self.assertEqual(general, self.ok(w.admin.get(f"Report/{report['id']}"))["folderId"])

    def test_the_system_folder_is_never_deleted(self):
        self.refused(W().admin.delete(f"ReportFolder/{S['general']}"), 403, "folderSystem")
        self.assertEqual([["0", "1"]], sql(f"SELECT deleted, is_system FROM report_folder WHERE id='{S['general']}'"))

    def test_a_folder_with_reports_is_not_deleted(self):
        w = W()
        full = folder("full")
        report = w.report("dir", "in folder", entityType="Account", columns=["name"], folderId=full)
        for client in (w.client("dir"), w.admin):
            self.refused(client.delete(f"ReportFolder/{full}"), 409, "folderNotEmpty")
        self.ok(w.client("dir").put(f"Report/{report['id']}", {"folderId": None}))
        self.ok(w.client("dir").delete(f"ReportFolder/{full}"))
        w.forget("ReportFolder", full)

    def test_reports_hidden_from_the_folder_owner_count_too(self):
        w = W()
        other = folder("other")
        report = w.report("dir2", "private of dir2", entityType="Account", columns=["name"], folderId=other)
        refusal = w.client("dir").delete(f"ReportFolder/{other}")
        self.refused(refusal, 409, "folderNotEmpty")
        # The answer does not tell how many reports, private ones of others included (external review W3).
        self.assertNotIn("count", json.dumps(refusal[1]))
        self.ok(w.client("dir2").put(f"Report/{report['id']}", {"folderId": None}))
        self.ok(w.client("dir").delete(f"ReportFolder/{other}"))
        w.forget("ReportFolder", other)

    def test_names_are_unique_ignoring_case(self):
        w = W()
        first = folder("Уникальная")
        self.refused(w.client("dir").post("ReportFolder", {"name": f"{w.tag} уникальная  ",
                                                           "assignedUserId": w.uid["dir"]}), 409, "folderNameExists")
        self.refused(w.client("dir2").post("ReportFolder", {"name": f"{w.tag} УНИКАЛЬНАЯ",
                                                            "assignedUserId": w.uid["dir2"]}), 409, "folderNameExists")
        second = folder("Другая")
        self.refused(w.client("dir").put(f"ReportFolder/{second}", {"name": f"{w.tag} уникальная"}), 409,
                     "folderNameExists")
        self.ok(w.client("dir").put(f"ReportFolder/{first}", {"name": f"{w.tag} Уникальная", "description": "x"}))

    def test_folders_are_flat(self):
        w = W()
        parent = folder("parent")
        child = w.create("ReportFolder", {"name": f"{w.tag} child", "parentId": parent,
                                          "assignedUserId": w.uid["dir"]}, by="dir")
        self.assertIsNone(self.ok(w.admin.get(f"ReportFolder/{child['id']}")).get("parentId"))
        w.admin.put(f"ReportFolder/{child['id']}", {"parentId": parent})
        self.assertIsNone(self.ok(w.admin.get(f"ReportFolder/{child['id']}")).get("parentId"))
        self.assertEqual([["NULL"]],
                         sql(f"SELECT IFNULL(parent_id, 'NULL') FROM report_folder WHERE id='{child['id']}'"))

    def test_moving_a_report_between_folders(self):
        w = W()
        first, second = folder("from"), folder("to")
        report = w.report("dir", "moving", entityType="Account", columns=["name"])
        self.assertEqual(S["general"], report["folderId"])
        self.ok(w.client("dir").put(f"Report/{report['id']}", {"folderId": first}))
        self.assertEqual(first, self.ok(w.client("dir").get(f"Report/{report['id']}"))["folderId"])
        self.ok(w.client("dir").put(f"Report/{report['id']}", {"folderId": second}))
        self.assertEqual(second, self.ok(w.client("dir").get(f"Report/{report['id']}"))["folderId"])
        self.ok(w.client("dir").put(f"Report/{report['id']}", {"folderId": None}))
        self.assertEqual(S["general"], self.ok(w.client("dir").get(f"Report/{report['id']}"))["folderId"])

    def test_folder_counts_only_readable_reports(self):
        w = W()
        counted = folder("counted")
        w.report("dir", "counted private", entityType="Account", columns=["name"], folderId=counted)
        w.report("dir", "counted public", entityType="Account", columns=["name"], folderId=counted,
                 accessType="public")
        w.report("dir", "counted shared", entityType="Account", columns=["name"], folderId=counted,
                 accessType="shared", sharedUsersIds=[w.uid["dir2"]])
        for user, expected in (("dir", 3), ("admin", 3), ("dir2", 2), ("access", 1)):
            with self.subTest(user=user):
                counts = self.ok(w.client(user).get("Report/folderCounts"))
                self.assertEqual(expected, counts["folders"].get(counted, 0))
                self.assertEqual(counts["total"], sum(counts["folders"].values()))


class DefinitionTest(Case):
    def test_refused_definitions_name_the_rule(self):
        w = W()
        cases = {
            "aggregatesRequired": {"type": "summaries", "entityType": "Invoice", "groups": [{"field": "status"}]},
            "matrixNeedsTwoGroups": {"type": "matrix", "entityType": "Invoice", "groups": [{"field": "status"}],
                                     "aggregates": [{"function": "COUNT"}]},
            "calculationUnexpectedEnd": {"entityType": "Invoice", "columns": ["name", "grandTotal"],
                                         "calculations": [{"label": "x", "expression": "{grandTotal} *"}]},
            "calculationBadReference": {"entityType": "Invoice", "columns": ["name", "grandTotal"],
                                        "calculations": [{"label": "x", "expression": "{subtotal} * 2"}]},
            "sharedNeedsList": {"entityType": "Invoice", "columns": ["name"], "accessType": "shared"},
            "columnsRequired": {"entityType": "Invoice", "columns": []},
            "unknownField": {"entityType": "Invoice", "columns": ["name", "noSuchField"]},
            "badSorting": {"entityType": "Invoice", "columns": ["name"], "sorting": [{"column": "status"}]},
            "badGranularity": {"type": "summaries", "entityType": "Invoice",
                               "groups": [{"field": "status", "granularity": "month"}],
                               "aggregates": [{"function": "COUNT"}]},
            "duplicateGroup": {"type": "summaries", "entityType": "Invoice",
                               "groups": [{"field": "status"}, {"field": "status"}],
                               "aggregates": [{"function": "COUNT"}]},
            "badGroupSort": {"type": "summaries", "entityType": "Invoice", "groups": [{"field": "status"}],
                             "aggregates": [{"function": "COUNT"}],
                             "groupSort": {"aggregate": "SUM:grandTotal", "direction": "desc"}},
            "badHavingValue": {"type": "summaries", "entityType": "Invoice", "groups": [{"field": "status"}],
                               "aggregates": [{"function": "COUNT"}],
                               "havingFilters": [{"aggregate": "COUNT", "operator": "greaterThan", "value": "x"}]},
            "aggregateNotNumeric": {"type": "summaries", "entityType": "Invoice", "groups": [{"field": "status"}],
                                    "aggregates": [{"function": "SUM", "field": "name"}]},
            "oneManyLink": {"entityType": "Account", "columns": ["name", "contacts.lastName", "cInvoices.name"]},
            "notForType": {"entityType": "Invoice", "columns": ["name"], "groups": [{"field": "status"}]},
            "operatorNotAllowed": {"entityType": "Invoice", "columns": ["name"],
                                   "filters": all_of(cond("status", "greaterThan", "1"))},
        }
        for key, definition in cases.items():
            with self.subTest(key=key):
                result = w.try_report("dir", f"bad {key}", **definition)
                self.refused(result, 400, key)
                self.assertEqual("Report", result[1]["messageTranslation"]["scope"])

    def test_type_and_entity_never_change(self):
        w = W()
        report = w.report("dir", "fixed", entityType="Invoice", columns=["name"])
        rid = report["id"]
        for change in ({"type": "summaries"}, {"entityType": "Account"}):
            with self.subTest(change=change):
                result = w.client("dir").put(f"Report/{rid}", change)
                # The record service of the core drops read-only-after-create fields from an update (200); the
                # definition hook refuses a change that reaches the ORM (400 readOnlyAfterCreate). Either way the
                # report keeps its type and entity.
                if result[0] != 200:
                    self.refused(result, 400, "readOnlyAfterCreate")
                stored = self.ok(w.admin.get(f"Report/{rid}"))
                self.assertEqual(("tabular", "Invoice"), (stored["type"], stored["entityType"]))
        # A field of the other entity is still checked against the report's own entity.
        self.refused(w.client("dir").put(f"Report/{rid}", {"entityType": "Account", "columns": ["name", "cInn"]}),
                     400, "unknownField")

    def test_the_stored_definition_is_canonical(self):
        w = W()
        tabular = w.report(
            "dir", "canonical", entityType="Invoice",
            columns=["name", "status", "name", "grandTotal", "status"],
            sorting=[{"column": "name"}, {"column": "name", "direction": "desc"}],
            totals=[{"column": "grandTotal", "functions": ["MAX", "SUM", "SUM"]}],
            quickFilters=["status", "status"],
            filters={"type": "and", "items": [{"field": "status", "where": {
                "type": "in", "attribute": "status", "value": ["Sent"], "extra": 1}, "junk": True}]},
            labels={"c:name": "  Счёт  ", "c:status": "", "c:noSuchColumn": "x"},
            groupLimit=7, sharedUsersIds=[w.uid["dir2"]])
        stored = self.ok(w.admin.get(f"Report/{tabular['id']}"))
        self.assertEqual(["name", "status", "grandTotal"], stored["columns"])
        self.assertEqual([{"column": "name", "direction": "asc"}], stored["sorting"])
        self.assertEqual([{"column": "grandTotal", "functions": ["SUM", "MAX"]}], stored["totals"])
        self.assertEqual(["status"], stored["quickFilters"])
        self.assertEqual({"type": "and", "items": [{"field": "status", "where": {
            "type": "in", "attribute": "status", "value": ["Sent"]}}]}, stored["filters"])
        self.assertEqual({"c:name": "Счёт"}, stored["labels"])
        self.assertEqual((None, None, [], "private"), (stored["groupLimit"], stored["groupSort"],
                                                      stored.get("sharedUsersIds") or [], stored["accessType"]))
        grouped = w.report("dir", "canonical groups", type="summaries", entityType="Invoice",
                           groups=[{"field": "dateInvoiced"}, {"field": "account", "direction": "desc"}],
                           aggregates=[{"function": "COUNT"}, {"function": "SUM", "field": "grandTotal"}],
                           groupSort={"aggregate": "SUM:grandTotal"})
        stored = self.ok(w.admin.get(f"Report/{grouped['id']}"))
        self.assertEqual([{"field": "dateInvoiced", "granularity": "day", "direction": "asc"},
                          {"field": "account", "granularity": None, "direction": "desc"}], stored["groups"])
        self.assertEqual([{"function": "COUNT", "link": None, "field": None},
                          {"function": "SUM", "link": None, "field": "grandTotal"}], stored["aggregates"])
        self.assertEqual({"aggregate": "SUM:grandTotal", "direction": "desc"}, stored["groupSort"])
        self.assertEqual(([], [], {"type": "and", "items": []}), (stored["columns"], stored["sorting"],
                                                                 stored["filters"]))


class StandardReportsTest(Case):
    @classmethod
    def setUpClass(cls):
        cls.manifests = {}
        for name in REGISTRY.get("standardReports", []):
            manifest = json.loads((MODULE / "reports/standard" / f"{name}.json").read_text(encoding="utf-8"))
            cls.manifests[manifest["seedKey"]] = manifest
        cls.catalog = {e["entityType"] for e in must(W().admin.get("Report/catalog"))["list"]}

    def seeded(self):
        rows = sql("SELECT id, seed_key FROM report WHERE seed_key IS NOT NULL AND deleted=0 ORDER BY seed_key")
        return [(rid, key) for rid, key in rows if key in self.manifests]

    def test_every_seed_key_exists_once(self):
        self.assertEqual(len(REGISTRY.get("standardReports", [])), len(self.manifests), "seedKeys are unique")
        for key, manifest in self.manifests.items():
            with self.subTest(report=key):
                rows = sql(f"SELECT type, entity_type, access_type FROM report WHERE seed_key='{key}'")
                if manifest["entityType"] not in self.catalog:
                    self.assertLessEqual(len(rows), 1)
                    continue
                self.assertEqual(1, len(rows), "one row per seedKey (deleted ones included)")
                self.assertEqual([manifest["type"], manifest["entityType"], "public"], rows[0])
        for item in REGISTRY.get("folders", []):
            with self.subTest(folder=item["seedKey"]):
                rows = sql(f"SELECT is_system FROM report_folder WHERE seed_key='{item['seedKey']}' AND deleted=0")
                self.assertLessEqual(len(rows), 1)
                if not item.get("onlyIfEntity") or item["onlyIfEntity"] in self.catalog:
                    self.assertEqual([["1" if item.get("isSystem") else "0"]], rows)

    def test_every_standard_report_runs(self):
        seeded = self.seeded()
        if not seeded:
            self.skipTest("no standard report on the stand")
        for rid, key in seeded:
            with self.subTest(report=key):
                status, payload, _ = run(W().admin, rid)
                self.assertEqual(200, status, f"{key}: HTTP {status} {json.dumps(payload, ensure_ascii=False)[:300]}")
                self.assertEqual(self.manifests[key]["type"], payload["type"])
                status, payload, _ = run(W().admin, rid, noLimit=True, withQuickFilterOptions=False)
                self.assertEqual(200, status, f"{key} noLimit: HTTP {status}")

    def test_setup_is_idempotent(self):
        self.assertEqual("no changes", setup_reports())
        self.assertEqual("[dry-run] no changes", espo_console("itvolga-setup-reports", "--dry-run").strip())

    def test_a_report_changed_by_a_user_is_not_overwritten(self):
        seeded = self.seeded()
        if not seeded:
            self.skipTest("no standard report on the stand")
        rid, key = seeded[0]
        before = sql(f"SELECT name, IFNULL(description, ''), modified_at, IFNULL(modified_by_id, ''), row_limit "
                     f"FROM report WHERE id='{rid}'")[0]
        original = must(W().admin.get(f"Report/{rid}"))
        try:
            changed = f"{W().tag} changed"
            self.ok(W().admin.put(f"Report/{rid}", {"name": changed, "description": changed, "rowLimit": 3}))
            self.assertEqual("no changes", setup_reports())
            stored = self.ok(W().admin.get(f"Report/{rid}"))
            self.assertEqual((changed, changed, 3), (stored["name"], stored["description"], stored["rowLimit"]))
        finally:
            must(W().admin.put(f"Report/{rid}", {"name": original["name"], "description": original["description"],
                                                 "rowLimit": original["rowLimit"]}), "restore the standard report")
            sql(f"UPDATE report SET modified_at='{before[2]}', modified_by_id=NULLIF('{before[3]}', '') "
                f"WHERE id='{rid}'")
        self.assertEqual([before], sql(f"SELECT name, IFNULL(description, ''), modified_at, "
                                       f"IFNULL(modified_by_id, ''), row_limit FROM report WHERE id='{rid}'"))

    def test_a_deleted_standard_report_is_not_recreated(self):
        seeded = self.seeded()
        if not seeded:
            self.skipTest("no standard report on the stand")
        rid, key = seeded[-1]
        before = sql(f"SELECT modified_at, IFNULL(modified_by_id, '') FROM report WHERE id='{rid}'")[0]
        try:
            self.ok(W().admin.delete(f"Report/{rid}"))
            self.assertEqual([["1"]], sql(f"SELECT deleted FROM report WHERE id='{rid}'"))
            self.assertEqual("no changes", setup_reports())
            self.assertEqual([[rid, "1"]], sql(f"SELECT id, deleted FROM report WHERE seed_key='{key}'"))
        finally:
            sql(f"UPDATE report SET deleted=0, modified_at='{before[0]}', modified_by_id=NULLIF('{before[1]}', '') "
                f"WHERE id='{rid}'")
        self.assertEqual([[rid, "0"]], sql(f"SELECT id, deleted FROM report WHERE seed_key='{key}'"))
        self.ok(run(W().admin, rid))


    def test_the_cleanup_job_keeps_a_deleted_standard_report(self):
        """The core cleanup job purges old soft-deleted rows; a standard report's row stays, so the setup still knows it
        was deleted (external review B10)."""
        seeded = self.seeded()
        if not seeded:
            self.skipTest("no standard report on the stand")
        rid, key = seeded[0]
        before = sql(f"SELECT modified_at, IFNULL(modified_by_id, '') FROM report WHERE id='{rid}'")[0]
        try:
            self.ok(W().admin.delete(f"Report/{rid}"))
            sql(f"UPDATE report SET modified_at='2020-01-01 00:00:00' WHERE id='{rid}'")
            espo_console("run-job", "Cleanup")
            self.assertEqual([[rid, "1"]], sql(f"SELECT id, deleted FROM report WHERE seed_key='{key}'"))
            self.assertEqual("no changes", setup_reports())
        finally:
            sql(f"UPDATE report SET deleted=0, modified_at='{before[0]}', modified_by_id=NULLIF('{before[1]}', '') "
                f"WHERE id='{rid}'")
        self.assertEqual([[rid, "0"]], sql(f"SELECT id, deleted FROM report WHERE seed_key='{key}'"))

    def test_a_restored_shared_report_without_lists_becomes_private(self):
        """Cleanup keeps a standard report's row but deletes its sharing rows; restored, it is private, not a shared
        report without anybody (external review W18)."""
        w = W()
        report = w.report("dir", "shared standard", entityType="Account", columns=["name"], accessType="shared",
                          sharedUsersIds=[w.uid["dir2"]])
        rid = report["id"]
        sql(f"UPDATE report SET seed_key='{w.tag}-shared' WHERE id='{rid}'")
        try:
            self.ok(w.admin.delete(f"Report/{rid}"))
            sql(f"UPDATE report SET modified_at='2020-01-01 00:00:00' WHERE id='{rid}'")
            espo_console("run-job", "Cleanup")
            self.assertEqual([], sql(f"SELECT 1 FROM report_shared_user WHERE report_id='{rid}'"))
            self.ok(w.admin.post("Report/action/restoreDeleted", {"id": rid}))
            self.assertEqual("private", self.ok(w.admin.get(f"Report/{rid}"))["accessType"])
        finally:
            sql(f"UPDATE report SET seed_key=NULL WHERE id='{rid}'")

    def test_a_deleted_standard_folder_is_not_recreated(self):
        """The core category tree deletes a folder row; a standard folder leaves a soft-deleted row, and the setup does
        not bring it back (D-100, review finding of 2026-10-04)."""
        keys = [f["seedKey"] for f in REGISTRY.get("folders", []) if not f.get("isSystem")]
        rows = [r for r in sql("SELECT id, seed_key FROM report_folder WHERE seed_key IS NOT NULL AND deleted=0")
                if r[1] in keys]
        if not rows:
            self.skipTest("no standard folder on the stand")
        fid, key = rows[0]
        general = sql("SELECT id FROM report_folder WHERE is_system=1 AND deleted=0")[0][0]
        moved = [r[0] for r in sql(f"SELECT id FROM report WHERE folder_id='{fid}'")]
        sql(f"UPDATE report SET folder_id='{general}' WHERE folder_id='{fid}'")
        try:
            self.ok(W().admin.delete(f"ReportFolder/{fid}"))
            self.assertEqual([["1", key]], sql(f"SELECT deleted, seed_key FROM report_folder WHERE id='{fid}'"))
            self.assertEqual([], sql(f"SELECT 1 FROM report_folder_path WHERE descendor_id='{fid}'"))
            self.assertEqual("no changes", setup_reports())
            self.assertEqual([[fid]], sql(f"SELECT id FROM report_folder WHERE seed_key='{key}'"))
        finally:
            # Restore through the setup itself: without the row it creates the folder again (a new id).
            sql(f"DELETE FROM report_folder WHERE id='{fid}' AND deleted=1")
            setup_reports()
            restored = sql(f"SELECT id FROM report_folder WHERE seed_key='{key}' AND deleted=0")[0][0]
            if moved:
                sql(f"UPDATE report SET folder_id='{restored}' WHERE id IN ({', '.join(repr(m) for m in moved)})")
        self.assertEqual(len(moved), int(sql(f"SELECT COUNT(*) FROM report WHERE folder_id='{restored}'")[0][0]))


if __name__ == "__main__":
    unittest.main()
