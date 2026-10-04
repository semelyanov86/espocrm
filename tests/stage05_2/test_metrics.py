"""Stage 05.2 acceptance tests: key metrics (D-111…D-113, D-115) on the local stand, synthetic data.

Values of report rows equal the report's own numbers (record count, column totals over all records of the conditions,
not the page) and the reference sums; filter rows equal the total of the standard list with the same conditions; each
viewer gets their own numbers; closed, removed and changed sources give a status per row; the rules of saving (sources,
name, author, reordering); the usage mark of the reports list; deleting a set removes its dashlets from the users'
dashboards, the dashboard templates and the default dashboard.
"""
import json
import unittest

from common import (D, SUM_ALL, World, all_of, avg8, cond, flat_where, label, metric_values, must, num,
                    reference_data, run)

S = {}
FULL = {"create": "yes", "read": "all", "edit": "own", "delete": "own"}


def setUpModule():
    world = World()
    unittest.addModuleCleanup(world.cleanup)
    S["w"] = world
    world.user("dir", roles=["Директор"])
    world.user("dir2", roles=["Директор"])
    # Reads only own invoices; key metrics like every working role.
    own = world.role("own invoices", {"Invoice": {"create": "no", "read": "own", "edit": "no", "delete": "no"},
                                      "Account": {"read": "all"}, "ReportMetricSet": FULL})
    world.user("own", role_ids=[own])
    S["ref"] = reference_data(world)
    S["list"] = world.report("dir", "invoices", type="tabular", entityType="Invoice",
                             columns=["name", "grandTotal", "items.amount"], rowLimit=1, accessType="public",
                             filters=all_of(world.name_filter()))
    S["plain"] = world.report("dir", "plain", type="tabular", entityType="Invoice", columns=["name", "grandTotal"],
                              rowLimit=1, accessType="public", filters=all_of(world.name_filter()),
                              totals=[{"column": "grandTotal", "functions": ["SUM", "AVG", "MIN", "MAX"]}])


def W():
    return S["w"]


def R():
    return S["ref"]


def report_row(label_, report_id, function="COUNT", column=None):
    return {"label": label_, "source": "report", "reportId": report_id, "function": function, "column": column}


def preset_row(label_, where):
    return {"label": label_, "source": "filter", "entityType": "Invoice",
            "filter": {"kind": "preset", "name": "мой фильтр"}, "where": where}


class Case(unittest.TestCase):
    def ok(self, result):
        status, payload, _ = result
        self.assertEqual(200, status, f"HTTP {status}: {payload}")
        return payload

    def refused(self, result, status, key=None):
        self.assertEqual(status, result[0], f"expected HTTP {status}, got {result[0]}: {result[1]}")
        if key:
            self.assertEqual(key, label(result))

    def make_set(self, name, rows, by="dir"):
        return W().create("ReportMetricSet", {"name": f"{W().tag} {name}", "rows": rows}, by=by)

    def values(self, set_id, by="dir"):
        return {row["label"]: row for row in self.ok(metric_values(W().client(by), set_id))["rows"]}


