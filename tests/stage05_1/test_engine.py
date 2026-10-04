"""Stage 05.1 acceptance tests: the report engine on the local stand — exact values ("до копейки"), synthetic data only.

  task test:stage05.1   (python3 -m unittest discover -s tests/stage05_1 -v)

The reference data set of fixture.reference_data() (seven invoices of this month and the last one with known sums) is
reported in every type: tabular (values, sorting, row limit, paging, totals over all filtered rows, custom
calculations, quick filters), summaries (two levels, COUNT/SUM/weighted AVG, group sort and limit, HAVING),
summaries with details, a matrix of invoice lines (product × month of the invoice), date granularities, COUNT DISTINCT
over a to-many link and the refusal of inflated sums, one-off conditions of a run, relative periods, the comparison of
two date fields, "current user", conditions on related records, the drill-down list of a group (core list with the
where item `itvolgaReport`) and that a run writes nothing. Numbers are compared as decimals.
"""
import re
import time
import unittest
from decimal import ROUND_HALF_UP

from fixture import (D, World, all_of, cond, drill_down, espo_console, label, must, num, period_key, reference_data, run,
                     sql)

S = {}
SUM_ALL = D("34477.39")


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


def inv(key):
    return R()["invoices"][key]


def names(result):
    """Short names (i1…i7) of the rows of a tabular result whose first column is the name."""
    tag = W().tag + " "
    return [row["cells"][0]["v"].removeprefix(tag) for row in result["rows"]]


def node(n):
    """(key, count, values as decimals) of a group node or a grand total."""
    return (n["key"]["v"] if "key" in n else None, n["count"], [num(v) for v in n["values"]])


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

    def assertDecimal(self, expected, cell, msg=None):
        self.assertEqual(D(expected), num(cell), msg)

    def names_of(self, report_id, by="dir", **body):
        return set(names(self.run_ok(report_id, by, noLimit=True, maxSize=200, **body)))


