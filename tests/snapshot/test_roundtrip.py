"""Snapshot codec round trip on the stand MySQL (stage 06.1): a synthetic source database with edge
values → capture (same code as for production, local client) → seal → verify (restore into a
temporary database, same count/digest SQL) → negative controls. No production access.

    task test:snapshot
"""
import contextlib
import gzip
import io
import secrets
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "snapshot"))
import capture  # noqa: E402
import codec  # noqa: E402
import snapshot  # noqa: E402
import verify  # noqa: E402
from common import Mysql, write_json  # noqa: E402

SOURCE = f"vtsnap_selftest_{secrets.token_hex(3)}"
FIXTURE = f"""
SET SESSION sql_log_bin=0;
SET SESSION sql_mode='ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION,NO_AUTO_VALUE_ON_ZERO';
CREATE DATABASE `{SOURCE}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE `{SOURCE}`;
CREATE TABLE t_str (id INT NOT NULL AUTO_INCREMENT PRIMARY KEY, a VARCHAR(50) CHARACTER SET latin1, b TEXT CHARACTER SET utf8mb3,
  c LONGTEXT CHARACTER SET utf8mb4, d CHAR(5) CHARACTER SET utf8mb3 NOT NULL DEFAULT '') ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;
INSERT INTO t_str (id, a, b, c, d) VALUES (0, NULL, 'NULL', '', 'x'),
  (1, CONVERT(X'808182839D9E9FE9' USING latin1), CONCAT('tab', CHAR(9), 'nl', CHAR(10), 'bs', CHAR(92), 'q', CHAR(39), '"'),
   _utf8mb4 X'F09F9880', 'ab  '),
  (2, '', NULL, NULL, '');
CREATE TABLE t_num (id BIGINT UNSIGNED NOT NULL PRIMARY KEY, d DECIMAL(25,8), s SMALLINT, t TINYINT(1), m MEDIUMINT) ENGINE=InnoDB;
INSERT INTO t_num VALUES (~0, -12.50000000, -32768, 1, NULL), (0, 0.00000001, 0, 0, 0);
CREATE TABLE t_time (id INT PRIMARY KEY, d DATE, dt DATETIME, dt6 DATETIME(6), ts TIMESTAMP NULL DEFAULT NULL, tm TIME) ENGINE=InnoDB;
INSERT INTO t_time VALUES (1, '0000-00-00', '0000-00-00 00:00:00', '2026-03-29 02:30:00.123456', '2026-03-29 03:30:00',
  '-838:59:59'), (2, NULL, NULL, NULL, NULL, NULL);
CREATE TABLE t_bin (id INT PRIMARY KEY, bl LONGBLOB, vb VARBINARY(10), bn BINARY(4)) ENGINE=InnoDB;
INSERT INTO t_bin VALUES (1, X'000102FF0A095C', X'', X'01'), (2, NULL, NULL, NULL);
CREATE TABLE t_nopk (a VARCHAR(10), b INT) ENGINE=InnoDB;
INSERT INTO t_nopk VALUES ('x', 1), ('x', 1), ('a', NULL), ('A', NULL);
CREATE TABLE t_my (id INT, v VARCHAR(10)) ENGINE=MyISAM;
INSERT INTO t_my VALUES (1, 'm');
CREATE TABLE t_empty (id INT PRIMARY KEY, v TEXT) ENGINE=InnoDB;
CREATE TABLE t_ai (id INT NOT NULL AUTO_INCREMENT, v INT, PRIMARY KEY (id), KEY k_v (v)) ENGINE=InnoDB AUTO_INCREMENT=100;
INSERT INTO t_ai VALUES (0, 5), (7, NULL);
"""
EXPECTED_ROWS = {"t_str": 3, "t_num": 2, "t_time": 2, "t_bin": 2, "t_nopk": 4, "t_my": 1, "t_empty": 0, "t_ai": 2}


def stand_sql(sql):
    return Mysql.stand().lines(sql, ROOT / "test.log")