class ValuesTest(Case):
    def test_report_rows_are_the_report_numbers(self):
        plain = S["plain"]["id"]
        metric = self.make_set("report values", [report_row("count", plain), report_row("sum", plain, "SUM", "grandTotal"),
                                                 report_row("avg", plain, "AVG", "grandTotal"),
                                                 report_row("min", plain, "MIN", "grandTotal"),
                                                 report_row("max", plain, "MAX", "grandTotal")])
        values = self.values(metric["id"])
        result = self.ok(run(W().client("dir"), plain))
        totals = result["totals"]["c:grandTotal"]

        self.assertEqual(7, values["count"]["value"]["v"])
        self.assertEqual(result["recordCount"], values["count"]["value"]["v"])
        for fn in ("SUM", "AVG", "MIN", "MAX"):
            self.assertEqual(totals[fn]["v"], values[fn.lower()]["value"]["v"], fn)
        # The row limit (1) and the page do not limit a metric.
        self.assertEqual(SUM_ALL, num(values["sum"]["value"]))
        self.assertLess(abs(num(values["avg"]["value"]) - avg8(SUM_ALL, 7)), D("1e-8"))
        self.assertEqual((D("0.01"), D("19500")), (num(values["min"]["value"]), num(values["max"]["value"])))
        self.assertTrue(all(row["status"] == "ok" for row in values.values()))

    def test_a_total_not_chosen_in_the_report_and_the_to_many_rule(self):
        lines = S["list"]["id"]
        metric = self.make_set("lines", [report_row("lines", lines, "SUM", "items.amount")])
        self.assertEqual(SUM_ALL, num(self.values(metric["id"])["lines"]["value"]))
        # A main field with a to-many link would be summed once per line (D-90).
        self.refused(W().try_create("ReportMetricSet", {"name": f"{W().tag} inflated",
                                                        "rows": [report_row("x", lines, "SUM", "grandTotal")]}),
                     400, "aggregateMultiplied")

    def test_filter_rows_equal_the_standard_list(self):
        where = [{"type": "startsWith", "attribute": "name", "value": W().tag},
                 {"type": "in", "attribute": "status", "value": ["Sent"]}]
        metric = self.make_set("filters", [preset_row("sent", where)])
        self.assertEqual(2, self.values(metric["id"])["sent"]["value"]["v"])
        status, payload, _ = W().client("dir").get("Invoice", **flat_where(where), maxSize=1)
        self.assertEqual((200, 2), (status, payload["total"]))

    def test_system_filter_rows(self):
        for stage, key in (("Qualification", "open1"), ("Closed Won", "won1")):
            W().create("Opportunity", {"name": f"{W().tag} {key}", "stage": stage, "amount": "10",
                                       "amountCurrency": "RUB", "closeDate": "2026-12-31",
                                       "assignedUserId": W().uid["dir"]}, by="dir")
        metric = self.make_set("system", [{"label": "open", "source": "filter", "entityType": "Opportunity",
                                           "filter": {"kind": "system", "name": "open"}}])
        status, payload, _ = W().client("dir").get("Opportunity", primaryFilter="open", maxSize=1)
        self.assertEqual(200, status)
        self.assertEqual(payload["total"], self.values(metric["id"])["open"]["value"]["v"])
        self.refused(W().try_create("ReportMetricSet", {"name": f"{W().tag} unknown", "rows": [
            {"label": "x", "source": "filter", "entityType": "Opportunity",
             "filter": {"kind": "system", "name": "noSuchFilter"}}]}), 400, "badMetricFilter")

    def test_filter_conditions_follow_the_time_zone_of_the_viewer(self):
        where = [{"type": "startsWith", "attribute": "name", "value": W().tag},
                 {"type": "lastSevenDays", "attribute": "createdAt", "dateTime": True, "timeZone": "UTC"}]
        metric = self.make_set("time zone", [preset_row("recent", where)])
        self.ok(W().admin.put(f"Preferences/{W().uid['dir2']}", {"timeZone": "Asia/Vladivostok"}))
        row = self.values(metric["id"], by="dir2")["recent"]
        # The conditions returned for the drill-down are those counted: in the viewer's time zone.
        self.assertEqual("Asia/Vladivostok", row["where"][1]["timeZone"])
        status, payload, _ = W().client("dir2").get("Invoice", **flat_where(row["where"]), maxSize=1)
        self.assertEqual((200, payload["total"]), (status, row["value"]["v"]))
        self.assertEqual("UTC", next(r for r in self.ok(W().client("dir").get(f"ReportMetricSet/{metric['id']}"))["rows"]
                                     if r["label"] == "recent")["where"][1]["timeZone"])

    def test_each_viewer_gets_their_own_numbers(self):
        where = [{"type": "startsWith", "attribute": "name", "value": W().tag}]
        metric = self.make_set("viewers", [report_row("count", S["plain"]["id"]), preset_row("all", where)])
        # «own» reads only own invoices: none of the reference set is theirs.
        own = self.values(metric["id"], by="own")
        self.assertEqual((0, 0), (own["count"]["value"]["v"], own["all"]["value"]["v"]))
        status, payload, _ = W().client("own").get("Invoice", **flat_where(where), maxSize=1)
        self.assertEqual((200, 0), (status, payload["total"]))
        self.assertEqual(7, self.values(metric["id"])["count"]["value"]["v"])


