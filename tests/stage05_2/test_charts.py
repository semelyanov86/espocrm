"""Stage 05.2 acceptance tests: chart data of report runs (D-105…D-108, D-114) on the local stand, synthetic data.

  task test:stage05.2   (python3 -m unittest discover -s tests/stage05_2 -v)

The chart points of a run are the cells of its table and equal the reference sums to the kopeck: axis group 1 of
summaries and of a matrix (row totals), COUNT without a COUNT aggregate, the axis «group 1 → group 2» (pairs, missing
pairs, series order), progress lines, pie shares; a point's path opens exactly the records of its group; the rules of
the charts part; its canonical form; the charts of the standard reports and their backfill.
"""
import json
import unittest
from pathlib import Path

from common import (BY_STATUS, BY_STATUS_ACCOUNT, SUM_ALL, D, World, all_of, avg8, drill_down, espo_console, label,
                    num, progress, reference_data, run, sql, summaries)

S = {}
REPO = Path(__file__).resolve().parents[2]


def setUpModule():
    world = World()
    unittest.addModuleCleanup(world.cleanup)
    S["w"] = world
    world.user("dir", roles=["Директор"])
    world.user("dir2", roles=["Директор"])
    S["ref"] = reference_data(world)


def W():
    return S["w"]


def R():
    return S["ref"]


class Case(unittest.TestCase):
    def ok(self, result):
        status, payload, _ = result
        self.assertEqual(200, status, f"HTTP {status}: {payload}")
        return payload

    def refused(self, result, status, key=None):
        self.assertEqual(status, result[0], f"expected HTTP {status}, got {result[0]}: {result[1]}")
        if key:
            self.assertEqual(key, label(result))

    def run_ok(self, report_id, by="dir", **body):
        return self.ok(run(W().client(by), report_id, **body))


class GroupOneTest(Case):
    @classmethod
    def setUpClass(cls):
        cls.report = summaries(W(), "dir", "by status", [{"field": "status"}], {
            "title": "Счета", "progressLines": ["MIN", "AVG", "MAX"],
            "items": [{"type": "bar", "aggregate": "SUM:grandTotal"}, {"type": "line"},
                      {"type": "piePercent", "aggregate": "SUM:grandTotal"}]})

    def test_points_are_the_table_cells_and_the_reference_sums(self):
        result = self.run_ok(self.report["id"])
        charts = result["charts"]
        keys = [n["key"]["v"] for n in result["tree"]]

        self.assertEqual(keys, [c["key"]["v"] for c in charts["categories"]])
        self.assertEqual([[k] for k in keys], [c["path"] for c in charts["categories"]])
        self.assertEqual(len(result["tree"]), len(charts["categories"]))
        bar, line, pie = charts["items"]
        for i, node in enumerate(result["tree"]):
            point = bar["series"][0]["points"][i]
            self.assertEqual(node["values"][1]["v"], point["v"])
            self.assertEqual(node["values"][1]["f"], point["f"])
            self.assertEqual(BY_STATUS[node["key"]["v"]][1], num(point))
            # COUNT is the group's exact count even when chosen as the record count of the chart.
            self.assertEqual(BY_STATUS[node["key"]["v"]][0], line["series"][0]["points"][i]["v"])
        self.assertEqual(SUM_ALL, sum(num(p) for p in bar["series"][0]["points"]))
        self.assertEqual("Счета", charts["title"])

    def test_progress_lines_are_running_values_of_the_categories(self):
        result = self.run_ok(self.report["id"])
        bar = result["charts"]["items"][0]
        values = [num(p) for p in bar["series"][0]["points"]]
        expected = progress(values)
        for fn in ("MIN", "AVG", "MAX"):
            self.assertEqual(expected[fn], [D(c["v"]) for c in bar["progress"][fn]], fn)
        self.assertTrue(bar["progress"]["AVG"][1]["f"].endswith("₽"))
        # Pies draw no progress lines.
        self.assertEqual({}, result["charts"]["items"][2]["progress"])

    def test_pie_shares_are_exact_percents_of_the_positive_values(self):
        pie = self.run_ok(self.report["id"])["charts"]["items"][2]
        for point in pie["series"][0]["points"]:
            self.assertEqual(avg8(num(point) * 100, SUM_ALL), D(point["share"]["v"]))

    def test_a_point_path_opens_the_records_of_its_group(self):
        result = self.run_ok(self.report["id"])
        expected = {"Created": {"i1", "i3", "i6", "i7"}, "Sent": {"i2", "i4"}, "Approved": {"i5"}}
        for category in result["charts"]["categories"]:
            status, ids = drill_down(W().client("dir"), "Invoice", self.report["id"], category["path"])
            self.assertEqual(200, status)
            self.assertEqual({R()[k] for k in expected[category["key"]["v"]]}, ids)

    def test_the_group_limit_limits_the_categories(self):
        report = summaries(W(), "dir", "top 2", [{"field": "status"}], {"items": [{"type": "bar"}]},
                           groupSort={"aggregate": "SUM:grandTotal", "direction": "desc"}, groupLimit=2)
        charts = self.run_ok(report["id"])["charts"]
        self.assertEqual(["Created", "Sent"], [c["key"]["v"] for c in charts["categories"]])


