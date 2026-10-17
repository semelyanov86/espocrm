"""Acceptance tests of the call history (stage 07.2, docs/migration/import.md «История звонков») on the stand: the
synthetic mini-Vtiger of stage 06.3 plus PBXManager/SPCallPopup records, a synthetic `asteriskcdrdb.cdr`, a synthetic
Master.csv and tiny WAV files — imported by the same code as a real run (importer.execute with the test sources).
Recordings are placed into the stand's recordings root under the synthetic day 2001-01-02 and removed by name;
records are removed by the ids this test recorded (never a list from the API). Telephony must be down
(task telephony:down) and its recordings root configured (task telephony:up once).

    task test:stage07.2
"""
import datetime as dt
import hashlib
import io
import json
import secrets
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "import"))
sys.path.insert(0, str(REPO / "scripts" / "snapshot"))
sys.path.insert(0, str(REPO / "tests" / "stage06_3"))
sys.path.insert(0, str(REPO / "tests" / "stage03"))
import importer  # noqa: E402
import test_stage06_3 as t3  # noqa: E402
from espo import BASE, Client  # noqa: E402
from test_stage06_3 import A1, KEYS, PREFIX, U_ADMIN, U_SALES, VT, entity, insert, one, sql  # noqa: E402

RUN = secrets.token_hex(3)
LID = f"978{secrets.randbelow(10 ** 6):06d}"     # Asterisk-like keys of the year 2001 (no real call has them)
DAY = "2001/01/02"
T0 = dt.datetime(2001, 1, 31)
MONITOR = Path("/var/lib/itvolga-espo/telephony/monitor")
SPOOL = "/var/spool/asterisk/monitor/"
EXTENSIONS = ("112", "113", "114", "115")
PX1, PX2, PX3, POP1, POP2, CTX, GONE = (VT + 971, VT + 972, VT + 973, VT + 975, VT + 976, VT + 977, VT + 978)
CDR_DDL = ("id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY, calldate DATETIME NOT NULL, "
           "clid VARCHAR(80) NOT NULL DEFAULT '', src VARCHAR(80) NOT NULL DEFAULT '', dst VARCHAR(80) NOT NULL DEFAULT '', "
           "dcontext VARCHAR(80) NOT NULL DEFAULT '', channel VARCHAR(80) NOT NULL DEFAULT '', "
           "dstchannel VARCHAR(80) NOT NULL DEFAULT '', lastapp VARCHAR(80) NOT NULL DEFAULT '', "
           "lastdata VARCHAR(80) NOT NULL DEFAULT '', duration INT NOT NULL DEFAULT 0, billsec INT NOT NULL DEFAULT 0, "
           "disposition VARCHAR(45) NOT NULL DEFAULT '', amaflags INT NOT NULL DEFAULT 0, "
           "accountcode VARCHAR(20) NOT NULL DEFAULT '', uniqueid VARCHAR(150) NOT NULL DEFAULT '', "
           "linkedid VARCHAR(150) NOT NULL DEFAULT '', peeraccount VARCHAR(80) NOT NULL DEFAULT '', "
           "sequence INT NOT NULL DEFAULT 0, userfield VARCHAR(255) NOT NULL DEFAULT '', "
           "recordingpath VARCHAR(255) NOT NULL DEFAULT ''")


def lid(n):
    return f"{LID}.{n}"


def ch(endpoint, n):
    return f"PJSIP/{endpoint}-{int(LID) % 4096:03x}{n:05x}"


def audio(frames):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        w.writeframes(secrets.token_bytes(2 * frames))
    return buf.getvalue()


def free_block():
    for _ in range(20):
        block = f"7999{secrets.randbelow(10000):04d}"
        if one(f"SELECT COUNT(*) FROM phone_number WHERE `numeric` LIKE '%{block[1:]}%'")[0] == "0":
            return block
    raise AssertionError("no free synthetic number block")


BLOCK = None


def num(n):
    return f"{BLOCK}{n:03d}"


def rec(name):
    return f"{DAY}/synth-{RUN}-{name}.wav"


def cdr_row(rid, uniqueid, linkedid, seq, local, duration, billsec, src, dst, dcontext, channel, dstchannel, lastapp,
            disposition, path=""):
    return insert("cdr", id=rid, calldate=local, clid=f'"{src}" <{src}>', src=src, dst=dst, dcontext=dcontext,
                  channel=channel, dstchannel=dstchannel, lastapp=lastapp, lastdata="", duration=duration,
                  billsec=billsec, disposition=disposition, amaflags=3, uniqueid=uniqueid, linkedid=linkedid,
                  sequence=seq, recordingpath=(SPOOL + path) if path else "")