class StatusTest(Case):
    def test_closed_removed_and_changed_sources(self):
        private = W().report("dir", "private", type="tabular", entityType="Invoice", columns=["name", "grandTotal"],
                             filters=all_of(W().name_filter()))
        gone = W().report("dir", "gone", type="tabular", entityType="Invoice", columns=["name", "grandTotal"],
                          accessType="public", filters=all_of(W().name_filter()))
        changing = W().report("dir", "changing", type="tabular", entityType="Invoice", columns=["name", "grandTotal"],
                              accessType="public", filters=all_of(W().name_filter()))
        metric = self.make_set("statuses", [report_row("private", private["id"]), report_row("gone", gone["id"]),
                                            report_row("changing", changing["id"], "SUM", "grandTotal"),
                                            report_row("fine", S["plain"]["id"])])
        must(W().admin.delete(f"Report/{gone['id']}"), "delete report")
        self.ok(W().client("dir").put(f"Report/{changing['id']}", {"columns": ["name"]}))

        values = self.values(metric["id"], by="dir2")
        self.assertEqual({"private": "forbidden", "gone": "notFound", "changing": "invalid", "fine": "ok"},
                         {k: v["status"] for k, v in values.items()})
        self.assertIsNone(values["private"]["value"])
        self.assertNotIn("reportName", values["private"])
        # The author still renames the set and reorders the rows: unchanged rows are not checked again.
        rows = json.loads(json.dumps(metric["rows"]))
        saved = self.ok(W().client("dir").put(f"ReportMetricSet/{metric['id']}",
                                              {"name": f"{W().tag} statuses 2", "rows": list(reversed(rows))}))
        self.assertEqual(["fine", "changing", "gone", "private"], [r["label"] for r in saved["rows"]])
        self.assertEqual(["m4", "m3", "m2", "m1"], [r["id"] for r in saved["rows"]])


class SaveTest(Case):
    def test_sources_are_checked_for_the_saving_user(self):
        summaries_report = W().report("dir", "summaries", type="summaries", entityType="Invoice",
                                      groups=[{"field": "status"}], aggregates=[{"function": "COUNT"}],
                                      accessType="public")
        private = W().report("dir", "private 2", type="tabular", entityType="Invoice", columns=["name"])
        plain = S["plain"]["id"]
        cases = [
            ([report_row("x", summaries_report["id"])], 400, "metricNotTabular"),
            ([report_row("x", plain, "SUM", "name")], 400, "metricBadColumn"),
            ([report_row("x", plain, "SUM", "dateDue")], 400, "metricBadColumn"),
            ([report_row("x", "0000000000000000z")], 400, "metricReportNotFound"),
            ([preset_row("x", [{"type": "nonsense", "attribute": "name", "value": 1}])], 400, None),
            ([report_row("x", plain)] * 31, 400, "tooMany"),
            ([{"label": "", "source": "report", "reportId": plain}], 400, "metricLabelRequired"),
        ]
        for rows, status, key in cases:
            self.refused(W().try_create("ReportMetricSet", {"name": f"{W().tag} bad", "rows": rows}, by="dir"),
                         status, key)
        self.refused(W().try_create("ReportMetricSet", {"name": f"{W().tag} not mine",
                                                        "rows": [report_row("x", private["id"])]}, by="dir2"), 403)

    def test_names_are_unique_among_live_sets(self):
        first = self.make_set("Уникальное имя", [])
        self.refused(W().try_create("ReportMetricSet", {"name": f"{W().tag} уникальное ИМЯ", "rows": []}), 409,
                     "metricSetNameExists")
        must(W().admin.delete(f"ReportMetricSet/{first['id']}"), "delete set")
        W().forget("ReportMetricSet", first["id"])
        self.make_set("уникальное имя", [])

    def test_only_the_author_changes_a_set(self):
        metric = self.make_set("authored", [report_row("count", S["plain"]["id"])])
        self.assertEqual(200, W().client("dir2").get(f"ReportMetricSet/{metric['id']}")[0])
        self.refused(W().client("dir2").put(f"ReportMetricSet/{metric['id']}", {"name": f"{W().tag} hijacked"}), 403)
        self.refused(W().client("dir2").delete(f"ReportMetricSet/{metric['id']}"), 403)
        self.ok(W().admin.put(f"ReportMetricSet/{metric['id']}", {"description": "admin"}))

    def test_used_reports_are_marked_in_the_list(self):
        used = W().report("dir", "used", type="tabular", entityType="Invoice", columns=["name"], accessType="public")
        unused = W().report("dir", "unused", type="tabular", entityType="Invoice", columns=["name"],
                            accessType="public")
        metric = self.make_set("usage", [report_row("count", used["id"])])
        status, payload, _ = W().client("dir").get("Report", select="id,usedInMetrics", maxSize=200,
                                                   **{"where[0][type]": "startsWith", "where[0][attribute]": "name",
                                                      "where[0][value]": W().tag})
        self.assertEqual(200, status)
        marks = {r["id"]: r.get("usedInMetrics") for r in payload["list"]}
        self.assertTrue(marks[used["id"]])
        self.assertFalse(marks[unused["id"]])
        must(W().client("dir").delete(f"ReportMetricSet/{metric['id']}"), "delete set")
        W().forget("ReportMetricSet", metric["id"])
        status, payload, _ = W().client("dir").get("Report", select="id,usedInMetrics", maxSize=200,
                                                   **{"where[0][type]": "equals", "where[0][attribute]": "id",
                                                      "where[0][value]": used["id"]})
        self.assertFalse(payload["list"][0].get("usedInMetrics"))