class SecondGroupTest(Case):
    @classmethod
    def setUpClass(cls):
        # Groups by the sum ascending: «Approved» (only a3) comes first, so the order in which the accounts appear
        # (a3, a1, a2) differs from the order of group 2 the series must follow.
        cls.report = summaries(W(), "dir", "status account", [{"field": "status"}, {"field": "account"}],
                               {"axis": "group1group2", "items": [{"type": "stackedBar", "aggregate": "SUM:grandTotal"}]},
                               groupSort={"aggregate": "SUM:grandTotal", "direction": "asc"})

    def test_series_are_the_accounts_and_points_the_pairs(self):
        result = self.run_ok(self.report["id"])
        charts = result["charts"]
        item = charts["items"][0]
        accounts = {R()[k]: k for k in ("a1", "a2", "a3")}

        self.assertEqual("group1group2", charts["axis"])
        self.assertEqual(sorted(accounts), sorted(s["key"]["v"] for s in item["series"]))
        # Series in the order of group 2 (accounts by name: Альфа, Бета, Гамма).
        self.assertEqual(["a1", "a2", "a3"], [accounts[s["key"]["v"]] for s in item["series"]])
        for c, category in enumerate(charts["categories"]):
            for series in item["series"]:
                pair = (category["key"]["v"], accounts[series["key"]["v"]])
                point = series["points"][c]
                if pair in BY_STATUS_ACCOUNT:
                    self.assertEqual(BY_STATUS_ACCOUNT[pair], num(point), pair)
                    self.assertEqual([category["key"]["v"], series["key"]["v"]], point["path"])
                else:
                    self.assertIsNone(point, pair)

    def test_a_pair_path_opens_the_records_of_the_pair(self):
        result = self.run_ok(self.report["id"])
        item = result["charts"]["items"][0]
        a1 = next(s for s in item["series"] if s["key"]["v"] == R()["a1"])
        created = [c["key"]["v"] for c in result["charts"]["categories"]].index("Created")
        status, ids = drill_down(W().client("dir"), "Invoice", self.report["id"], a1["points"][created]["path"])
        self.assertEqual((200, {R()["i1"], R()["i7"]}), (status, ids))

    def test_rings_of_a_pie_give_both_levels(self):
        report = summaries(W(), "dir", "rings", [{"field": "status"}, {"field": "account"}],
                           {"axis": "group1group2", "items": [{"type": "pie", "aggregate": "SUM:grandTotal"}]})
        item = self.run_ok(report["id"])["charts"]["items"][0]
        self.assertEqual(sorted(v for _, v in BY_STATUS.values()), sorted(num(p) for p in item["inner"]))
        outer = [p for s in item["series"] for p in s["points"] if p]
        self.assertEqual(sorted(BY_STATUS_ACCOUNT.values()), sorted(num(p) for p in outer))
        self.assertEqual(avg8(D("20000.00") * 100, SUM_ALL),
                         D(next(p for p in outer if num(p) == D("20000.00"))["share"]["v"]))

    def test_matrix_rows_and_columns(self):
        report = W().report("dir", "matrix", type="matrix", entityType="InvoiceItem",
                            groups=[{"field": "product"}, {"field": "invoice.dateInvoiced", "granularity": "month"}],
                            aggregates=[{"function": "SUM", "field": "quantity"}],
                            filters=all_of({"field": "invoice.name", "where": {"type": "startsWith",
                                                                               "attribute": "name", "value": W().tag}}),
                            charts={"axis": "group1group2", "items": [{"type": "line", "aggregate": "SUM:quantity"}]})
        result = self.run_ok(report["id"])
        matrix, item = result["matrix"], result["charts"]["items"][0]
        self.assertEqual([c["key"]["v"] for c in matrix["columns"]], [s["key"]["v"] for s in item["series"]])
        for r, row in enumerate(matrix["rows"]):
            for c, series in enumerate(item["series"]):
                cell = matrix["cells"][r][c]
                point = series["points"][r]
                self.assertEqual(None if cell is None else cell["values"][0]["v"], None if point is None else point["v"])
        # Axis group 1: the row totals; product p1 has 4 units, p2 6.5, p3 4.
        saved = self.ok(W().client("dir").put(f"Report/{report['id']}", {"charts": {"items": [{"type": "bar",
                                                                                  "aggregate": "SUM:quantity"}]}}))
        self.assertEqual("group1", saved["charts"]["axis"])
        rows = self.run_ok(report["id"])
        totals = {R()[k]: v for k, v in (("p1", D("4")), ("p2", D("6.5")), ("p3", D("4")))}
        points = rows["charts"]["items"][0]["series"][0]["points"]
        self.assertEqual([totals[c["key"]["v"]] for c in rows["charts"]["categories"]], [num(p) for p in points])