class TabularTest(Case):
    """Columns [name, account, status, dateInvoiced, grandTotal] sorted by grandTotal desc, row limit 5."""

    @classmethod
    def setUpClass(cls):
        cls.report = W().report(
            "dir", "tabular", entityType="Invoice",
            columns=["name", "account", "status", "dateInvoiced", "grandTotal"],
            sorting=[{"column": "grandTotal", "direction": "desc"}], rowLimit=5,
            totals=[{"column": "grandTotal", "functions": ["SUM", "AVG", "MIN", "MAX"]}],
            calculations=[{"label": "Треть", "expression": "round({grandTotal} / 3, 2)", "functions": ["SUM"]},
                          {"label": "НДС 20 %", "expression": "{grandTotal} * 0.2", "functions": ["SUM", "MAX"]}],
            filters=all_of(W().name_filter()), quickFilters=["status", "contact"])
        cls.id = cls.report["id"]

    def test_values_and_order_by_sorting(self):
        result = self.run_ok(self.id)
        self.assertEqual(["i1", "i3", "i4", "i2", "i7"], names(result))
        for row in result["rows"]:
            spec = inv(row["cells"][0]["v"].split()[-1])
            self.assertEqual(spec["id"], row["id"])
            account, status, dated, total = row["cells"][1:]
            self.assertEqual((R()[spec["account"]], "Account"), (account["id"], account["et"]))
            self.assertEqual(spec["status"], status["v"])
            self.assertEqual(spec["date"].isoformat(), dated["v"])
            self.assertDecimal(spec["total"], total)
            self.assertEqual("RUB", total.get("cur"))
        self.assertEqual(["c:name", "c:account", "c:status", "c:dateInvoiced", "c:grandTotal"],
                         [c["key"] for c in result["columns"]])

    def test_sorting_by_a_link_column_and_then_by_a_number(self):
        report = W().report("dir", "by account", entityType="Invoice", columns=["name", "account", "grandTotal"],
                            sorting=[{"column": "account", "direction": "desc"},
                                     {"column": "grandTotal", "direction": "asc"}],
                            rowLimit=None, filters=all_of(W().name_filter()))
        # Accounts by the name shown (Гамма, Бета, Альфа), then the amount ascending inside each account.
        self.assertEqual(["i6", "i5", "i4", "i3", "i7", "i2", "i1"], names(self.run_ok(report["id"])))

    def test_row_limit(self):
        result = self.run_ok(self.id)
        self.assertEqual((7, 7, 5), (result["recordCount"], result["rowCount"], result["availableRows"]))
        self.assertEqual(5, result["limits"]["rowLimit"])
        self.assertTrue(result["limits"]["rowLimitHit"])
        self.assertFalse(result["limits"]["capHit"])
        everything = self.run_ok(self.id, noLimit=True)
        self.assertEqual(["i1", "i3", "i4", "i2", "i7", "i5", "i6"], names(everything))
        self.assertFalse(everything["limits"]["rowLimitHit"])

    def test_paging_stays_within_the_row_limit(self):
        self.assertEqual(["i4", "i2"], names(self.run_ok(self.id, offset=2, maxSize=2)))
        self.assertEqual(["i7"], names(self.run_ok(self.id, offset=4, maxSize=2)))
        self.assertEqual([], names(self.run_ok(self.id, offset=5, maxSize=2)))

    def check_totals(self, totals, total, avg, low, high):
        cells = totals["c:grandTotal"]
        self.assertDecimal(total, cells["SUM"])
        self.assertDecimal(low, cells["MIN"])
        self.assertDecimal(high, cells["MAX"])
        # AVG is the exact quotient of SQL (not rounded to the kopeck in `v`); `f` shows the kopecks.
        self.assertLess(abs(num(cells["AVG"]) - avg), D("1e-9"))
        kopecks = str(avg.quantize(D("0.01"), rounding=ROUND_HALF_UP)).replace(".", "")
        self.assertEqual(kopecks, re.sub(r"\D", "", cells["AVG"]["f"]))

    def test_totals_cover_all_filtered_rows_whatever_the_limit_and_page(self):
        for body in ({}, {"offset": 2, "maxSize": 2}, {"offset": 5, "maxSize": 1}, {"noLimit": True}):
            result = self.run_ok(self.id, **body)
            self.check_totals(result["totals"], SUM_ALL, SUM_ALL / 7, "0.01", "19500")

    def test_totals_follow_the_quick_filters(self):
        result = self.run_ok(self.id, quickFilters=[{"field": "status", "mode": "in", "values": ["Sent"]}])
        self.assertEqual(["i4", "i2"], names(result))
        self.check_totals(result["totals"], D("3469.62"), D("3469.62") / 2, "1000.50", "2469.12")

    def test_custom_calculations_per_row_and_totals(self):
        result = self.run_ok(self.id)
        third = {"i1": "6500", "i3": "3666.66", "i4": "823.04", "i2": "333.50", "i7": "166.67"}
        for name, row in zip(names(result), result["rows"]):
            self.assertDecimal(third[name], row["calc"][0], name)
            self.assertDecimal(inv(name)["total"] * D("0.2"), row["calc"][1], name)
        self.assertEqual(["k:k1", "k:k2"], [c["key"] for c in result["calculations"]])
        # Totals over all seven filtered rows (i5: 2.59, i6: 0.00 included), not the five shown.
        self.assertDecimal("11492.46", result["calculationTotals"]["k:k1"]["SUM"])
        self.assertDecimal("6895.478", result["calculationTotals"]["k:k2"]["SUM"])
        self.assertDecimal("3900", result["calculationTotals"]["k:k2"]["MAX"])
        self.assertFalse(result["limits"]["calculationsCapped"])

    def test_quick_filter_options(self):
        options = {q["field"]: q for q in self.run_ok(self.id)["quickFilters"]}
        self.assertEqual(["Created", "Approved", "Sent"], [o["v"] for o in options["status"]["options"]])
        self.assertEqual([R()["c1"], R()["c2"], None], [o["v"] for o in options["contact"]["options"]])
        self.assertTrue(options["contact"]["options"][-1].get("empty"))
        self.assertFalse(options["contact"]["truncated"])
        # The options stay the same while quick filters are ticked.
        ticked = self.run_ok(self.id, quickFilters=[{"field": "status", "mode": "in", "values": ["Sent"]}])
        self.assertEqual(["Created", "Approved", "Sent"],
                         [o["v"] for o in {q["field"]: q for q in ticked["quickFilters"]}["status"]["options"]])
        self.assertNotIn("quickFilters", self.run_ok(self.id, withQuickFilterOptions=False))

    def test_quick_filters_in_not_in_and_the_empty_item(self):
        c1 = R()["c1"]
        cases = [
            ({"field": "status", "mode": "in", "values": ["Sent"]}, {"i2", "i4"}),
            ({"field": "status", "mode": "notIn", "values": ["Created"]}, {"i2", "i4", "i5"}),
            ({"field": "contact", "mode": "in", "values": [c1]}, {"i1"}),
            ({"field": "contact", "mode": "in", "values": [c1], "includeEmpty": True},
             {"i1", "i2", "i4", "i5", "i6", "i7"}),
            ({"field": "contact", "mode": "in", "values": [], "includeEmpty": True}, {"i2", "i4", "i5", "i6", "i7"}),
            # notIn: the ticked items are excluded — "(empty)" is one of them when includeEmpty is set.
            ({"field": "contact", "mode": "notIn", "values": [c1]}, {"i2", "i3", "i4", "i5", "i6", "i7"}),
            ({"field": "contact", "mode": "notIn", "values": [c1], "includeEmpty": True}, {"i3"}),
        ]
        for quick, expected in cases:
            with self.subTest(quick=quick):
                result = self.run_ok(self.id, noLimit=True, quickFilters=[quick])
                self.assertEqual(expected, set(names(result)))
                self.assertEqual(len(expected), result["recordCount"])
        both = self.run_ok(self.id, noLimit=True, quickFilters=[
            {"field": "status", "mode": "in", "values": ["Created"]},
            {"field": "contact", "mode": "in", "values": [], "includeEmpty": True}])
        self.assertEqual({"i6", "i7"}, set(names(both)))

    def test_bad_quick_filters_are_refused(self):
        dir_ = W().client("dir")
        for quick in ({"field": "name", "mode": "in", "values": ["x"]},  # not a quick filter of the report
                      {"field": "status", "mode": "like", "values": ["x"]},
                      {"field": "status", "mode": "in", "values": [{"x": 1}]}):
            self.refused(run(dir_, self.id, quickFilters=[quick]), 400, "badQuickFilter")
        self.refused(run(dir_, self.id, offset=-1), 400, "badPage")
        self.refused(run(dir_, self.id, maxSize=100000), 400, "badPage")