def csv_line(src, dst, dcontext, channel, dstchannel, lastapp, start, answer, end, duration, billsec, disposition, uid):
    return ["", src, dst, dcontext, f'"{src}" <{src}>', channel, dstchannel, lastapp, "", start, answer, end,
            str(duration), str(billsec), disposition, "DOCUMENTATION", uid, ""]


def g2_wav():
    """D-31: the local minute (UTC 10:00 → CET 11:00), the caller and the callee of the CSV-only call."""
    return f"{DAY}/2001.01.02_11-00_From.114_To.+{num(2)}.wav"


def as_root(*argv):
    return subprocess.run(["sudo", "-n", *argv], capture_output=True, text=True, check=False)


def probe(payload):
    php = subprocess.run(["bash", "-c", f"source {REPO}/scripts/stand/lib.sh >/dev/null && echo $PHP_BIN"],
                         capture_output=True, text=True, check=True).stdout.strip()
    out = subprocess.run(["sudo", "-n", "-u", "espocrm", "env", f"ESPO_ROOT={REPO}", php, "--", json.dumps(payload)],
                         input=(Path(__file__).parent / "fixture.php").read_text(encoding="utf-8"),
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out.strip().splitlines()[-1])


def must(result, what):
    status, payload, _ = result
    if status != 200:
        raise AssertionError(f"{what}: HTTP {status}")
    return payload


