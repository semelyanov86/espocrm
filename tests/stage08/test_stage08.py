"""Stage 08 tests without the stand (docs/migration/rehearsal.md): what the full rehearsal found and added.

- the first imported file of a fresh installation (no data/upload yet) — tests/stage08/blob_receiver_fresh.php; the
  stand fingerprint of a storage not created yet;
- the summary of a run: every finance measure on its own (equal or not, a value only for counting measures — the
  amounts stay private) and the per-column tables of import-columns.md (one row per column, counts only), on a
  synthetic report.
"""
import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "import"))
sys.path.insert(0, str(REPO / "scripts" / "snapshot"))
sys.path.insert(0, str(REPO / "scripts" / "stand"))
import fingerprint  # noqa: E402
import importer  # noqa: E402

AMOUNT = "987654.32"  # synthetic amount: must never reach the summary


def synthetic_report():
    rule = {"category": "rule", "column": "vtiger_account.accountname", "exempt": 0, "fate": "перенос",
            "meaningful": 3, "mismatch": 0, "module": "Accounts", "nonempty": 3, "outcomes": {"carried": 3},
            "unaccounted": 0, "verified": 3}
    return {
        "aggregates": {"excluded": {}, "reader": {"measures": 3, "unequal": 1}, "writer": {"measures": 3, "unequal": 0}},
        "columns": [rule,
                    {"category": "excluded", "column": "vtiger_account.notify_owner", "fate": "исключено: флаг",
                     "meaningful": 0, "module": "Accounts", "nonempty": 3},
                    {"category": "rule", "column": "cdr.billsec", "exempt": 0, "fate": "перенос: Call.cBillDuration",
                     "meaningful": 2, "mismatch": 0, "module": "CDR", "nonempty": 2, "outcomes": {"carried": 2},
                     "unaccounted": 0, "verified": 2},
                    {"category": "relation", "column": "vtiger_crmentityrel.crmid", "fate": "", "meaningful": 4,
                     "module": "links", "nonempty": 4}],
        "entities": {"Account": {"source": 3, "apply:created": 3, "check:equal": 3}},
        "files": {}, "finance": {"formula": {"noLineTax": 1}}, "findings": [], "flags": {}, "inventory": {},
        "ledger": {"columns": 2, "status": "pass"}, "link_tables": {}, "problems": [], "relations": [],
        "silence": {}, "snapshot": "20000101T000000", "status": "pass", "telephony": {},
        "tool": {"git_head": "0" * 40, "dirty_tool_files": 0},
    }


def synthetic_aggregates():
    return {"excluded": {},
            "reader": [{"measure": "Invoice.count", "equal": True, "left": "3", "right": "3"},
                       {"measure": "Invoice.grandTotal", "equal": False, "left": AMOUNT, "right": "1"},
                       {"measure": "Invoice.taxMode.group.count", "equal": True, "left": "2", "right": "2"}],
            "writer": [{"measure": "Invoice.count", "equal": True, "left": "3", "right": "3"},
                       {"measure": "Invoice.grandTotal", "equal": True, "left": AMOUNT, "right": AMOUNT},
                       {"measure": "Invoice.taxMode.group.count", "equal": True, "left": "2", "right": "2"}]}