class SummariesTest(Case):
    """Status → account with COUNT, SUM and AVG of grandTotal."""

    AGGREGATES = [{"function": "COUNT"}, {"function": "SUM", "field": "grandTotal"},
                  {"function": "AVG", "field": "grandTotal"}]

    @classmethod
    def summaries(cls, name, **extra):
        return W().report("dir", name, type="summaries", entityType="Invoice",
                          groups=[{"field": "status"}, {"field": "account"}], aggregates=cls.AGGREGATES,
                          filters=all_of(W().name_filter()), **extra)

    @classmethod
    def setUpClass(cls):
        cls.report = cls.summaries("summaries", groupLimit=None)

    def test_two_levels_count_sum_avg_and_grand_total(self):
        result = self.run_ok(self.report["id"])
        a1, a2, a3 = R()["a1"], R()["a2"], R()["a3"]
        tree = result["tree"]
        self.assertEqual([("Created", 4, [D(4), D("31000"), D("7750")]),
                          ("Approved", 1, [D(1), D("7.77"), D("7.77")]),
                          ("Sent", 2, [D(2), D("3469.62"), D("1734.81")])], [node(n) for n in tree])
        self.assertEqual([(a1, 2, [D(2), D("20000"), D("10000")]), (a2, 1, [D(1), D("10999.99"), D("10999.99")]),
                          (a3, 1, [D(1), D("0.01"), D("0.01")])], [node(n) for n in tree[0]["children"]])
        self.assertEqual([(a3, 1, [D(1), D("7.77"), D("7.77")])], [node(n) for n in tree[1]["children"]])
        self.assertEqual([(a1, 1, [D(1), D("1000.50"), D("1000.50")]), (a2, 1, [D(1), D("2469.12"), D("2469.12")])],
                         [node(n) for n in tree[2]["children"]])
        grand = node(result["grandTotal"])
        self.assertEqual((7, D(7), SUM_ALL), (grand[1], grand[2][0], grand[2][1]))
        self.assertLess(abs(grand[2][2] - SUM_ALL / 7), D("1e-9"))
        self.assertEqual(["a:COUNT", "a:SUM:grandTotal", "a:AVG:grandTotal"], [a["key"] for a in result["aggregates"]])
        self.assertFalse(result["limits"]["groupLimitHit"])
        self.assertEqual(3, result["limits"]["groupCount"])

    def test_avg_is_weighted_by_records(self):
        created = self.run_ok(self.report["id"])["tree"][0]
        count, total, avg = (num(v) for v in created["values"])
        self.assertEqual(total / count, avg)
        children = [num(c["values"][2]) for c in created["children"]]
        self.assertNotEqual(sum(children) / len(children), avg, "AVG must not be an average of averages")

    def test_group_sort_by_sum_desc_and_group_limit(self):
        report = self.summaries("top2", groupSort={"aggregate": "SUM:grandTotal", "direction": "desc"},
                                groupLimit=2)
        result = self.run_ok(report["id"])
        self.assertEqual(["Created", "Sent"], [n["key"]["v"] for n in result["tree"]])
        self.assertEqual(2, len(result["tree"][1]["children"]))
        self.assertTrue(result["limits"]["groupLimitHit"])
        self.assertEqual((2, 3), (result["limits"]["groupLimit"], result["limits"]["groupCount"]))
        grand = node(result["grandTotal"])
        self.assertEqual((6, D(6), D("34469.62")), (grand[1], grand[2][0], grand[2][1]))
        everything = self.run_ok(report["id"], noLimit=True)
        self.assertEqual(["Created", "Sent", "Approved"], [n["key"]["v"] for n in everything["tree"]])
        self.assertFalse(everything["limits"]["groupLimitHit"])

    def test_having_removes_a_group(self):
        report = self.summaries("having", havingFilters=[
            {"aggregate": "SUM:grandTotal", "operator": "greaterThan", "value": "1000"}])
        result = self.run_ok(report["id"])
        self.assertEqual(["Created", "Sent"], [n["key"]["v"] for n in result["tree"]])
        grand = node(result["grandTotal"])
        self.assertEqual((6, D("34469.62")), (grand[1], grand[2][1]))
        between = self.summaries("between", havingFilters=[
            {"aggregate": "COUNT", "operator": "between", "value": ["1", "2"]}])
        self.assertEqual(["Approved", "Sent"], [n["key"]["v"] for n in self.run_ok(between["id"])["tree"]])