class RulesTest(Case):
    def refused_report(self, key, **definition):
        self.refused(W().try_report("dir", "bad", entityType="Invoice", **definition), 400, key)

    def test_charts_rules(self):
        groups1 = [{"field": "status"}]
        groups2 = [{"field": "status"}, {"field": "account"}]
        aggregates = [{"function": "COUNT"}]
        self.refused_report("notForType", type="tabular", columns=["name"], charts={"items": [{"type": "bar"}]})
        self.refused_report("chartAxisNotAllowed", type="summaries", groups=groups1, aggregates=aggregates,
                            charts={"axis": "group1group2", "items": [{"type": "bar"}]})
        self.refused_report("chartAxisNotAllowed", type="summariesWithDetails", groups=groups1, columns=["name"],
                            aggregates=aggregates, charts={"axis": "group1group2", "items": [{"type": "bar"}]})
        self.refused_report("chartAxisOneChart", type="summaries", groups=groups2, aggregates=aggregates,
                            charts={"axis": "group1group2", "items": [{"type": "bar"}, {"type": "line"}]})
        self.refused_report("chartFunnelSecondGroup", type="summaries", groups=groups2, aggregates=aggregates,
                            charts={"axis": "group1group2", "items": [{"type": "funnel"}]})
        self.refused_report("chartProgressSecondGroup", type="summaries", groups=groups2, aggregates=aggregates,
                            charts={"axis": "group1group2", "progressLines": ["AVG"], "items": [{"type": "bar"}]})
        self.refused_report("badChartAggregate", type="summaries", groups=groups1, aggregates=aggregates,
                            charts={"items": [{"type": "bar", "aggregate": "SUM:grandTotal"}]})
        self.refused_report("badChartType", type="summaries", groups=groups1, aggregates=aggregates,
                            charts={"items": [{"type": "pie3d"}]})
        self.refused_report("tooMany", type="summaries", groups=groups1, aggregates=aggregates,
                            charts={"items": [{"type": "bar"}] * 4})

    def test_charts_are_stored_canonically_and_kept_by_partial_saves(self):
        report = W().report("dir", "canonical", type="summaries", entityType="Invoice", groups=[{"field": "status"}],
                            aggregates=[{"function": "COUNT"}], charts=None)
        self.assertEqual({"title": "", "position": "top", "collapseTable": False, "axis": "group1",
                          "progressLines": [], "items": []}, report["charts"])
        self.assertEqual({"filterField": None, "mode": "table"}, report["dashboard"])
        rid = report["id"]
        self.ok(W().client("dir").put(f"Report/{rid}", {"charts": {"items": [{"type": "pie"}]}}))
        self.ok(W().client("dir").put(f"Report/{rid}", {"name": W().tag + " canonical 2"}))
        stored = sql(f"SELECT charts FROM report WHERE id = '{rid}'")[0][0]
        self.assertEqual([{"type": "pie", "aggregate": "COUNT"}], json.loads(stored)["items"])

    def test_a_chart_of_a_closed_field_is_refused_to_its_viewer(self):
        role = W().role("no total", {"Invoice": {"create": "no", "read": "all", "edit": "no", "delete": "no"},
                                     "Account": {"read": "all"}},
                        field_data={"Invoice": {"grandTotal": {"read": "no", "edit": "no"}}})
        W().user("blind", role_ids=[role])
        report = summaries(W(), "dir", "public sums", [{"field": "status"}],
                           {"items": [{"type": "bar", "aggregate": "SUM:grandTotal"}]}, accessType="public")
        self.refused(run(W().client("blind"), report["id"]), 403)