class RoundTrip(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global ROOT
        ROOT = Path(tempfile.mkdtemp(prefix="vtsnap-test-"))
        cls.addClassCleanup(shutil.rmtree, ROOT, True)
        cls.addClassCleanup(stand_sql, f"SET SESSION sql_log_bin=0;\nDROP DATABASE IF EXISTS `{SOURCE}`;\n")
        stand_sql(FIXTURE)
        cls.snap = ROOT / "snap"
        planned = capture.plan(Mysql.stand(), [SOURCE], cls.snap / "logs")
        db = capture.capture_db(Mysql.stand(), planned, cls.snap)
        write_json(cls.snap / "MANIFEST.json", snapshot.build_manifest("selftest", planned, db, {}))
        verify.write_seal(cls.snap)

    def run_verify(self, name):
        report = verify.verify(self.snap, ROOT, completeness=False, report_dir=ROOT / name)
        return report, {c["id"].split(".")[0]: c["status"] for c in report["checks"]}

    def test_1_round_trip(self):
        tables = verify.read_json(self.snap / "db" / SOURCE / "tables.json")
        self.assertEqual({t: m["rows"] for t, m in tables.items()}, EXPECTED_ROWS)
        self.assertEqual(tables["t_my"]["consistency"], "stable-window")
        report, st = self.run_verify("verify-ok")
        self.assertEqual(report["status"], "pass", report["checks"])
        self.assertEqual(st, {"V0": "pass", "V1": "pass", "V3": "pass", "V4": "pass", "V5": "pass"})
        self.assertEqual(verify.journal_leftovers(ROOT, ROOT / "test.log"), [])

    def test_2_tampered_byte_breaks_the_seal(self):
        path = self.snap / "db" / SOURCE / "ddl" / "t_num.sql"
        original = path.read_bytes()
        try:
            path.write_bytes(original.replace(b"DECIMAL", b"decimal").replace(b"decimal(25,8)", b"decimal(25,7)"))
            report, st = self.run_verify("verify-seal")
            self.assertEqual((st["V1"], st["V4"]), ("fail", "fail"))
            self.assertEqual(report["tempdbs"]["created"], 0)       # nothing of a broken seal runs as root
        finally:
            path.write_bytes(original)

    def test_3_changed_value_is_caught_by_digests(self):
        path = self.snap / "db" / SOURCE / "rows" / "t_num.hex.gz"
        original = path.read_bytes()
        try:
            lines = gzip.decompress(original).split(b"\n")[:-1]
            lines[0] = lines[0].replace(b"\t30", b"\t31", 1)   # -12.5 → -12.5 with another digit: still valid
            self.assertNotEqual(gzip.decompress(original).split(b"\n")[0], lines[0])
            path.unlink()
            capture.write_rows(path, sorted(lines))
            verify.write_seal(self.snap)                        # an attacker-free reseal: only digests remain
            _report, st = self.run_verify("verify-digest")
            self.assertEqual((st["V1"], st["V3"], st["V4"]), ("pass", "fail", "fail"))
        finally:
            path.unlink()
            path.write_bytes(original)
            verify.write_seal(self.snap)

    # --- capture side: a changed source is refused, nothing is published ---------------------------

    def capture_with(self, alter_line=None, alter_plan=None):
        planned = capture.plan(Mysql.stand(), [SOURCE], ROOT / "nc" / "logs")
        if alter_plan:
            alter_plan(planned)
        client = Mysql.stand()
        session = client.session

        def tampered(script, consume, errlog):
            return session(script, lambda line: alter_line(line, consume) if alter_line else consume(line), errlog)

        client.session = tampered
        staging = ROOT / f"nc-{secrets.token_hex(3)}"
        with self.assertRaises(capture.SnapshotError) as ctx:
            capture.capture_db(client, planned, staging)
        return str(ctx.exception)

    def test_4_schema_change_is_refused(self):
        def alter(planned):
            planned["catalogues"][SOURCE]["fingerprint"] = "0" * 64   # as if DDL ran between plan and T0
        self.assertIn("changed during the export", self.capture_with(alter_plan=alter))

    def test_5_lost_row_is_refused(self):
        state = {"in_rows": False, "dropped": False}

        def drop_first_row(line, consume):
            if line.startswith(b"#vtsnap#"):
                state["in_rows"] = b"#rows#" in line and b"#t_nopk" in line
            elif state["in_rows"] and not state["dropped"]:
                state["dropped"] = True
                return
            consume(line)
        self.assertIn("differ from the server count/digest", self.capture_with(alter_line=drop_first_row))

    def test_6_changed_myisam_table_is_refused(self):
        def change_end(line, consume):
            if b"#nontx#end#" in line:
                head, count, *rest = line.split(b"\t")
                line = b"\t".join([head, b"99", *rest])
            consume(line)
        self.assertIn("changed during the export", self.capture_with(alter_line=change_end))

    def test_8_second_statement_in_ddl_is_not_executed(self):
        canary = f"vtsnap_canary_{secrets.token_hex(3)}"
        stand_sql(f"SET SESSION sql_log_bin=0;\nCREATE DATABASE `{canary}`;\n"
                  f"CREATE TABLE `{canary}`.victim LIKE `{SOURCE}`.t_num;\nALTER TABLE `{canary}`.victim ENGINE=MyISAM;\n")
        self.addCleanup(stand_sql, f"SET SESSION sql_log_bin=0;\nDROP DATABASE IF EXISTS `{canary}`;\n")
        path = self.snap / "db" / SOURCE / "ddl" / "t_num.sql"
        original = path.read_bytes()
        plain = original.rstrip(b"\n") + f";\nDROP DATABASE `{canary}`\n".encode()
        # a quote inside a comment must not hide the second statement (review of 2026-10-06)
        hidden = original.replace(b") ENGINE", f" /* ' */);\nDROP DATABASE `{canary}`;\n-- '\n) ENGINE".encode(), 1)
        # another engine: MERGE over a table of another database would receive the restore INSERTs (review round 2)
        merge = original.replace(b"ENGINE=InnoDB", f"ENGINE=MRG_MYISAM UNION=(`{canary}`.`victim`) INSERT_METHOD=LAST".encode(), 1)
        self.assertNotEqual(merge, original)
        try:
            for n, payload in enumerate((plain, hidden, merge)):
                path.unlink()
                path.write_bytes(payload)
                verify.write_seal(self.snap)                # the seal no longer protects: the DDL rule must
                _report, st = self.run_verify(f"verify-ddl-{n}")
                self.assertEqual((st["V1"], st["V3"], st["V4"], st["V5"]), ("pass", "pass", "fail", "pass"))
                self.assertEqual(stand_sql(f"SHOW DATABASES LIKE '{canary}';\n"), [canary.encode()])
                self.assertEqual(stand_sql(f"SELECT COUNT(*) FROM `{canary}`.victim;\n"), [b"0"])
        finally:
            path.unlink()
            path.write_bytes(original)
            verify.write_seal(self.snap)

    def test_9_file_list_fails_closed_without_paths(self):
        tree = ROOT / "tree"
        (tree / "secret-name-dir").mkdir(parents=True)
        (tree / "ok.txt").write_text("x")
        (tree / "unreadable-name.txt").write_text("y")
        (tree / "unreadable-name.txt").chmod(0)
        out = capture.parse_file_list(capture.local_file_list(tree, ["."], ROOT / "fl.log"))[0]
        self.assertEqual(out[b"unreadable-name.txt"][0], "unstable")
        (tree / "secret-name-dir").chmod(0)
        try:
            r = subprocess.run([sys.executable, "-I", str(capture.FILE_LIST), str(tree), "."], capture_output=True)
            self.assertEqual(r.returncode, 3)
            self.assertEqual(r.stdout, b"")
            self.assertNotIn(b"name", r.stderr)
        finally:
            (tree / "secret-name-dir").chmod(0o700)

    def test_10_altered_contract_never_reaches_sql(self):
        """sql_mode and column charsets from a resealed snapshot are checked before any SQL (review 2026-10-06)."""
        manifest_path = self.snap / "MANIFEST.json"
        tables_path = self.snap / "db" / SOURCE / "tables.json"
        originals = {manifest_path: manifest_path.read_bytes(), tables_path: tables_path.read_bytes()}
        mode_ok = verify.read_json(manifest_path)["source"]["sql_mode"]
        try:
            for name, path, change in (
                    ("mode-injection", manifest_path, lambda m: m["source"].update(sql_mode=mode_ok + "';DROP DATABASE x;'")),
                    ("mode-backslash", manifest_path, lambda m: m["source"].update(sql_mode=mode_ok + ",NO_BACKSLASH_ESCAPES")),
                    ("charset", tables_path, lambda t: t["t_str"]["columns"][1].update(charset="latin1 X'' ; DROP"))):
                for p, data in originals.items():
                    p.unlink()
                    p.write_bytes(data)
                obj = verify.read_json(path)
                change(obj)
                path.unlink()
                write_json(path, obj)
                verify.write_seal(self.snap)
                report, st = self.run_verify(f"verify-{name}")
                self.assertEqual((st["V0"], st["V1"], st["V4"]), ("fail", "pass", "fail"), name)
                self.assertEqual(report["tempdbs"]["created"], 0, name)
        finally:
            for p, data in originals.items():
                p.unlink()
                p.write_bytes(data)
            verify.write_seal(self.snap)

    def test_11_unexpected_error_prints_no_file_name(self):
        """A foreign exception may carry a file name; even if saving its traceback fails, the console
        gets the exception type only (review of 2026-10-06)."""
        def boom(_args):
            raise FileNotFoundError(2, "No such file", "/srv/storage/synthetic-client-name.pdf")

        def no_space(*_a, **_k):
            raise OSError(28, "No space left on device")

        saved = (snapshot.cmd_list, snapshot.write_private, sys.argv)
        err = io.StringIO()
        try:
            snapshot.cmd_list, snapshot.write_private, sys.argv = boom, no_space, ["snapshot.py", "list"]
            with contextlib.redirect_stderr(err):
                code = snapshot.main()
        finally:
            snapshot.cmd_list, snapshot.write_private, sys.argv = saved
        self.assertEqual(code, 1)
        self.assertIn("FileNotFoundError", err.getvalue())
        self.assertNotIn("synthetic-client-name", err.getvalue())
        self.assertNotIn("storage", err.getvalue())

    def test_12_partial_composition_is_not_complete(self):
        """A full verification demands both source databases and all file parts (review round 2)."""
        report = verify.verify(self.snap, ROOT, completeness=True, report_dir=ROOT / "verify-full")
        st = {c["id"]: c for c in report["checks"]}
        self.assertEqual(st["V0"]["status"], "fail")
        self.assertIn("composition", st["V0"]["counts"]["bad"])
        self.assertEqual((report["tempdbs"]["created"], report["completeness"]), (0, False))

    def test_13_cleanup_survives_a_failed_journal(self):
        temp = verify.TempDatabases(ROOT, ROOT / "logs13")
        names = [temp.create(SOURCE, "utf8mb4", "utf8mb4_0900_ai_ci") for _ in range(2)]

        def full_disk(state, name, original=temp._journal):
            if state == "dropped":
                raise OSError(28, "No space left on device")
            original(state, name)

        temp._journal = full_disk
        self.assertEqual(temp.drop_all(), [])
        self.assertEqual(verify.existing(names, ROOT / "test.log"), [])

    def test_14_audit_inputs_are_plain_identifiers(self):
        """gen_sql.py interpolates vtiger_field values into SQL run as root: only identifiers pass (review round 3)."""
        audit = ROOT / "audit14"
        audit.mkdir()
        (audit / "03_columns.tsv").write_text("TABLE_NAME\tCOLUMN_NAME\tDATA_TYPE\nvtiger_tab\tname\tvarchar\n")
        (audit / "04_tables.tsv").write_text("TABLE_NAME\nvtiger_tab\n")
        (audit / "05_primary_keys.tsv").write_text("TABLE_NAME\tpk\nvtiger_tab\ttabid,name\n")
        head = "tabid\tmodule\tfieldid\ttablename\tcolumnname\tfieldname\tuitype\n"
        (audit / "02_fields.tsv").write_text(head + "1\tAccounts\t1\tvtiger_account\taccountname\taccountname\t2\n")
        self.assertTrue(verify.audit_inputs_safe(audit))
        (audit / "02_fields.tsv").write_text(
            head + "1\tAccounts\t1\tvtiger_account\tx\tx';SET GLOBAL general_log=ON;SELECT 'x\t2\n")
        self.assertFalse(verify.audit_inputs_safe(audit))

    def test_15_engine_and_journal_edge_cases(self):
        ddl = "CREATE TABLE `t` (\n  `a` int\n) ENGINE=InnoDB"
        self.assertTrue(codec.single_create_table(ddl, "t", "InnoDB"))
        self.assertFalse(codec.single_create_table(ddl + " ENGINE='MyISAM'", "t", "InnoDB"))  # review round 3
        root = ROOT / "journal15"
        root.mkdir()
        (root / "tempdbs.journal").write_text("created\tvtsnap_20990101t000000_abcdef_x\ndropp")  # torn last line
        self.assertEqual(verify.journal_leftovers(root, ROOT / "test.log"), [])

    def test_7_root_inside_git_is_refused(self):
        with self.assertRaises(capture.SnapshotError):
            snapshot.ensure_root(REPO / "build" / "snapshots")


if __name__ == "__main__":
    unittest.main()