class DetailsTest(Case):
    """Summaries with details: account groups with the invoice rows, sorted by grandTotal desc."""

    @staticmethod
    def details(name, row_limit):
        return W().report("dir", name, type="summariesWithDetails", entityType="Invoice",
                          groups=[{"field": "account"}],
                          aggregates=[{"function": "COUNT"}, {"function": "SUM", "field": "grandTotal"}],
                          columns=["name", "grandTotal"], sorting=[{"column": "grandTotal", "direction": "desc"}],
                          rowLimit=row_limit, filters=all_of(W().name_filter()))

    def test_group_headers_and_rows_per_group(self):
        result = self.run_ok(self.details("details", None)["id"])
        tree = result["tree"]
        self.assertEqual([(R()["a1"], 3, [D(3), D("21000.50")]), (R()["a2"], 2, [D(2), D("13469.11")]),
                          (R()["a3"], 2, [D(2), D("7.78")])], [node(n) for n in tree])
        tag = W().tag + " "
        self.assertEqual([["i1", "i2", "i7"], ["i3", "i4"], ["i5", "i6"]],
                         [[r["cells"][0]["v"].removeprefix(tag) for r in n["rows"]] for n in tree])
        self.assertDecimal("19500", tree[0]["rows"][0]["cells"][1])
        self.assertFalse(result["limits"]["rowLimitHit"])

    def test_row_limit_applies_per_group(self):
        result = self.run_ok(self.details("details1", 1)["id"])
        tag = W().tag + " "
        self.assertEqual([["i1"], ["i3"], ["i5"]],
                         [[r["cells"][0]["v"].removeprefix(tag) for r in n["rows"]] for n in result["tree"]])
        self.assertEqual([3, 2, 2], [n["count"] for n in result["tree"]])
        self.assertTrue(result["limits"]["rowLimitHit"])
        self.assertEqual((7, D("34477.39")), (result["grandTotal"]["count"], num(result["grandTotal"]["values"][1])))


class RawGroupKeyTest(Case):
    """Group keys whose display differs from the SQL value (decimal quantity '1.00000000' shown as 1) still find their
    lower levels and detail rows (review finding of 2026-10-04: lookups used the display value)."""

    @classmethod
    def setUpClass(cls):
        lines = cond("invoice.name", "startsWith", W().tag, attribute="name")
        cls.summaries = W().report("dir", "qty levels", type="summaries", entityType="InvoiceItem",
                                   groups=[{"field": "quantity"}, {"field": "product"}],
                                   aggregates=[{"function": "COUNT"}], filters=all_of(lines))
        cls.details = W().report("dir", "qty details", type="summariesWithDetails", entityType="InvoiceItem",
                                 groups=[{"field": "quantity"}], aggregates=[{"function": "COUNT"}],
                                 columns=["product", "quantity"], rowLimit=None, filters=all_of(lines))

    def test_lower_levels_of_a_decimal_group(self):
        tree = self.run_ok(self.summaries["id"])["tree"]
        self.assertEqual([D("1"), D("2"), D("2.5"), D("3")], [D(n["key"]["v"]) for n in tree])
        self.assertEqual([7, 1, 1, 1], [n["count"] for n in tree])
        self.assertEqual({R()["p1"]: 4, R()["p2"]: 1, R()["p3"]: 2},
                         {c["key"]["v"]: c["count"] for c in tree[0]["children"]})
        for group in tree:
            self.assertEqual(group["count"], sum(c["count"] for c in group["children"]))

    def test_detail_rows_of_a_decimal_group(self):
        tree = self.run_ok(self.details["id"])["tree"]
        self.assertEqual([7, 1, 1, 1], [len(n["rows"]) for n in tree])
        self.assertEqual([n["count"] for n in tree], [len(n["rows"]) for n in tree])


