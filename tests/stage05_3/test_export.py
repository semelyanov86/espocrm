"""Stage 05.3 acceptance tests: export of a report result to CSV, XLSX and PDF and the print view (D-116…D-120).

Files hold the numbers of the result to the kopeck (decimal strings in CSV, exact numeric cells in XLSX), the variant
«report data» keeps the limits of the report and says so, «all» lifts them; one-off conditions and quick filters of
the shown result reach the file; CSV has a byte order mark and the user's delimiter, protects texts against formulas
and has the currency column; XLSX has no formulas, a bold frozen header and typed cells; a PDF of a matrix is landscape
and holds the table as on the screen. Export and print need the export permission and read access to the report; the
file is downloaded only by the one who made it; a run of the API keeps its page of at most 200 rows.
"""
import unittest
import uuid

from output import (BY_STATUS, EXPORT_FORMATS, MIME, SUM_ALL, D, Letters, World, all_of, cond, csv_rows, dec,
                    download, export, export_file, label, ok, pdf_size, pdf_text, reference_data, run, sql,
                    xlsx_rows)

S = {}
NO_EXPORT = {"Invoice": {"create": "no", "read": "all", "edit": "no", "delete": "no"},
             "Account": {"read": "all"}, "InvoiceItem": {"read": "all"}}
BULK = 205


def setUpModule():
    world = World()
    letters = Letters(world)
    # Cleanups run in reverse: letters and files, then the world, then its notifications.
    unittest.addModuleCleanup(letters.purge_notifications)
    unittest.addModuleCleanup(world.cleanup)
    unittest.addModuleCleanup(letters.purge)
    S["w"] = world
    S["letters"] = letters
    world.user("dir", roles=["Директор"])
    world.user("dir2", roles=["Директор"])
    no_export = world.role("no export", NO_EXPORT)
    sql(f"UPDATE role SET export_permission = 'no' WHERE id = '{no_export}'")
    world.user("noexp", role_ids=[no_export])
    # Exports and reads reports, but not their names (field level).
    nameless = world.role("nameless", NO_EXPORT, field_data={"Report": {"name": {"read": "no", "edit": "no"}}})
    sql(f"UPDATE role SET export_permission = 'yes' WHERE id = '{nameless}'")
    world.user("nameless", role_ids=[nameless])
    S["ref"] = reference_data(world)
    tag = world.tag
    S["tabular"] = world.report("dir", "Счета итоги", type="tabular", entityType="Invoice",
                                columns=["name", "account", "status", "grandTotal", "dateInvoiced", "createdAt"],
                                sorting=[{"column": "name", "direction": "asc"}], rowLimit=3, accessType="public",
                                filters=all_of(world.name_filter()), quickFilters=["status"],
                                totals=[{"column": "grandTotal", "functions": ["SUM", "MAX"]}],
                                labels={"c:status": "=SUM(A1)"})
    S["summaries"] = world.report("dir", "по статусам", type="summaries", entityType="Invoice",
                                  groups=[{"field": "status"}], accessType="public",
                                  aggregates=[{"function": "COUNT"}, {"function": "SUM", "field": "grandTotal"}],
                                  filters=all_of(world.name_filter()))
    S["details"] = world.report("dir", "детализация", type="summariesWithDetails", entityType="Invoice",
                                groups=[{"field": "status"}], columns=["name", "grandTotal"], accessType="public",
                                aggregates=[{"function": "SUM", "field": "grandTotal"}],
                                filters=all_of(world.name_filter()))
    S["matrix"] = world.report("dir", "матрица", type="matrix", entityType="Invoice", accessType="public",
                               groups=[{"field": "status"}, {"field": "dateInvoiced", "granularity": "month"}],
                               aggregates=[{"function": "SUM", "field": "grandTotal"}],
                               filters=all_of(world.name_filter()))
    S["private"] = world.report("dir", "личный", type="tabular", entityType="Invoice", columns=["name"],
                                filters=all_of(world.name_filter()))
    # Many rows: synthetic accounts written straight to the stand database (removed by the cleanup below).
    S["bulk"] = [uuid.uuid4().hex[:17] for _ in range(BULK)]
    values = ",".join(f"('{i}', '{tag} bulk {n:03d}', 0, NOW())" for n, i in enumerate(S["bulk"]))
    sql(f"INSERT INTO account (id, name, deleted, created_at) VALUES {values}")
    unittest.addModuleCleanup(lambda: sql("DELETE FROM account WHERE id IN ('" + "','".join(S["bulk"]) + "')"))
    S["accounts"] = world.report("admin", "контрагенты", type="tabular", entityType="Account", columns=["name"],
                                 rowLimit=None, filters=all_of(cond("name", "startsWith", f"{tag} bulk")))


