"""Stage 08 tests without the stand (docs/migration/rehearsal.md): what the full rehearsal found and added.

- the first imported file of a fresh installation (no data/upload yet) — tests/stage08/blob_receiver_fresh.php; the
  stand fingerprint of a storage not created yet;
- the summary of a run: every finance measure on its own (equal or not, a value only for counting measures — the
  amounts stay private) and the per-column tables of import-columns.md (one row per column, counts only), on a
  synthetic report.
"""
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
        self.assertNotIn("## Каждая непустая колонка снимка", text)


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