class MatrixTest(Case):
    """Invoice lines: product (rows) × month of invoice.dateInvoiced (columns), COUNT and SUM of the line amount."""

    def test_cells_row_and_column_totals_and_grand_total(self):
        ref = R()
        report = W().report("dir", "matrix", type="matrix", entityType="InvoiceItem",
                            groups=[{"field": "product"}, {"field": "invoice.dateInvoiced", "granularity": "month"}],
                            aggregates=[{"function": "COUNT"}, {"function": "SUM", "field": "amount"}],
                            filters=all_of(cond("product", "in", [ref["p1"], ref["p2"], ref["p3"]],
                                                attribute="productId")))
        result = self.run_ok(report["id"])
        matrix = result["matrix"]
        m1, m0 = period_key(ref["m1"], "month"), period_key(ref["m0"], "month")
        self.assertEqual([ref["p1"], ref["p2"], ref["p3"]], [r["key"]["v"] for r in matrix["rows"]])
        self.assertEqual([m1, m0], [c["key"]["v"] for c in matrix["columns"]])
        self.assertRegex(m0, r"^\d{4}-\d{2}$")
        cells = [[None if c is None else (c["count"], num(c["values"][1])) for c in line] for line in matrix["cells"]]
        self.assertEqual([[None, (4, D("16008.27"))],
                          [(2, D("1000.00")), (1, D("4500"))],
                          [(2, D("12469.12")), (1, D("500"))]], cells)
        self.assertEqual([(4, D("16008.27")), (3, D("5500.00")), (3, D("12969.12"))],
                         [(r["count"], num(r["values"][1])) for r in matrix["rows"]])
        self.assertEqual([(4, D("13469.12")), (6, D("21008.27"))],
                         [(c["count"], num(c["values"][1])) for c in matrix["columns"]])
        self.assertEqual((10, D("34477.39")), (result["grandTotal"]["count"], num(result["grandTotal"]["values"][1])))


class MatrixCapTest(Case):
    """With the run cap at 4 rows, the 3 × 2 matrix of MatrixTest shows 2 rows: every shown cell is there, and the
    columns and the grand total are those of the shown rows (review finding of 2026-10-04: cells beyond the cap were
    missing next to totals of all data)."""

    @staticmethod
    def set_cap(value, kind):
        espo_console("config:set", "itvolgaReportMaxRows", value, f"--type={kind}")
        # PHP-FPM of the stand revalidates data/config.php in OPcache every 2 s (opcache.revalidate_freq).
        time.sleep(3)

    @classmethod
    def setUpClass(cls):
        cls.set_cap("4", "int")
        cls.addClassCleanup(cls.set_cap, "null", "json")

    def test_rows_are_cut_so_that_all_cells_fit(self):
        ref = R()
        report = W().report("dir", "matrix cap", type="matrix", entityType="InvoiceItem",
                            groups=[{"field": "product"}, {"field": "invoice.dateInvoiced", "granularity": "month"}],
                            aggregates=[{"function": "COUNT"}, {"function": "SUM", "field": "amount"}],
                            filters=all_of(cond("product", "in", [ref["p1"], ref["p2"], ref["p3"]],
                                                attribute="productId")))
        result = self.run_ok(report["id"])
        matrix = result["matrix"]
        self.assertTrue(result["limits"]["capHit"])
        self.assertEqual([ref["p1"], ref["p2"]], [r["key"]["v"] for r in matrix["rows"]])
        self.assertEqual([period_key(ref["m1"], "month"), period_key(ref["m0"], "month")],
                         [c["key"]["v"] for c in matrix["columns"]])
        cells = [[None if c is None else (c["count"], num(c["values"][1])) for c in line] for line in matrix["cells"]]
        self.assertEqual([[None, (4, D("16008.27"))], [(2, D("1000.00")), (1, D("4500"))]], cells)
        self.assertEqual([(2, D("1000.00")), (5, D("20508.27"))],
                         [(c["count"], num(c["values"][1])) for c in matrix["columns"]])
        self.assertEqual((7, D("21508.27")), (result["grandTotal"]["count"], num(result["grandTotal"]["values"][1])))


