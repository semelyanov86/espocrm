"""Stage 05.2 acceptance tests: the report on a dashboard (D-109, D-110) on the local stand, synthetic data.

The dashboard part (main filter field: an enum field or the owner of the main entity; default mode), the main filter
of a run as a quick filter of that field — the same numbers as the report with the equivalent condition, also in the
charts and the drill-down — the options offered in the dashlet header, and the answers a viewer without access gets.
"""
import unittest

from common import BY_STATUS, D, World, all_of, cond, drill_down, label, num, reference_data, run, summaries

S = {}


def setUpModule():
    world = World()
    unittest.addModuleCleanup(world.cleanup)
    S["w"] = world
    world.user("dir", roles=["Директор"])
    world.user("dir2", roles=["Директор"])
    world.user("other", roles=["Менеджер по продажам"])
    S["ref"] = reference_data(world)


def W():
    return S["w"]


def R():
    return S["ref"]


class DashletTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = summaries(W(), "dir", "dashboard", [{"field": "status"}],
                               {"items": [{"type": "bar", "aggregate": "SUM:grandTotal"}]},
                               dashboard={"filterField": "assignedUser", "mode": "chart"})

    def ok(self, result):
        status, payload, _ = result
        self.assertEqual(200, status, f"HTTP {status}: {payload}")
        return payload

    def test_dashboard_field_rules(self):
        for field in ("status", "assignedUser"):
            report = summaries(W(), "dir", "field " + field, [{"field": "status"}], None,
                               dashboard={"filterField": field})
            self.assertEqual({"filterField": field, "mode": "table"}, report["dashboard"])
        for field in ("name", "account", "account.name", "dateInvoiced"):
            result = W().try_report("dir", "bad " + field, type="summaries", entityType="Invoice",
                                    groups=[{"field": "status"}], aggregates=[{"function": "COUNT"}],
                                    dashboard={"filterField": field})
            self.assertEqual((400, "badDashboardFilter"), (result[0], label(result)), field)
        tabular = W().try_report("dir", "tabular chart", type="tabular", entityType="Invoice", columns=["name"],
                                 dashboard={"mode": "chart"})
        self.assertEqual((400, "notForType"), (tabular[0], label(tabular)))

    def test_options_of_the_main_filter(self):
        result = self.ok(run(W().client("dir"), self.report["id"], withDashboardFilterOptions=True,
                             withQuickFilterOptions=False))
        self.assertEqual({"filterField": "assignedUser", "mode": "chart"}, result["dashboard"])
        options = result["dashboardFilter"]
        self.assertEqual("assignedUser", options["field"])
        self.assertEqual({W().uid["dir"], W().uid["dir2"]}, {o["v"] for o in options["options"]})
        self.assertNotIn("quickFilters", result)
        # Without the flag no options are computed.
        self.assertNotIn("dashboardFilter", self.ok(run(W().client("dir"), self.report["id"])))

    def test_main_filter_equals_the_equivalent_condition(self):
        quick = [{"field": "assignedUser", "mode": "in", "values": [W().uid["dir2"]]}]
        filtered = self.ok(run(W().client("dir"), self.report["id"], quickFilters=quick))
        condition = self.ok(run(W().client("dir"), self.report["id"], filters=all_of(
            W().name_filter(), cond("assignedUser", "in", [W().uid["dir2"]], attribute="assignedUserId"))))
        # Only i7 (Created, 500.00) belongs to dir2.
        self.assertEqual((1, 1), (filtered["recordCount"], condition["recordCount"]))
        self.assertEqual([("Created", D("500"))], [(n["key"]["v"], num(n["values"][1])) for n in filtered["tree"]])
        self.assertEqual([n["values"] for n in condition["tree"]], [n["values"] for n in filtered["tree"]])
        self.assertEqual(D("500"), num(filtered["charts"]["items"][0]["series"][0]["points"][0]))
        status, ids = drill_down(W().client("dir"), "Invoice", self.report["id"], ["Created"], quickFilters=quick)
        self.assertEqual((200, {R()["i7"]}), (status, ids))

    def test_other_quick_filters_stay_refused(self):
        result = run(W().client("dir"), self.report["id"],
                     quickFilters=[{"field": "status", "mode": "in", "values": ["Sent"]}])
        self.assertEqual((400, "badQuickFilter"), (result[0], label(result)))

    def test_all_values_is_the_whole_report(self):
        result = self.ok(run(W().client("dir"), self.report["id"]))
        self.assertEqual({k: v[1] for k, v in BY_STATUS.items()},
                         {n["key"]["v"]: num(n["values"][1]) for n in result["tree"]})

    def test_a_viewer_without_access_gets_no_data(self):
        private = summaries(W(), "dir", "private", [{"field": "status"}], {"items": [{"type": "bar"}]},
                            accessType="private")
        self.assertEqual(403, run(W().client("other"), private["id"])[0])
        self.assertEqual(403, W().client("other").get(f"Report/{private['id']}")[0])
        self.assertEqual(404, run(W().client("dir"), "0000000000000000x")[0])


if __name__ == "__main__":
    unittest.main()