class FreshInstallation(unittest.TestCase):
    @unittest.skipUnless((REPO / "vendor" / "autoload.php").is_file(),
                         "the EspoCRM core is not unpacked here (task stand:install): no core FileManager")
    def test_first_file_creates_the_upload_directory(self):
        run = subprocess.run(["php", str(REPO / "tests/stage08/blob_receiver_fresh.php")], capture_output=True,
                             text=True, timeout=60)
        self.assertEqual("ok", run.stdout.strip(), run.stderr[-500:])
        self.assertEqual(0, run.returncode)


    def test_fingerprint_of_a_storage_not_created_yet(self):
        """task stand:fingerprint on a fresh installation: no data/upload yet is an empty storage, not a failure."""
        missing = Path(tempfile.mkdtemp(prefix="itvolga-stage08-")) / "upload"
        saved, fingerprint.UPLOAD = fingerprint.UPLOAD, missing
        try:
            self.assertEqual({}, fingerprint.uploads())
        finally:
            fingerprint.UPLOAD = saved
            missing.parent.rmdir()

    def test_fingerprint_refuses_a_storage_path_of_another_kind(self):
        """A file or a dangling link where data/upload should be is a broken storage, never an empty one."""
        work = Path(tempfile.mkdtemp(prefix="itvolga-stage08-"))
        saved = fingerprint.UPLOAD
        try:
            (work / "file").write_text("not a directory", encoding="utf-8")
            (work / "link").symlink_to(work / "absent")
            for path in (work / "file", work / "link"):
                fingerprint.UPLOAD = path
                with self.assertRaises(fingerprint.SnapshotError, msg=path.name):
                    fingerprint.uploads()
        finally:
            fingerprint.UPLOAD = saved
            for child in work.iterdir():
                child.unlink()
            work.rmdir()


class Summary(unittest.TestCase):
    def test_measures_one_by_one_without_amounts(self):
        text = importer.render_summary(synthetic_report(), "20000101T000000", synthetic_aggregates())
        rows = {line.split("|")[1].strip(): [c.strip() for c in line.split("|")[2:-1]]
                for line in text.splitlines() if line.startswith("| `Invoice.")}
        self.assertEqual(["счётчик", "=", "=", "3"], rows["`Invoice.count`"])
        self.assertEqual(["деньги", "**≠**", "=", ""], rows["`Invoice.grandTotal`"])
        self.assertEqual(["налог, счётчик", "=", "=", "2"], rows["`Invoice.taxMode.group.count`"])
        self.assertNotIn(AMOUNT, text)
        self.assertIn("## Каждая колонка (этап 08)", text)

    def test_summary_without_aggregates_file(self):
        text = importer.render_summary(synthetic_report(), "20000101T000000")
        self.assertNotIn("### Меры по одной", text)
        self.assertIn("Меры по одной: нет — в прогоне нет `aggregates.json`", text)

    def test_column_tables_one_row_per_column(self):
        ledger_rows = [
            {"cls": "excluded", "column": "gscrmid", "fates": ["excluded"], "nonempty": 5, "nonzero": 5,
             "schema": "vtiger7", "table": "berli_globalsearch_data"},
            {"categories": {"rule": 1}, "cls": "import", "column": "billsec", "deleted": 0, "live": 4, "mismatch": 0,
             "nonempty": 4, "nonzero": None, "outside_fates": ["исключено | причина"], "outside_scope": 0,
             "schema": "asteriskcdrdb", "table": "cdr", "unaccounted": 0, "verified": 3}]
        text = importer.render_column_tables(synthetic_report(), "20000101T000000",
                                             REPO / "docs" / "migration" / "field-map.csv", ledger_rows)
        parts = text.split("## Каждая непустая колонка снимка")
        self.assertEqual(2, len(parts))
        read, snapshot = (table_rows(part) for part in parts)
        self.assertEqual(4, len(read))
        by = {(r[0], r[2]): r for r in read}
        self.assertEqual(["Accounts", "vtiger7", "`vtiger_account.accountname`", "rule", "перенос", "Account.name",
                          "3", "3", "0", "0", "carried=3"], by[("Accounts", "`vtiger_account.accountname`")])
        self.assertEqual(["excluded", "", "", "", ""], by[("Accounts", "`vtiger_account.notify_owner`")][3:4] +
                         by[("Accounts", "`vtiger_account.notify_owner`")][7:])
        self.assertEqual("asteriskcdrdb", by[("CDR", "`cdr.billsec`")][1])
        self.assertIn(("links", "`vtiger_crmentityrel.crmid`"), by)
        self.assertEqual(2, len(snapshot))
        self.assertEqual(["`asteriskcdrdb.cdr.billsec`", "import", "4", "", "4", "3", "0", "0", "0", "0",
                          "rule=1, вне границ: исключено \\| причина"], snapshot[0])
        self.assertEqual(["`vtiger7.berli_globalsearch_data.gscrmid`", "excluded", "5", "5", "", "", "", "", "", "",
                          "excluded"], snapshot[1])

    def test_column_tables_without_ledger(self):
        text = importer.render_column_tables(synthetic_report(), "20000101T000000",
                                             REPO / "docs" / "migration" / "field-map.csv")
        self.assertIn("Нет: полная сверка колонок снимка в прогоне не выполнялась", text)
        self.assertNotIn("—.—", text)  # the map's placeholder target of an excluded column is no target