class SeedTest(Case):
    def test_standard_reports_have_the_charts_of_their_manifests(self):
        rows = dict(sql("SELECT seed_key, charts FROM report WHERE seed_key IS NOT NULL AND deleted = 0"))
        self.assertEqual(29, len(rows))
        with_charts = 0
        for path in sorted(REPO.glob("custom/Espo/Modules/Itvolga/Resources/reports/standard/*.json")):
            manifest = json.loads(path.read_text(encoding="utf-8"))
            items = (manifest["definition"].get("charts") or {}).get("items")
            if items:
                with_charts += 1
                self.assertEqual(items, json.loads(rows[manifest["seedKey"]])["items"], manifest["seedKey"])
            elif rows[manifest["seedKey"]] != "NULL":
                # Inserted or saved since the charts exist: the canonical empty part.
                self.assertEqual([], json.loads(rows[manifest["seedKey"]])["items"], manifest["seedKey"])
        self.assertEqual(18, with_charts)

    def test_backfill_fills_only_reports_never_saved_since(self):
        key = "leads-by-status"
        original = sql(f"SELECT charts, modified_at FROM report WHERE seed_key = '{key}'")[0]
        try:
            sql(f"UPDATE report SET charts = NULL WHERE seed_key = '{key}'")
            output = espo_console("itvolga-setup-reports")
            self.assertIn(f"report ~ {key}: charts", output)
            restored = json.loads(sql(f"SELECT charts FROM report WHERE seed_key = '{key}'")[0][0])
            self.assertEqual([{"type": "pie", "aggregate": "COUNT"}], restored["items"])
            self.assertNotIn("report ~", espo_console("itvolga-setup-reports"))
        finally:
            charts = original[0].encode("utf-8").hex()
            sql(f"UPDATE report SET charts = CONVERT(UNHEX('{charts}') USING utf8mb4), modified_at = '{original[1]}' "
                f"WHERE seed_key = '{key}'")


if __name__ == "__main__":
    unittest.main()