class CalculationReferenceTest(Case):
    """Two calculations share {quantity}: each operand keeps its own value (review finding of 2026-10-04: the shared
    reference took the alias of another column)."""

    def test_a_shared_reference_keeps_every_operand(self):
        report = W().report("dir", "calc refs", entityType="InvoiceItem", columns=["quantity", "unitPrice", "amount"],
                            calculations=[{"label": "q+p", "expression": "{quantity} + {unitPrice}", "functions": ["SUM"]},
                                          {"label": "q+a", "expression": "{quantity} + {amount}", "functions": ["SUM"]}],
                            filters=all_of(cond("invoice.name", "startsWith", W().tag, attribute="name")))
        totals = self.run_ok(report["id"])["calculationTotals"]
        # Ten lines: quantities 14.5, unit prices 29876.17, amounts 34477.39.
        self.assertDecimal("29890.67", totals["k:k1"]["SUM"])
        self.assertDecimal("34491.89", totals["k:k2"]["SUM"])


class GranularityTest(Case):
    def test_date_group_keys(self):
        for granularity in ("day", "week", "month", "quarter", "halfYear", "year"):
            with self.subTest(granularity=granularity):
                report = W().report("dir", f"by {granularity}", type="summaries", entityType="Invoice",
                                    groups=[{"field": "dateInvoiced", "granularity": granularity}],
                                    aggregates=[{"function": "COUNT"}, {"function": "SUM", "field": "grandTotal"}],
                                    filters=all_of(W().name_filter()), groupLimit=None)
                expected = {}
                for spec in R()["invoices"].values():
                    count, total = expected.get(period_key(spec["date"], granularity), (0, D(0)))
                    expected[period_key(spec["date"], granularity)] = (count + 1, total + spec["total"])
                tree = self.run_ok(report["id"])["tree"]
                got = [(n["key"]["v"], n["count"], num(n["values"][1])) for n in tree]
                ordered = sorted(expected, key=lambda k: [int(p) for p in k.replace("/", "-").replace("_", "-")
                                                           .split("-")])
                self.assertEqual([(k, *expected[k]) for k in ordered], got)
                self.assertTrue(all(n["key"]["f"] for n in tree))


class ToManyLinkTest(Case):
    def test_count_is_distinct_over_a_to_many_link(self):
        ref = R()
        report = W().report("dir", "by item product", type="summaries", entityType="Invoice",
                            groups=[{"field": "items.product"}],
                            aggregates=[{"function": "COUNT"}, {"function": "SUM", "link": "items", "field": "amount"}],
                            filters=all_of(W().name_filter()))
        result = self.run_ok(report["id"])
        # p1 is on four lines of three invoices (i5 has it twice): COUNT counts invoices.
        self.assertEqual([(ref["p1"], 3, [D(3), D("16008.27")]), (ref["p2"], 3, [D(3), D("5500")]),
                          (ref["p3"], 3, [D(3), D("12969.12")])], [node(n) for n in result["tree"]])
        self.assertEqual((7, D("34477.39")), (result["grandTotal"]["count"], num(result["grandTotal"]["values"][1])))

    def test_a_to_many_column_repeats_rows_but_counts_records(self):
        tabular = W().report("dir", "lines", entityType="Invoice", columns=["name", "items.product"],
                             filters=all_of(W().name_filter()), rowLimit=None)
        rows = self.run_ok(tabular["id"], noLimit=True)
        self.assertEqual((7, 10, 10), (rows["recordCount"], rows["rowCount"], len(rows["rows"])))
        i5 = [r["cells"][1]["v"] for r in rows["rows"] if r["id"] == inv("i5")["id"]]
        self.assertEqual([R()["p1"], R()["p1"]], i5)

    def test_sums_of_the_main_entity_with_a_to_many_link_are_refused(self):
        self.refused(W().try_report("dir", "inflated", type="summaries", entityType="Invoice",
                                    groups=[{"field": "items.product"}],
                                    aggregates=[{"function": "SUM", "field": "grandTotal"}]), 400,
                     "aggregateMultiplied")
        self.refused(W().try_report("dir", "inflated totals", entityType="Invoice",
                                    columns=["name", "grandTotal", "items.amount"],
                                    totals=[{"column": "grandTotal", "functions": ["SUM"]}]), 400,
                     "aggregateMultiplied")