class DetailFiles(unittest.TestCase):
    """The per-measure and per-column tables must prove the totals of report.json (external review of stage 08, B1)."""

    def setUp(self):
        self.report = synthetic_report()
        self.report["ledger"] = {"columns": 2, "values": 9, "status": "pass"}
        self.aggregates = synthetic_aggregates()
        self.ledger = [{"cls": "excluded", "column": "a", "fates": [], "nonempty": 5, "schema": "vtiger7", "table": "t"},
                       {"cls": "excluded", "column": "b", "fates": [], "nonempty": 4, "schema": "vtiger7", "table": "t"}]

    def test_complete_files(self):
        self.assertEqual([], importer.detail_gaps(self.report, self.aggregates, self.ledger))

    def test_missing_short_duplicated_or_disagreeing_files(self):
        short = {**self.aggregates, "writer": self.aggregates["writer"][:2]}
        twice = {**self.aggregates, "writer": self.aggregates["writer"][:2] + self.aggregates["writer"][:1]}
        unequal = {**self.aggregates, "reader": [{**m, "equal": True} for m in self.aggregates["reader"]]}
        for aggregates, ledger, gap in (
                (None, self.ledger, "aggregates.json:reader missing"),
                (short, self.ledger, "aggregates.json:writer differs"),
                (twice, self.ledger, "aggregates.json:writer differs"),
                (unequal, self.ledger, "aggregates.json:reader differs"),
                (self.aggregates, None, "ledger.jsonl missing"),
                (self.aggregates, self.ledger[:1], "ledger.jsonl differs"),
                (self.aggregates, [self.ledger[0], self.ledger[0]], "ledger.jsonl differs"),
                (self.aggregates, [self.ledger[0], {**self.ledger[1], "nonempty": 3}], "ledger.jsonl differs")):
            self.assertIn(gap, importer.detail_gaps(self.report, aggregates, ledger))

    def test_run_without_the_sections_needs_no_files(self):
        report = {**self.report, "aggregates": {}, "ledger": {}}
        self.assertEqual([], importer.detail_gaps(report, None, None))

    def test_summary_is_not_written_when_files_disagree(self):
        root = Path(tempfile.mkdtemp(prefix="itvolga-stage08-"))
        run, out = root / "20000101T000000", root / "out"
        run.mkdir()
        out.mkdir()
        (run / "report.json").write_text(json.dumps(self.report), encoding="utf-8")
        (run / "aggregates.json").write_text(json.dumps(self.aggregates), encoding="utf-8")
        (run / "ledger.jsonl").write_text(json.dumps(self.ledger[0]) + "\n", encoding="utf-8")
        saved, importer.IMPORT_ROOT = importer.IMPORT_ROOT, root
        try:
            args = argparse.Namespace(run=run.name, out=str(out / "summary.md"), columns_out=str(out / "columns.md"))
            with self.assertRaises(importer.SnapshotError):
                importer.cmd_summary(args)
            self.assertEqual([], list(out.iterdir()))
        finally:
            importer.IMPORT_ROOT = saved
            for path in (*run.iterdir(), run, out, root):
                path.rmdir() if path.is_dir() else path.unlink()


def table_rows(text):
    """Data rows of the Markdown tables of a text (header and separator rows dropped); `\\|` stays in its cell."""
    rows = []
    for line in text.splitlines():
        if line.startswith("| ") and not line.startswith(("| Модуль |", "| Колонка |")):
            cells = [c.strip() for c in line.replace("\\|", "\0").strip("|").split("|")]
            rows.append([c.replace("\0", "\\|") for c in cells])
    return rows


if __name__ == "__main__":
    unittest.main()