class Stage072(t3.Stage063):
    runs = []
    created_api = []

    @classmethod
    def setUpClass(cls):
        global BLOCK
        super().setUpClass()
        BLOCK = free_block()
        busy = one("SELECT COUNT(*) FROM user WHERE deleted = 0 AND is_active = 1 AND c_phone_extension IN ("
                   + ",".join(f"'{e}'" for e in EXTENSIONS) + ")")[0]
        assert busy == "0", "an active user of the stand already has a test extension"
        t3.source_sql("\n".join(cls.vtiger_extras()))
        cls.cdr_db = cls.temp.create("asteriskcdrdb", "utf8mb4", "utf8mb4_0900_ai_ci")
        cls.cdr_sql(f"CREATE TABLE `cdr` ({CDR_DDL}) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;\n" + "\n".join(cls.cdr_rows()))
        cls.cdr_root = t3.ROOT / "cdr"
        cls.write_sources()
        cls.users()
        cls.live = probe({"live": {"linkedId": lid(6), "name": f"{PREFIX} live"}})["id"]
        cls.conflict = audio(400)
        tmp = Path(tempfile.mkdtemp(prefix="vt072-")) / "c.wav"
        tmp.write_bytes(cls.conflict)
        tmp.chmod(0o644)
        for d in ("2001", "2001/01", DAY):
            as_root("install", "-d", "-m", "0750", "-o", "100", "-g", "101", str(MONITOR / d))
        assert as_root("install", "-m", "0644", "-o", "100", "-g", "101", str(tmp), str(MONITOR / rec("conflict"))
                       ).returncode == 0, "cannot write into the stand's recordings root"

    @classmethod
    def cdr_sql(cls, script):
        t3.Mysql.stand(database=cls.cdr_db).lines(script + "\n", t3.ROOT / "cdr-source.log")

    @staticmethod
    def vtiger_extras():
        """PBXManager calls (external with a popup, internal with a popup, outbound to a deleted contact), a contact
        with the number of the calls."""
        p = "vtiger_pbxmanager"
        return [
            entity(CTX, "Contacts"),
            insert("vtiger_contactdetails", contactid=CTX, contact_no=f"КОНТАКТ_{CTX}", accountid=A1,
                   lastname=f"{PREFIX} CTX", phone="+" + num(1)),
            insert("vtiger_contactaddress", contactaddressid=CTX), insert("vtiger_contactsubdetails", contactsubscriptionid=CTX),
            insert("vtiger_contactscf", contactid=CTX), insert("vtiger_customerdetails", customerid=CTX),
            entity(GONE, "Contacts", deleted=1),
            insert("vtiger_contactdetails", contactid=GONE, contact_no=f"КОНТАКТ_{GONE}", lastname=f"{PREFIX} gone"),
            entity(PX1, "PBXManager"),
            insert(p, pbxmanagerid=PX1, direction="inbound", callstatus="completed", starttime="2020-06-01 12:00:00",
                   endtime="2020-06-01 12:05:00", totalduration=300, billduration=280,
                   recordingurl="http://127.0.0.1:5000/recording?id=1", sourceuuid="1", gateway="PBXManager",
                   customer="", user=str(U_SALES), customernumber=num(1), incominglinename="290001"),
            entity(POP1, "SPCallPopup", created="2020-06-01 12:06:00"),
            insert("vtiger_sp_callpopup", popupid=POP1, callid=PX1, status=1, firstname="Синт", comment=f"{PREFIX} popup"),
            insert("vtiger_crmentityrel", crmid=PX1, module="PBXManager", relcrmid=POP1, relmodule="SPCallPopup"),
            insert("vtiger_crmentityrel", crmid=POP1, module="SPCallPopup", relcrmid=PX1, relmodule="PBXManager"),
            insert("vtiger_crmentityrel", crmid=CTX, module="Contacts", relcrmid=PX1, relmodule="PBXManager"),
            entity(PX2, "PBXManager"),
            insert(p, pbxmanagerid=PX2, direction="outbound", callstatus="completed", starttime="2021-02-01 12:00:00",
                   endtime="2021-02-01 12:01:00", totalduration=60, billduration=50, sourceuuid="2",
                   gateway="PBXManager", user=str(U_SALES), customernumber="113"),
            entity(POP2, "SPCallPopup"),
            insert("vtiger_sp_callpopup", popupid=POP2, callid=PX2, status=1, comment=f"{PREFIX} internal"),
            entity(PX3, "PBXManager"),
            insert(p, pbxmanagerid=PX3, direction="outbound", callstatus="busy", starttime="2023-05-05 10:00:00",
                   totalduration=30, billduration=0, sourceuuid="3", gateway="PBXManager", customer=str(GONE),
                   user=str(U_SALES), customernumber="8" + num(5)[1:]),
        ]

    @staticmethod
    def cdr_rows():
        """G1 inbound in two legs (112 rings, 113 answers), G3 voice menu only (its recording is not in the snapshot),
        G4 outbound with a header-only recording, G5 trainer, G6 the key of a live call, G7 a recording whose path holds
        another file in the root. The CSV adds G1's lines (overlap), G2 (CSV only) and a line after T0."""
        tr, g1 = ch("trunk-russia", 1), rec("g1")
        return [
            cdr_row(1, lid(1), lid(1), 1, "2001-01-02 10:00:00", 20, 0, num(1), "290001", "call-in", tr, ch("112", 2),
                    "Dial", "NO ANSWER", g1),
            cdr_row(2, lid(1), lid(1), 2, "2001-01-02 10:00:20", 70, 40, num(1), "290001", "call-in", tr, ch("113", 3),
                    "Dial", "ANSWERED", g1),
            cdr_row(3, lid(3), lid(3), 1, "2001-01-02 12:00:00", 15, 15, num(3), "s", "incoming-menu",
                    ch("trunk-russia", 6), "", "BackGround", "ANSWERED", rec("missing")),
            cdr_row(4, lid(4), lid(4), 1, "2001-01-02 13:00:00", 30, 5, "115", "+" + num(4), "call-out", ch("115", 7),
                    ch("trunk-russia", 8), "Dial", "ANSWERED", rec("empty")),
            cdr_row(5, lid(5), lid(5), 1, "2001-01-02 14:00:00", 40, 40, "112", "555", "german-training", ch("112", 9),
                    "", "AGI", "ANSWERED", rec("trainer")),
            cdr_row(6, lid(6), lid(6), 1, "2001-01-02 10:30:00", 60, 50, "113", "+" + num(6), "call-out", ch("113", 10),
                    ch("trunk-russia", 11), "Dial", "ANSWERED", rec("live")),
            cdr_row(7, lid(7), lid(7), 1, "2001-01-02 15:00:00", 60, 45, "113", "+" + num(7), "call-out", ch("113", 12),
                    ch("trunk-russia", 13), "Dial", "ANSWERED", rec("conflict")),
        ]

    @classmethod
    def write_sources(cls, bill=40):
        tr = ch("trunk-russia", 1)
        answer = (dt.datetime(2001, 1, 2, 9, 1, 30) - dt.timedelta(seconds=bill)).strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            csv_line(num(1), "290001", "call-in", tr, ch("112", 2), "Dial", "2001-01-02 09:00:00", "",
                     "2001-01-02 09:00:20", 20, 0, "NO ANSWER", lid(1)),
            csv_line(num(1), "290001", "call-in", tr, ch("113", 3), "Dial", "2001-01-02 09:00:20", answer,
                     "2001-01-02 09:01:30", 70, bill, "ANSWERED", lid(1)),
            csv_line("114", "+" + num(2), "call-out", ch("114", 4), ch("trunk-russia", 5), "Dial", "2001-01-02 10:00:10",
                     "2001-01-02 10:00:15", "2001-01-02 10:01:10", 60, 55, "ANSWERED", lid(2)),
            csv_line(num(9), "290001", "call-in", ch("trunk-russia", 14), "", "BackGround", "2001-01-30 23:59:50",
                     "2001-01-30 23:59:50", "2001-01-31 00:00:20", 30, 30, "ANSWERED", lid(9)),
        ]
        import csv as csvmod
        (cls.cdr_root / "cdr-csv").mkdir(parents=True, exist_ok=True)
        with open(cls.cdr_root / "cdr-csv" / "Master.csv", "w", newline="", encoding="utf-8") as fh:
            csvmod.writer(fh, quoting=csvmod.QUOTE_ALL).writerows(lines)
        if getattr(cls, "audio", None):
            return
        cls.audio = {rec("g1"): audio(800), g2_wav(): audio(600), rec("empty"): audio(0), rec("trainer"): audio(300),
                     rec("live"): audio(300), rec("conflict"): audio(500)}
        for rel, data in cls.audio.items():
            path = cls.cdr_root / "monitor" / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        assert len(cls.audio[rec("empty")]) == 44

    @classmethod
    def users(cls):
        admin = cls.client
        roles = {r["name"]: r["id"] for r in must(admin.get("Role", maxSize=200), "roles")["list"]}

        def create(entity, data):
            payload = must(admin.post(entity, data), f"create {entity}")
            cls.created_api.append((entity, payload["id"]))
            return payload["id"]

        cls.teams = [create("Team", {"name": f"{PREFIX} T{i}"}) for i in (1, 2)]
        norec = create("Role", {"name": f"{PREFIX} no-recording",
                                "data": {"Call": {"create": "yes", "read": "all", "edit": "no", "delete": "no"}},
                                "fieldData": {"Call": {"cRecording": {"read": "no", "edit": "no"}}}})
        cls.uid, cls.clients = {}, {}
        for key, role_ids, team, ext in (
                ("u112", [roles["Менеджер по продажам"]], 1, "112"), ("u113", [roles["Менеджер по продажам"]], 0, "113"),
                ("u114", [roles["Менеджер по продажам"]], 0, "114"), ("u115", [roles["Менеджер по продажам"]], 1, "115"),
                ("mate", [roles["Менеджер по продажам"]], 0, None), ("outsider", [roles["Менеджер по продажам"]], 1, None),
                ("director", [roles["Директор"]], 1, None), ("norec", [norec], 1, None)):
            password = secrets.token_urlsafe(18) + "Aa1!"
            data = {"userName": f"synth-cdr-{RUN}-{key}", "lastName": f"{PREFIX} {key}", "type": "regular",
                    "isActive": True, "password": password, "passwordConfirm": password, "rolesIds": role_ids,
                    "teamsIds": [cls.teams[team]], "defaultTeamId": cls.teams[team], "sendAccessInfo": False}
            if ext:
                data["cPhoneExtension"] = ext
            cls.uid[key] = create("User", data)
            cls.clients[key] = Client(data["userName"], password)

    @classmethod
    def run_import(cls, check_only=False, only=t3.ONLY, files_root=None, recordings="place"):
        rundir = t3.ROOT / f"run-{len(cls.runs)}"
        rundir.mkdir()
        report = importer.execute(rundir, source_db=t3.SOURCE, only=only, check_only=check_only, adopt=t3.ADMIN_NAME,
                                  key_range=KEYS, effective_admin=U_ADMIN, files_root=files_root or cls.files,
                                  cdr_db=cls.cdr_db, cdr_root=cls.cdr_root, cdr_t0=T0, recordings=recordings)
        recs = [json.loads(line) for line in (rundir / "records.jsonl").read_text().splitlines()]
        calls = {c["key"]: c for c in map(json.loads, (rundir / "telephony-calls.jsonl").read_text().splitlines())}
        cls.runs.append(recs + [{"key": f"cdr:{k}", "id": c["id"]} for k, c in calls.items() if c.get("id")])
        return report, calls, rundir

    @classmethod
    def cleanup(cls):
        """The 06.3 cleanup plus the calls of this test (PBXManager, CDR, the live one), their links, history and
        recordings, and the users, teams and role created through the API."""
        ids = ({cls.live} if getattr(cls, "live", None) else set()) | set(getattr(cls, "extra_calls", []))
        for recs in cls.runs:
            ids |= {r["id"] for r in recs if r.get("id") and r["key"].split(":")[0] in ("Call", "cdr")}
        for journal in t3.ROOT.glob("run-*/applied.jsonl"):
            for line in journal.read_text().splitlines():
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if entry["key"].split(":")[0] in ("Call", "cdr"):
                    ids.add(entry["id"])
        if ids:
            listed = ",".join(f"'{i}'" for i in sorted(ids))
            script = [f"DELETE FROM `{t}` WHERE call_id IN ({listed});" for t in ("call_contact", "call_user", "call_lead")]
            script += [f"DELETE FROM entity_team WHERE entity_type = 'Call' AND entity_id IN ({listed});",
                       f"DELETE FROM reminder WHERE entity_type = 'Call' AND entity_id IN ({listed});",
                       f"DELETE FROM action_history_record WHERE target_type = 'Call' AND target_id IN ({listed});",
                       f"DELETE FROM `call` WHERE id IN ({listed});"]
            t3.Mysql.stand(database="espocrm").lines("\n".join(script) + "\n", t3.ROOT / "cleanup.log")
        for rel in [*getattr(cls, "audio", {}), rec("missing")]:
            as_root("rm", "-f", str(MONITOR / rel))
        for d in (DAY, "2001/01", "2001"):
            as_root("rmdir", str(MONITOR / d))  # only when empty
        for entity, rid in reversed(cls.created_api):
            cls.client.delete(f"{entity}/{rid}")
        if cls.created_api:
            by = {}
            for entity, rid in cls.created_api:
                by.setdefault(entity, []).append(rid)
            script = []
            for entity, table in (("User", "user"), ("Team", "team"), ("Role", "role")):
                if by.get(entity):
                    listed = ",".join(f"'{i}'" for i in by[entity])
                    script += [f"DELETE FROM team_user WHERE user_id IN ({listed}) OR team_id IN ({listed});",
                               f"DELETE FROM role_user WHERE user_id IN ({listed}) OR role_id IN ({listed});",
                               f"DELETE FROM `{table}` WHERE id IN ({listed});"]
            t3.Mysql.stand(database="espocrm").lines("\n".join(script) + "\n", t3.ROOT / "cleanup.log")
        super().cleanup()

    def call(self, key):
        cols = ("id", "status", "direction", "date_start", "date_end", "c_bill_duration", "c_answered_at",
                "c_call_status_raw", "c_extension", "assigned_user_id", "parent_type", "parent_id", "c_recording",
                "IFNULL(c_recording_path, '')", "c_cdr_source", "c_live_state", "c_phone_number",
                "IFNULL(c_incoming_line, '')", "name", "IFNULL(description, '')", "deleted", "modified_at")
        row = one(f"SELECT {', '.join(cols)} FROM `call` WHERE c_asterisk_linked_id = '{key}'")
        if not row:
            return None
        return dict(zip(("id", "status", "direction", "start", "end", "bill", "answered", "raw", "ext", "assigned",
                         "parent_type", "parent_id", "recording", "path", "source", "state", "number", "line", "name",
                         "description", "deleted", "modified"), row))

    def related(self, table, call_id, column):
        return sorted(r[0] for r in sql(f"SELECT {column} FROM {table} WHERE call_id = '{call_id}' AND deleted = 0"))

    # --- scenarios (in order) ----------------------------------------------------------------------------------

    def test_01_import(self):
        report, calls, rundir = self.run_import()
        self.__class__.first = report
        self.assertEqual(report["problems"], {}, report.get("problem_columns"))
        self.assertEqual(report["silence"], {k: 0 for k in report["silence"]})
        t = report["telephony"]
        self.assertEqual(t["groups"]["classes"], {"Inbound": 2, "Outbound": 4, "trainer": 1})
        self.assertEqual(t["csv"]["fates"], {"duplicate_of_mysql": 2, "call": 1, "after_t0": 1})
        self.assertEqual({k: calls[lid(n)]["apply"] for k, n in (("g1", 1), ("g2", 2), ("g3", 3), ("g4", 4), ("g7", 7))},
                         {k: "created" for k in ("g1", "g2", "g3", "g4", "g7")})
        self.assertEqual((calls[lid(6)]["apply"], calls[lid(6)]["check"]), ("live_call", "live_call"))
        for finding in ("live_call", "recording_placement_conflict", "recording_unavailable:missing_in_snapshot",
                        "recording_unavailable:without_audio", "csv_after_t0"):
            self.assertIn(finding, report["findings"])
        cdr_columns = [c for c in report["columns"] if c["module"] == "CDR"]
        self.assertEqual(len(cdr_columns), 21)
        self.assertEqual([c["column"] for c in cdr_columns if c["unaccounted"] or c["mismatch"]], [])
        self.assertEqual(sorted(p.name for p in rundir.glob("telephony-*.jsonl")),
                         ["telephony-calls.jsonl", "telephony-files.jsonl", "telephony-lines.jsonl",
                          "telephony-rows.jsonl"])

    def test_02_several_legs_and_the_overlap_make_one_call(self):
        c = self.call(lid(1))
        self.assertEqual((c["status"], c["direction"], c["raw"], c["bill"], c["ext"], c["assigned"], c["source"],
                          c["state"], c["line"], c["number"]),
                         ("Held", "Inbound", "ANSWER", "40", "113", self.uid["u113"], "mysql", "ended", "290001",
                          "+" + num(1)))
        self.assertEqual((c["start"], c["end"], c["answered"]),
                         ("2001-01-02 09:00:00", "2001-01-02 09:01:30", "2001-01-02 09:00:50"))  # exact UTC of the CSV
        self.assertEqual(self.related("call_user", c["id"], "user_id"), sorted([self.uid["u112"], self.uid["u113"]]))
        account = self.id_of("account", A1)
        self.assertEqual((c["parent_type"], c["parent_id"]), ("Account", account))
        self.assertEqual(self.related("call_contact", c["id"], "contact_id"), [self.id_of("contact", CTX)])
        self.assertEqual((c["recording"], c["path"]), ("1", rec("g1")))
        self.assertEqual(one(f"SELECT COUNT(*) FROM `call` WHERE c_asterisk_linked_id LIKE '{LID}.%'")[0], "6",
                         "five CDR calls and the live one")
        teams = [r[0] for r in sql(f"SELECT team_id FROM entity_team WHERE entity_type = 'Call' "
                                   f"AND entity_id = '{c['id']}' AND deleted = 0")]
        self.assertIn(self.teams[0], teams, "the default team of the assignee")
        others = {one(f"SELECT name FROM team WHERE id = '{t}'")[0] for t in teams if t != self.teams[0]}
        self.assertLessEqual(others, {"Подчинённые заместителей"}, "plus the hierarchy team of a manager's record")

    def test_03_csv_only_call_with_its_d31_recording(self):
        c = self.call(lid(2))
        self.assertEqual((c["direction"], c["source"], c["ext"], c["assigned"], c["recording"], c["path"]),
                         ("Outbound", "csv", "114", self.uid["u114"], "1", g2_wav()))

    def test_04_unavailable_audio_and_classes_not_imported(self):
        self.assertEqual((self.call(lid(3))["recording"], self.call(lid(3))["raw"], self.call(lid(3))["status"]),
                         ("0", "NODIAL", "Not Held"))
        self.assertEqual(self.call(lid(4))["recording"], "0", "header only: no audio")
        self.assertEqual(self.call(lid(7))["recording"], "0", "another file at its path in the root")
        self.assertIsNone(self.call(lid(5)), "trainer: never a call")
        self.assertIsNone(self.call(lid(9)), "after T0: the next snapshot")
        for name in ("trainer", "live", "empty", "missing"):
            self.assertNotEqual(as_root("test", "-e", str(MONITOR / rec(name))).returncode, 0, f"{name} not placed")
        digest = as_root("sha256sum", str(MONITOR / rec("conflict"))).stdout.split(" ")[0]
        self.assertEqual(digest, hashlib.sha256(self.conflict).hexdigest(), "the file in the root is never replaced")

    def test_05_live_call_untouched(self):
        live = one(f"SELECT IFNULL(c_cdr_source, ''), c_bill_duration, name, modified_at FROM `call` WHERE id = '{self.live}'")
        self.assertEqual(live[:3], ["", "50", f"{PREFIX} live"])

    def test_06_pbxmanager_history(self):
        row = one(f"SELECT id, status, direction, date_start, date_end, c_call_status_raw, c_bill_duration, "
                  f"IFNULL(c_legacy_recording_url, ''), c_connector_call_id, c_recording, IFNULL(c_asterisk_linked_id, ''), "
                  f"parent_type, parent_id, description, vtiger_data, c_phone_number, name FROM `call` "
                  f"WHERE vtiger_id = {PX1} AND deleted = 0")
        self.assertEqual(row[1:7], ["Held", "Inbound", "2020-06-01 10:00:00", "2020-06-01 10:05:00", "completed", "280"])
        self.assertEqual(row[7:11], ["http://127.0.0.1:5000/recording?id=1", "1", "0", ""])
        self.assertEqual((row[11], row[12]), ("Account", self.id_of("account", A1)), "the contact of the number")
        self.assertEqual(row[13], f"{PREFIX} popup", "the popup's comment")
        data = json.loads(row[14])
        self.assertEqual((data["popup_createdtime"], data["popup_firstname"]), ("2020-06-01 12:06:00", "Синт"))
        self.assertEqual(row[15], "+" + num(1))
        self.assertEqual(self.related("call_contact", row[0], "contact_id"), [self.id_of("contact", CTX)])
        self.assertEqual(404, self.client.entry_point("itvolgaRecording", id=row[0])[0], "the dead connector: no audio")
        self.assertIsNone(one(f"SELECT id FROM `call` WHERE vtiger_id = {PX2}"), "an internal call is not imported")
        busy = one(f"SELECT status, c_call_status_raw, date_start, date_end, vtiger_data, IFNULL(parent_id, '') "
                   f"FROM `call` WHERE vtiger_id = {PX3}")
        self.assertEqual(busy[:4], ["Not Held", "busy", "2023-05-05 08:00:00", "2023-05-05 08:00:00"])
        data = json.loads(busy[4])
        self.assertEqual((data["dateEndMissing"], data["totalduration"]), (True, 30))
        self.assertEqual(busy[5], "", "a deleted customer and no client with the number: no parent")

    def test_07_recording_access(self):
        call_id = self.call(lid(1))["id"]
        expected = {"u113": 200, "u112": 200, "mate": 200, "director": 200, "outsider": 403, "norec": 403}
        for key, status in expected.items():
            got, body, headers = self.clients[key].entry_point("itvolgaRecording", id=call_id)
            self.assertEqual(status, got, key)
            if status == 200:
                self.assertEqual("audio/wav", headers.get("Content-Type"))
                self.assertEqual(body, self.audio[rec("g1")], key)
        self.assertEqual(200, self.client.entry_point("itvolgaRecording", id=call_id)[0])
        got, body, headers = self.clients["u113"]._send(f"{BASE}/?entryPoint=itvolgaRecording&id={call_id}", "GET",
                                                        None, {"Range": "bytes=10-19"})
        self.assertEqual((got, len(body)), (206, 10))
        logged = dict((u, int(n)) for u, n in sql(
            f"SELECT user_id, COUNT(*) FROM action_history_record WHERE action = 'listen' AND target_type = 'Call' "
            f"AND target_id = '{call_id}' GROUP BY user_id"))
        self.assertEqual(logged.get(self.uid["u113"]), 1)
        self.assertNotIn(self.uid["outsider"], logged)
        api = must(self.client.get(f"Call/{call_id}"), "call")
        self.assertNotIn("cRecordingPath", api)
        self.assertEqual(api["cCdrSource"], "mysql")
        self.assertEqual(404, self.client.entry_point("itvolgaRecording", id=self.call(lid(4))["id"])[0])

    def test_08_facts_are_closed_and_edits_stay(self):
        call_id = self.call(lid(1))["id"]
        must(self.clients["u113"].put(f"Call/{call_id}", {
            "name": f"{PREFIX} переименован", "description": "заметка", "status": "Planned",
            "dateStart": "2020-01-01 00:00:00", "dateEnd": "2020-01-01 00:10:00"}), "edit")
        c = self.call(lid(1))
        self.assertEqual((c["name"], c["description"], c["status"], c["start"]),
                         (f"{PREFIX} переименован", "заметка", "Held", "2001-01-02 09:00:00"))

    def test_09_rerun_writes_nothing(self):
        report, calls, _ = self.run_import()
        self.assertEqual(report["problems"], {}, report.get("problem_columns"))
        self.assertEqual({k: c["apply"] for k, c in calls.items() if c["class"] in ("Inbound", "Outbound")},
                         {lid(n): ("live_call" if n == 6 else "unchanged") for n in (1, 2, 3, 4, 6, 7)})
        self.assertEqual(calls[lid(1)]["recording"]["placement"], "present")
        self.assertEqual(report["telephony"]["pbx"]["check"], {"equal": 2})
        self.assertEqual(self.call(lid(1))["name"], f"{PREFIX} переименован", "a user's edit stays")

    def test_10_delta_facts_deleted_absent(self):
        """The source changes G1's talk time (facts only), loses G4 (the call stays); an administrator deleted G2 (not
        created again); PX3 is deleted in Vtiger (removed by the delta); the answering phone's user lost its extension
        (cExtension follows, the assignee stays)."""
        self.cdr_sql("UPDATE cdr SET billsec = 45 WHERE id = 2; DELETE FROM cdr WHERE id = 4;")
        self.write_sources(bill=45)
        must(self.client.put(f"User/{self.uid['u113']}", {"cPhoneExtension": None}), "extension of u113")
        t3.source_sql(f"UPDATE vtiger_crmentity SET deleted = 1 WHERE crmid = {PX3};")
        self.assertEqual(200, self.client.delete(f"Call/{self.call(lid(2))['id']}")[0])
        report, calls, _ = self.run_import()
        self.assertEqual(report["problems"], {}, report.get("problem_columns"))
        self.assertEqual((calls[lid(1)]["apply"], calls[lid(2)]["apply"]), ("updated", "deleted_in_target"))
        c = self.call(lid(1))
        self.assertEqual((c["bill"], c["answered"], c["name"], c["ext"], c["assigned"]),
                         ("45", "2001-01-02 09:00:45", f"{PREFIX} переименован", "112", self.uid["u113"]))
        self.assertEqual(calls[lid(1)]["check"], "equal", "the check pass after the write")
        self.assertEqual(self.call(lid(2))["deleted"], "1", "not created again")
        self.assertEqual(self.call(lid(4))["deleted"], "0", "a CDR call gone from the source stays")
        self.assertIn(lid(4), report["telephony"]["absent_keys"])  # (the stand's real CDR calls are absent too)
        self.assertIsNone(one(f"SELECT id FROM `call` WHERE vtiger_id = {PX3} AND deleted = 0"), "removed by the delta")

    def test_11_a_path_another_call_stores_stays_claimed_and_plays_for_none(self):
        """The live listener later stores G1's recording path on another call (same minute and numbers): the history
        call keeps its claim (cRecording off) on the next run, so neither call plays a file of uncertain owner."""
        g1 = self.call(lid(1))
        other = probe({"live": {"linkedId": lid(8), "name": f"{PREFIX} live 2", "recordingPath": rec("g1")}})["id"]
        self.__class__.extra_calls = [other]
        report, calls, _ = self.run_import()
        self.assertEqual(report["problems"], {}, report.get("problem_columns"))
        self.assertEqual(calls[lid(1)]["recording"]["writer"], "claimed_in_target")
        c = self.call(lid(1))
        self.assertEqual((c["recording"], c["path"]), ("0", rec("g1")), "the claim stays")
        for call_id in (g1["id"], other):
            self.assertEqual(404, self.client.entry_point("itvolgaRecording", id=call_id)[0])

    def test_12_a_shared_claim_survives_a_run_without_the_recording(self):
        """The next snapshot no longer names G1's recording: its stored path, shared with the other call, is kept
        (claim_kept) — otherwise the other call would become the file's sole claimant and play it."""
        self.cdr_sql("UPDATE cdr SET recordingpath = '' WHERE id IN (1, 2);")
        report, calls, _ = self.run_import()
        self.assertEqual(report["problems"], {}, report.get("problem_columns"))
        self.assertEqual(calls[lid(1)]["recording"]["writer"], "claim_kept")
        c = self.call(lid(1))
        self.assertEqual((c["recording"], c["path"]), ("0", rec("g1")))
        for call_id in (c["id"], *self.extra_calls):
            self.assertEqual(404, self.client.entry_point("itvolgaRecording", id=call_id)[0])

    def test_13_verify_mode_checks_the_file_where_it_is(self):
        """--recordings verify (production): nothing is copied; the writer itself refuses a file in the root whose
        size or sha256 is not the snapshot's (G7: another file at its path) — a finding, not a problem."""
        report, calls, _ = self.run_import(recordings="verify")
        self.assertEqual(report["problems"], {}, report.get("problem_columns"))
        self.assertEqual(calls[lid(7)]["recording"]["placement"], None, "nothing copied in verify mode")
        self.assertIn(calls[lid(7)]["recording"]["writer"], ("size", "sha256"))
        self.assertEqual(self.call(lid(7))["recording"], "0")
        self.assertTrue({"recording_size", "recording_sha256"} & set(report["findings"]))


# The scenarios of stage 06.3 belong to its own suite: this class reuses only its fixture and cleanup.
for _name in [n for n in vars(t3.Stage063) if n.startswith("test_") and n not in vars(Stage072)]:
    setattr(Stage072, _name, None)


if __name__ == "__main__":
    unittest.main()