class ConditionsTest(Case):
    def plain(self, name, *conditions, **extra):
        return W().report("dir", name, entityType="Invoice", columns=["name"], rowLimit=None,
                          sorting=[{"column": "name"}], filters=all_of(W().name_filter(), *conditions), **extra)

    def test_one_off_conditions_replace_the_saved_ones_for_one_run(self):
        report = self.plain("created", cond("status", "in", ["Created"]))
        saved = must(W().admin.get(f"Report/{report['id']}"))["filters"]
        self.assertEqual({"i1", "i3", "i6", "i7"}, self.names_of(report["id"]))
        sent = all_of(W().name_filter(), cond("status", "in", ["Sent"]))
        self.assertEqual({"i2", "i4"}, self.names_of(report["id"], filters=sent))
        stored = must(W().admin.get(f"Report/{report['id']}"))
        self.assertEqual(saved, stored["filters"])
        self.assertEqual(report["modifiedAt"], stored["modifiedAt"])
        self.assertEqual({"i1", "i3", "i6", "i7"}, self.names_of(report["id"]))
        # Without the name condition the one-off filters would reach other data: they really replace the saved ones.
        self.assertEqual({"i3", "i4"}, self.names_of(report["id"], filters=all_of(
            W().name_filter(), cond("account.name", "startsWith", f"{W().tag} Бета"))))

    def test_relative_periods(self):
        report = self.plain("this month", cond("dateInvoiced", "currentMonth"))
        self.assertEqual({"i1", "i2", "i5", "i7"}, self.names_of(report["id"]))
        self.assertEqual({"i3", "i4", "i6"}, self.names_of(report["id"], filters=all_of(
            W().name_filter(), cond("dateInvoiced", "lastMonth"))))
        self.assertEqual({"i1", "i2", "i3", "i4", "i5", "i6", "i7"}, self.names_of(report["id"], filters=all_of(
            W().name_filter(), {"type": "or", "items": [cond("dateInvoiced", "currentMonth"),
                                                         cond("dateInvoiced", "lastMonth")]})))

    def test_compare_two_date_fields(self):
        report = self.plain("overdue at once", cond("dateDue", "compareField",
                                                    {"operator": "lessThan", "field": "dateInvoiced"}))
        self.assertEqual({"i2", "i4"}, self.names_of(report["id"]))
        self.refused(W().try_report("dir", "bad compare", entityType="Invoice", columns=["name"], filters=all_of(
            cond("dateDue", "compareField", {"operator": "lessThan", "field": "createdAt"}))), 400, "badCompareField")

    def test_current_user(self):
        report = self.plain("mine", cond("assignedUser", "isCurrentUser", attribute="assignedUserId"),
                            accessType="public")
        self.assertEqual({"i1", "i2", "i3", "i4", "i5", "i6"}, self.names_of(report["id"], "dir"))
        self.assertEqual({"i7"}, self.names_of(report["id"], "dir2"))
        self.assertEqual(set(), self.names_of(report["id"], "admin"))

    def test_conditions_on_related_records(self):
        by_inn = self.plain("by inn", cond("account.cInn", "equals", "77-SYNTH-A1"))
        self.assertEqual({"i1", "i2", "i7"}, self.names_of(by_inn["id"]))
        by_name = self.plain("by account", cond("account.name", "startsWith", f"{W().tag} Бета"))
        self.assertEqual({"i3", "i4"}, self.names_of(by_name["id"]))
        no_inn = self.plain("no inn", cond("account.cInn", "isNull"))
        self.assertEqual({"i5", "i6"}, self.names_of(no_inn["id"]))

    def test_bad_conditions_are_refused(self):
        dir_ = W().client("dir")
        report = self.plain("plain")
        for filters, key in (
                (all_of(cond("status", "between", ["a", "b"])), "operatorNotAllowed"),
                (all_of(cond("grandTotal", "greaterThan", "1e5")), "badConditionValue"),
                (all_of(cond("status", "in", ["Sent"], attribute="name")), "badCondition"),
                (all_of(cond("noSuchField", "isNull")), "unknownField")):
            with self.subTest(key=key):
                self.refused(run(dir_, report["id"], filters=filters), 400, key)