class DeletionTest(Case):
    def test_deleting_a_set_removes_its_dashlets_everywhere(self):
        doomed = self.make_set("doomed", [])
        kept = self.make_set("kept", [])
        layout = [{"id": "t1", "name": "Tab 1", "layout": [
            {"id": "dA", "name": "ReportMetrics", "x": 0, "y": 0, "width": 2, "height": 2},
            {"id": "dB", "name": "ReportMetrics", "x": 2, "y": 0, "width": 2, "height": 2},
            {"id": "dC", "name": "Stream", "x": 0, "y": 2, "width": 2, "height": 2}]},
                  {"id": "t2", "name": "Tab 2", "layout": [
                      {"id": "dD", "name": "ReportMetrics", "x": 0, "y": 0, "width": 2, "height": 2}]}]
        options = {"dA": {"metricSetId": doomed["id"], "title": "a"}, "dB": {"metricSetId": kept["id"], "title": "b"},
                   "dC": {"title": "c"}, "dD": {"metricSetId": doomed["id"], "title": "d"}}
        for key in ("dir", "dir2"):
            self.ok(W().admin.put(f"Preferences/{W().uid[key]}", {"dashboardLayout": layout,
                                                                   "dashletsOptions": options}))
        template = W().create("DashboardTemplate", {"name": f"{W().tag} template", "layout": layout,
                                                    "dashletsOptions": options})
        settings = self.ok(W().admin.get("Settings"))
        saved_settings = {"dashboardLayout": settings.get("dashboardLayout"),
                          "dashletsOptions": settings.get("dashletsOptions")}
        try:
            self.ok(W().admin.put("Settings", {"dashboardLayout": layout, "dashletsOptions": options}))
            must(W().client("dir").delete(f"ReportMetricSet/{doomed['id']}"), "delete set")
            W().forget("ReportMetricSet", doomed["id"])

            def ids(tabs):
                return [[item["id"] for item in tab["layout"]] for tab in tabs]

            for key in ("dir", "dir2"):
                prefs = self.ok(W().admin.get(f"Preferences/{W().uid[key]}"))
                self.assertEqual([["dB", "dC"], []], ids(prefs["dashboardLayout"]), key)
                self.assertEqual({"dB", "dC"}, set(prefs["dashletsOptions"]), key)
            stored = self.ok(W().admin.get(f"DashboardTemplate/{template['id']}"))
            self.assertEqual([["dB", "dC"], []], ids(stored["layout"]))
            self.assertEqual({"dB", "dC"}, set(stored["dashletsOptions"]))
            settings = self.ok(W().admin.get("Settings"))
            self.assertEqual([["dB", "dC"], []], ids(settings["dashboardLayout"]))
            self.assertEqual(404, metric_values(W().client("dir"), doomed["id"])[0])
        finally:
            self.ok(W().admin.put("Settings", saved_settings))


if __name__ == "__main__":
    unittest.main()