def W():
    return S["w"]


class Case(unittest.TestCase):
    def refused(self, result, status, key=None):
        self.assertEqual(status, result[0], f"expected HTTP {status}, got {result[0]}: {result[1]}")
        if key:
            self.assertEqual(key, label(result))


class CsvTest(Case):
    def test_tabular_csv(self):
        dir_ = W().client("dir")
        payload, data, headers = export_file(dir_, S["tabular"]["id"], "csv")
        self.assertEqual("text/csv", payload["type"])
        self.assertTrue(payload["name"].endswith(".csv") and "Счета" in payload["name"], payload["name"])
        self.assertTrue(headers.get("Content-Type", "").startswith("text/csv"))
        rows = csv_rows(data)
        # Header: labels (a label like a formula is protected), a currency column after the money.
        self.assertEqual(["Название", "Контрагент", "'=SUM(A1)", "Итого", "Валюта", "Дата счёта", "Создано"], rows[0])
        invoices = S["ref"]["invoices"]
        expected = sorted(invoices, key=lambda k: f"{W().tag} {k}")[:3]
        body = rows[1:4]
        self.assertEqual([f"{W().tag} {k}" for k in expected], [r[0] for r in body])
        self.assertEqual([invoices[k]["total"] for k in expected], [dec(r[3]) for r in body])
        self.assertEqual(["RUB"] * 3, [r[4] for r in body])
        self.assertEqual([invoices[k]["date"].isoformat() for k in expected], [r[5] for r in body])
        self.assertRegex(body[0][6], r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")
        # The totals over all records of the conditions (D-96), not the three rows, after a blank row.
        self.assertEqual([], rows[4])
        self.assertIn(["Колонка", "Функция", "Значение", "Валюта"], rows)
        self.assertIn(["Итого", "Сумма", str(SUM_ALL), "RUB"], [[r[0], r[1], str(dec(r[2])), r[3]] for r in rows
                                                               if len(r) == 4 and r[1] == "Сумма"])
        # The variant «report data» says the row limit cut it.
        self.assertEqual([], rows[-2])
        self.assertEqual(1, len(rows[-1]))
        self.assertIn("3", rows[-1][0])

    def test_variant_all_and_one_off_conditions(self):
        dir_ = W().client("dir")
        rows = csv_rows(export_file(dir_, S["tabular"]["id"], "csv", variant="all")[1])
        self.assertEqual(7, len([r for r in rows[1:] if r and r[0].startswith(W().tag)]))

        quick = [{"field": "status", "mode": "in", "values": ["Sent"], "includeEmpty": False}]
        rows = csv_rows(export_file(dir_, S["tabular"]["id"], "csv", variant="all", quickFilters=quick)[1])
        self.assertEqual({"Отправлен"} if rows[1][2] == "Отправлен" else {rows[1][2]},
                         {r[2] for r in rows[1:] if r and r[0].startswith(W().tag)})
        self.assertEqual(2, len([r for r in rows[1:] if r and r[0].startswith(W().tag)]))

        filters = all_of(W().name_filter(), cond("status", "in", ["Approved"]))
        rows = csv_rows(export_file(dir_, S["tabular"]["id"], "csv", filters=filters)[1])
        self.assertEqual([f"{W().tag} i5"], [r[0] for r in rows[1:] if r and r[0].startswith(W().tag)])

    def test_user_delimiter_and_summaries(self):
        dir2 = W().client("dir2")
        ok(W().admin.put(f"Preferences/{W().uid['dir2']}", {"exportDelimiter": ";"}), "preferences")
        rows = csv_rows(export_file(dir2, S["summaries"]["id"], "csv")[1], delimiter=";")
        self.assertEqual(["Статус", "Число записей", "Сумма: Итого", "Валюта"], rows[0])
        got = {r[0]: (int(r[1]), dec(r[2]), r[3]) for r in rows[1:-1]}
        expected = {k: (n, s, "RUB") for k, (n, s) in BY_STATUS.items()}
        self.assertEqual(sorted(expected.values()), sorted(got.values()))
        self.assertEqual(["Итого", "7", str(SUM_ALL)], [rows[-1][0], rows[-1][1], str(dec(rows[-1][2]))])

    def test_details_and_matrix_are_flat(self):
        dir_ = W().client("dir")
        rows = csv_rows(export_file(dir_, S["details"]["id"], "csv")[1])
        self.assertEqual(["Статус", "Сумма: Итого", "Валюта", "Название", "Итого", "Валюта"], rows[0])
        records = [r for r in rows[1:] if r[3]]
        self.assertEqual(7, len(records))
        self.assertEqual(SUM_ALL, sum(dec(r[4]) for r in records))
        self.assertTrue(all(r[1] == "" for r in records), "a record row has no aggregates")
        self.assertEqual(str(SUM_ALL), str(dec(rows[-1][1])))

        rows = csv_rows(export_file(dir_, S["matrix"]["id"], "csv")[1])
        width = len(rows[0])
        self.assertTrue(all(len(r) == width for r in rows), "every row has the width of the header")
        self.assertEqual("Итого", rows[-1][0])
        self.assertEqual(str(SUM_ALL), str(dec(rows[-1][-2])))
        self.assertEqual("RUB", rows[-1][-1])


class XlsxPdfTest(Case):
    def test_xlsx(self):
        payload, data, _ = export_file(W().client("dir"), S["tabular"]["id"], "xlsx", variant="all")
        self.assertEqual(MIME["xlsx"], payload["type"])
        rows, sheet = xlsx_rows(data)
        self.assertNotIn("formula", {cell[0] for row in rows for cell in row})
        self.assertEqual("=SUM(A1)", rows[0][2][1], "a text stays a text, never a formula")
        pane = sheet.find(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}pane")
        self.assertEqual("frozen", pane.get("state"))
        records = [r for r in rows[1:] if r and str(r[0][1]).startswith(W().tag)]
        self.assertEqual(7, len(records))
        self.assertEqual({"n"}, {r[3][0] for r in records}, "amounts are numeric cells")
        self.assertEqual(SUM_ALL, sum(D(r[3][1]) for r in records))
        self.assertEqual({"n"}, {r[5][0] for r in records}, "dates are date cells")

    def test_pdf(self):
        dir_ = W().client("dir")
        payload, data, headers = export_file(dir_, S["matrix"]["id"], "pdf")
        self.assertEqual(MIME["pdf"], payload["type"])
        self.assertTrue(data.startswith(b"%PDF"))
        width, height = pdf_size(data)
        self.assertGreater(width, height, "a matrix is landscape")
        text = pdf_text(data)
        self.assertIn("матрица", text)
        self.assertIn("Всего записей: 7", text)
        self.assertIn("Итого", text)
        self.assertIn("34 477,39", text.replace(" ", " "))

        _, data, _ = export_file(dir_, S["details"]["id"], "pdf")
        width, height = pdf_size(data)
        self.assertLess(width, height, "a narrow table is portrait")
        text = pdf_text(data)
        self.assertIn("Статус =", text)

    def test_every_type_and_format(self):
        dir_ = W().client("dir")
        for key in ("tabular", "summaries", "details", "matrix"):
            for fmt in EXPORT_FORMATS:
                with self.subTest(report=key, format=fmt):
                    payload, data, headers = export_file(dir_, S[key]["id"], fmt)
                    self.assertEqual(MIME[fmt], payload["type"])
                    self.assertGreater(len(data), 100)


class ManyRowsTest(Case):
    def test_file_has_all_rows_the_api_a_page(self):
        result = ok(run(W().admin, S["accounts"]["id"], maxSize=200))
        self.assertEqual(200, len(result["rows"]))
        self.assertEqual(BULK, result["availableRows"])
        self.refused(run(W().admin, S["accounts"]["id"], maxSize=201), 400)
        rows = csv_rows(export_file(W().admin, S["accounts"]["id"], "csv", track=S["letters"].extra_attachments)[1])
        self.assertEqual(BULK, len([r for r in rows[1:] if r and r[0].startswith(W().tag)]))


class AccessTest(Case):
    def test_export_needs_the_permission(self):
        noexp = W().client("noexp")
        self.assertEqual(200, run(noexp, S["tabular"]["id"])[0], "the report itself is readable")
        self.refused(export(noexp, S["tabular"]["id"], "csv"), 403, "exportForbidden")
        self.refused(noexp.request("POST", f"Report/{S['tabular']['id']}/printView", {}), 403, "exportForbidden")
        self.refused(export(noexp, S["tabular"]["id"], "csv", background=True), 403, "exportForbidden")

    def test_a_closed_report_name_is_not_exported(self):
        """The name goes into the file name, the print title and a background letter: closed to the user at the
        field level — no export or print (external review 05.3 B6)."""
        nameless = W().client("nameless")
        self.assertEqual(200, run(nameless, S["tabular"]["id"])[0], "the report itself is readable")
        self.refused(export(nameless, S["tabular"]["id"], "csv"), 403, "exportForbidden")
        self.refused(nameless.request("POST", f"Report/{S['tabular']['id']}/printView", {}), 403, "exportForbidden")
        self.refused(export(nameless, S["tabular"]["id"], "csv", background=True), 403, "exportForbidden")

    def test_report_access_and_bad_requests(self):
        dir2 = W().client("dir2")
        self.refused(export(dir2, S["private"]["id"], "csv"), 403)
        self.refused(dir2.request("POST", f"Report/{S['private']['id']}/printView", {}), 403)
        self.refused(export(dir2, "nonexistent", "csv"), 404)
        self.refused(export(dir2, S["tabular"]["id"], "xml"), 400, "badExportFormat")
        self.refused(export(dir2, S["tabular"]["id"], "csv", variant="everything"), 400, "badExportVariant")
        self.refused(export(dir2, S["tabular"]["id"], "csv", quickFilters=[{"field": "name", "values": []}]), 400)

    def test_only_the_maker_downloads(self):
        payload = ok(export(W().client("dir"), S["tabular"]["id"], "csv"))
        self.assertEqual(200, download(W().client("dir"), payload["id"])[0])
        self.assertEqual(403, download(W().client("dir2"), payload["id"])[0])
        row = sql(f"SELECT role, created_by_id, parent_id FROM attachment WHERE id = '{payload['id']}'")[0]
        self.assertEqual(["Export File", W().uid["dir"], "NULL"], row)


class PrintTest(Case):
    def test_print_view(self):
        view = ok(W().client("dir").request("POST", f"Report/{S['summaries']['id']}/printView", {}))
        html = view["html"]
        self.assertEqual("Portrait", view["orientation"])
        self.assertTrue(html.startswith("<!DOCTYPE html>"))
        self.assertIn('<table class="report">', html)
        self.assertNotIn("<script", html.lower())
        self.assertNotIn("data-action", html)
        self.assertIn("Итого (7)", html)
        self.assertIn(W().tag, view["title"])
        matrix = ok(W().client("dir").request("POST", f"Report/{S['matrix']['id']}/printView", {}))
        self.assertEqual("Landscape", matrix["orientation"])
        self.assertIn("size: A4 landscape", matrix["html"])

    def test_print_writes_nothing(self):
        before = sql("SELECT COUNT(*) FROM attachment")[0][0]
        ok(W().client("dir").request("POST", f"Report/{S['tabular']['id']}/printView", {"variant": "all"}))
        self.assertEqual(before, sql("SELECT COUNT(*) FROM attachment")[0][0])


if __name__ == "__main__":
    unittest.main()