class DrillDownTest(Case):
    @classmethod
    def setUpClass(cls):
        cls.report = W().report("dir", "drill", type="summaries", entityType="Invoice",
                                groups=[{"field": "status"}, {"field": "account"}], aggregates=[{"function": "COUNT"}],
                                filters=all_of(W().name_filter()), quickFilters=["contact"])

    def ids(self, *keys):
        return {inv(k)["id"] for k in keys}

    def drill(self, path=(), by="dir", **extra):
        status, ids = drill_down(W().client(by), "Invoice", self.report["id"], path, **extra)
        self.assertEqual(200, status)
        return ids

    def test_records_of_a_group_are_exactly_its_records(self):
        result = self.run_ok(self.report["id"])
        for level1 in result["tree"]:
            expected = {s["id"] for s in R()["invoices"].values() if s["status"] == level1["key"]["v"]}
            self.assertEqual(expected, self.drill([level1["key"]["v"]]))
            self.assertEqual(level1["count"], len(expected))
            for level2 in level1["children"]:
                got = self.drill([level1["key"]["v"], level2["key"]["v"]])
                self.assertEqual(level2["count"], len(got))
        self.assertEqual(self.ids("i1", "i7"), self.drill(["Created", R()["a1"]]))
        self.assertEqual(self.ids("i4"), self.drill(["Sent", R()["a2"]]))
        self.assertEqual(set(), self.drill(["Paid"]))
        self.assertEqual(self.ids(*R()["invoices"]), self.drill([]))

    def test_one_off_conditions_and_quick_filters_of_the_run(self):
        sent = all_of(W().name_filter(), cond("status", "in", ["Sent"]))
        self.assertEqual(self.ids("i2", "i4"), self.drill([], filters=sent))
        quick = [{"field": "contact", "mode": "in", "values": [], "includeEmpty": True}]
        self.assertEqual(self.ids("i6", "i7"), self.drill(["Created"], quickFilters=quick))

    def test_period_group_of_a_date(self):
        report = W().report("dir", "drill month", type="summaries", entityType="Invoice",
                            groups=[{"field": "dateInvoiced", "granularity": "month"}],
                            aggregates=[{"function": "COUNT"}], filters=all_of(W().name_filter()))
        status, ids = drill_down(W().client("dir"), "Invoice", report["id"], [period_key(R()["m1"], "month")])
        self.assertEqual((200, self.ids("i3", "i4", "i6")), (status, ids))

    def test_bad_drill_down_requests(self):
        dir_ = W().client("dir")
        self.assertEqual(400, drill_down(dir_, "Invoice", self.report["id"], ["Created", "x", "y"])[0])
        self.assertEqual(400, drill_down(dir_, "Account", self.report["id"], [])[0])
        self.assertEqual(404, drill_down(dir_, "Invoice", "no-such-report", [])[0])


def snapshot():
    """Every column of the rows of this run (reports, invoices, their lines, accounts, contacts, products) and the
    report tables as a whole. Other suites may write invoices of their own on the stand meanwhile, so whole-table
    checksums of the shared tables would not tell their writes from a write of a run."""
    tag, ids = W().tag, "', '".join(s["id"] for s in R()["invoices"].values())
    return {
        "report tables": sql("CHECKSUM TABLE report, report_folder, report_folder_path, report_shared_user, "
                             "report_shared_team"),
        "report": sql(f"SELECT * FROM report WHERE name LIKE '{tag}%' ORDER BY id"),
        "invoice": sql(f"SELECT * FROM invoice WHERE name LIKE '{tag}%' ORDER BY id"),
        "invoice_item": sql(f"SELECT * FROM invoice_item WHERE invoice_id IN ('{ids}') ORDER BY id"),
        "account": sql(f"SELECT * FROM account WHERE name LIKE '{tag}%' ORDER BY id"),
        "contact": sql(f"SELECT * FROM contact WHERE last_name LIKE '{tag}%' ORDER BY id"),
        "product": sql(f"SELECT * FROM product WHERE name LIKE '{tag}%' ORDER BY id"),
    }


class NoWritesTest(Case):
    def test_a_run_writes_nothing(self):
        ref, w = R(), W()
        tabular = w.report("dir", "nowrite tab", entityType="Invoice", columns=["name", "account", "grandTotal"],
                           totals=[{"column": "grandTotal", "functions": ["SUM"]}],
                           calculations=[{"label": "x", "expression": "{grandTotal} * 2", "functions": ["SUM"]}],
                           filters=all_of(w.name_filter()), quickFilters=["status"])
        grouped = w.report("dir", "nowrite sum", type="summariesWithDetails", entityType="Invoice",
                           groups=[{"field": "account"}], aggregates=[{"function": "COUNT"}], columns=["name"],
                           filters=all_of(w.name_filter()))
        matrix = w.report("dir", "nowrite matrix", type="matrix", entityType="InvoiceItem",
                          groups=[{"field": "product"}, {"field": "invoice.dateInvoiced", "granularity": "month"}],
                          aggregates=[{"function": "COUNT"}],
                          filters=all_of(cond("product", "in", [ref["p1"]], attribute="productId")))
        before = snapshot()
        self.assertEqual((7, 10), (len(before["invoice"]), len(before["invoice_item"])))
        for report in (tabular, grouped, matrix):
            for _ in range(2):
                self.run_ok(report["id"])
                self.run_ok(report["id"], "admin", noLimit=True)
        self.run_ok(tabular["id"], quickFilters=[{"field": "status", "mode": "in", "values": ["Sent"]}])
        drill_down(w.client("dir"), "Invoice", grouped["id"], [ref["a1"]])
        run(w.client("dir2"), tabular["id"])  # a refused run (private report of another user) writes nothing either
        after = snapshot()
        for part in before:
            self.assertEqual(before[part], after[part], part)


if __name__ == "__main__":
    unittest.main()
