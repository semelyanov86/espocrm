"""Pure tests of the CDR history planner (stage 07.2, scripts/import/cdr.py) and of the telephony parts of the
reconciliation — synthetic rows only, no stand, no snapshot.

    task test:stage07.2   (runs these together with the stand tests)
"""
import datetime as dt
import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "import"))
import cdr  # noqa: E402
import history  # noqa: E402
import ledger  # noqa: E402
import transforms as T  # noqa: E402

RULES = cdr.Rules({"extensionPattern": "^[12][01][0-9]$",
                   "trunks": {"trunk-russia": "inbound", "trunk-megafon": "inbound", "trunk-easybell": "ignored"},
                   "inboundContexts": ["call-in"], "originatePrefix": "crm-", "localAreaCode": "8352"})
T0 = dt.datetime(2026, 9, 30, 12, 0, 0)
NUM = "7999" + "0000001"  # built at run time: no phone-shaped literal in Git
NUM2 = "7999" + "0000002"


def ch(endpoint, n):
    return f"PJSIP/{endpoint}-{n:08x}"


def mysql(i, uid, lid, seq, local, duration, billsec, src, dst, dcontext, channel, dstchannel, lastapp, disposition,
          path=None):
    return {"cdr.id": str(i), "cdr.uniqueid": uid, "cdr.linkedid": lid, "cdr.sequence": str(seq), "cdr.calldate": local,
            "cdr.duration": str(duration), "cdr.billsec": str(billsec), "cdr.src": src, "cdr.dst": dst,
            "cdr.dcontext": dcontext, "cdr.channel": channel, "cdr.dstchannel": dstchannel, "cdr.lastapp": lastapp,
            "cdr.disposition": disposition, "cdr.recordingpath": path, "cdr.clid": f'"{src}" <{src}>',
            "cdr.amaflags": "3", "cdr.lastdata": "", "cdr.accountcode": "", "cdr.peeraccount": "", "cdr.userfield": ""}


def csv_line(src, dst, dcontext, channel, dstchannel, lastapp, start, answer, end, duration, billsec, disposition, uid):
    return ["", src, dst, dcontext, f'"{src}" <{src}>', channel, dstchannel, lastapp, "", start, answer, end,
            str(duration), str(billsec), disposition, "DOCUMENTATION", uid, ""]


def wav(day_local, minute, frm, to):
    y, m, d = day_local.split("-")
    return f"{y}/{m}/{d}/{y}.{m}.{d}_{minute}_From.{frm}_To.{to}.wav"


class PlannerTest(unittest.TestCase):
    def build(self, rows=(), lines=(), inventory=None):
        return cdr.build(list(rows), list(enumerate(lines, 1)), inventory or {}, RULES, T0)

    def test_overlap_csv_is_the_mysql_row_and_gives_exact_utc(self):
        """D-20: the CSV start in UTC equals the local calldate (Europe/Berlin, +2 in summer) → the same row."""
        rows = [mysql(1, "100.1", "100.1", 1, "2026-08-10 11:00:00", 60, 40, NUM, "290001", "call-in",
                      ch("trunk-russia", 1), ch("118", 2), "Dial", "ANSWERED")]
        lines = [csv_line(NUM, "290001", "call-in", ch("trunk-russia", 1), ch("118", 2), "Dial", "2026-08-10 09:00:00",
                          "2026-08-10 09:00:20", "2026-08-10 09:01:00", 60, 40, "ANSWERED", "100.1"),
                 ]
        plan = self.build(rows, lines)
        self.assertEqual(plan.lines[1], "duplicate_of_mysql")
        self.assertEqual(len(plan.ops), 1)
        facts = plan.ops[0].payload()
        self.assertEqual((facts["dateStart"], facts["answeredAt"], facts["billSeconds"]),
                         ("2026-08-10 09:00:00", "2026-08-10 09:00:20", 40))
        winter = self.build([mysql(2, "200.1", "200.1", 1, "2026-11-10 10:00:00", 5, 0, NUM, "290001", "call-in",
                                   ch("trunk-russia", 3), "", "BackGround", "ANSWERED")], [])
        # a MySQL row is in the snapshot by definition (T0 bounds only CSV lines); winter time is +1
        self.assertEqual(winter.ops[0].payload()["dateStart"], "2026-11-10 09:00:00")

    def test_several_legs_of_one_call(self):
        """Sequential ringing: two Dial legs of one uniqueid (sequences 1, 2) → one call; the second phone answered."""
        lid = "300.1"
        rows = [mysql(1, lid, lid, 1, "2026-09-01 10:00:00", 20, 0, NUM, "290001", "call-in", ch("trunk-russia", 5),
                      ch("118", 6), "Dial", "NO ANSWER", "/var/spool/asterisk/monitor/2026/09/01/a.wav"),
                mysql(2, lid, lid, 2, "2026-09-01 10:00:20", 70, 50, NUM, "290001", "call-in", ch("trunk-russia", 5),
                      ch("218", 7), "Dial", "ANSWERED", "/var/spool/asterisk/monitor/2026/09/01/a.wav"),
                mysql(3, "300.9", lid, 1, "2026-09-01 10:00:20", 70, 50, NUM, "s", "phones-in", ch("218", 7), "",
                      "AppDial", "ANSWERED")]
        plan = self.build(rows, [], {"2026/09/01/a.wav": (5000, "a" * 64)})
        self.assertEqual(len(plan.ops), 1)
        p = plan.ops[0].payload()
        self.assertEqual((p["direction"], p["rawStatus"], p["rungExtensions"], p["answeredExtension"], p["billSeconds"]),
                         ("Inbound", "ANSWER", ["118", "218"], "218", 50))
        self.assertEqual(p["recording"], {"path": "2026/09/01/a.wav", "size": 5000, "sha256": "a" * 64})
        self.assertEqual(p["line"], "290001")
        self.assertEqual(set(plan.rows.values()), {"call"})
        self.assertEqual(plan.files["2026/09/01/a.wav"], "candidate")

    def test_a_csv_leg_missing_in_mysql_joins_its_call(self):
        """MySQL has the unanswered first Dial; the answered second leg exists only in the CSV (the table lost the row):
        the leg joins the call of its uniqueid instead of being dropped. A uniqueid of two MySQL calls is a conflict."""
        lid = "150.1"
        rows = [mysql(1, lid, lid, 1, "2026-08-11 11:00:00", 20, 0, NUM, "290001", "call-in", ch("trunk-russia", 1),
                      ch("118", 2), "Dial", "NO ANSWER"),
                mysql(2, "160.1", "160.1", 1, "2026-08-11 12:00:00", 5, 0, NUM, "s", "call-in", ch("trunk-russia", 3),
                      "", "BackGround", "ANSWERED"),
                mysql(3, "160.1", "170.1", 2, "2026-08-11 12:00:00", 5, 0, NUM, "s", "call-in", ch("trunk-russia", 4),
                      "", "BackGround", "ANSWERED")]
        lines = [csv_line(NUM, "290001", "call-in", ch("trunk-russia", 1), ch("218", 5), "Dial", "2026-08-11 09:00:20",
                          "2026-08-11 09:00:30", "2026-08-11 09:01:30", 70, 60, "ANSWERED", lid),
                 csv_line(NUM, "s", "call-in", ch("trunk-russia", 6), "", "Hangup", "2026-08-11 10:05:00",
                          "2026-08-11 10:05:00", "2026-08-11 10:05:01", 1, 1, "ANSWERED", "160.1")]
        plan = self.build(rows, lines)
        p = next(o.payload() for o in plan.ops if o.group.key == lid)
        self.assertEqual((p["rawStatus"], p["billSeconds"], p["answeredExtension"], p["rungExtensions"]),
                         ("ANSWER", 60, "218", ["118", "218"]))
        self.assertEqual((plan.lines[1], plan.lines[2], plan.flags["csv_leg_joined_mysql"]),
                         ("call", "conflict_with_mysql", 1))

    def test_overflow_to_the_mobile_is_a_human_answer_without_a_phone(self):
        lid = "310.1"
        rows = [mysql(1, lid, lid, 1, "2026-09-02 10:00:00", 30, 0, NUM, "290001", "call-in", ch("trunk-russia", 8),
                      ch("trunk-russia", 9), "Dial", "NO ANSWER"),
                mysql(2, lid, lid, 2, "2026-09-02 10:00:30", 40, 25, NUM, "290001", "call-in", ch("trunk-russia", 8),
                      ch("trunk-russia", 10), "Dial", "ANSWERED")]
        p = self.build(rows).ops[0].payload()
        self.assertEqual((p["rawStatus"], p["answeredExtension"], p["rungExtensions"]), ("ANSWER", None, []))

    def test_voice_menu_answer_is_not_a_human_answer(self):
        rows = [mysql(1, "320.1", "320.1", 1, "2026-09-03 10:00:00", 15, 15, NUM, "s", "incoming-menu",
                      ch("trunk-russia", 11), "", "BackGround", "ANSWERED")]
        p = self.build(rows).ops[0].payload()
        self.assertEqual((p["direction"], p["rawStatus"], p["answeredAt"], p["billSeconds"], p["line"]),
                         ("Inbound", "NODIAL", None, 0, None))

    def test_classes_like_the_live_integration(self):
        def one(channel, dstchannel, dst, dcontext, lastapp, disposition="ANSWERED"):
            return self.build([mysql(1, "400.1", "400.1", 1, "2026-09-04 10:00:00", 30, 20, "105", dst, dcontext,
                                     channel, dstchannel, lastapp, disposition)]).groups[0]
        out = one(ch("105", 1), ch("trunk-russia", 2), "+7" + NUM[1:], "call-out", "Dial")
        self.assertEqual((out.direction, out.facts["callerExtension"], out.facts["numberRaw"]),
                         ("Outbound", "105", "+7" + NUM[1:]))
        self.assertEqual(one(ch("105", 1), ch("118", 2), "118", "call-out", "Dial").reason, "internal")
        self.assertEqual(one(ch("105", 1), "", "555", "german-training", "AGI").reason, "trainer")
        self.assertEqual(one(ch("trunk-easybell", 1), "", "555", "easybell-in", "AGI").reason, "trainer")
        self.assertEqual(one("Local/555@german-training-0000a1;2", "", "555", "german-training", "AGI").reason,
                         "trainer")
        self.assertEqual(one("Local/x@y-0000a1;1", "", "9", "other", "Wait").reason, "local_first")
        self.assertEqual(one(ch("105", 1), "", "811", "conf-room", "ConfBridge").reason, "conference")
        self.assertEqual(one(ch("105", 1), "", "808", "mail", "VoiceMail").reason, "voicemail")
        self.assertEqual(one("PJSIP/105-1", "", "1", "x", "Hangup").reason, "other")  # not an 8-hex channel name
        busy = one(ch("105", 1), ch("trunk-russia", 2), "+7" + NUM[1:], "call-out", "Dial", "BUSY")
        self.assertEqual((busy.direction, busy.facts["rawStatus"], busy.facts["answeredAt"]), ("Outbound", "BUSY", None))

    def test_csv_only_calls_by_uniqueid_and_the_boundary(self):
        lines = [csv_line(NUM, "290001", "call-in", ch("trunk-russia", 1), ch("118", 2), "Dial", "2026-07-01 08:00:00",
                          "2026-07-01 08:00:10", "2026-07-01 08:01:00", 60, 50, "ANSWERED", "500.1"),
                 csv_line("105", "+7" + NUM2[1:], "call-out", ch("105", 3), ch("trunk-russia", 4), "Dial",
                          "2026-07-01 09:00:00", "", "2026-07-01 09:00:30", 30, 0, "NO ANSWER", "501.1"),
                 csv_line(NUM, "290001", "call-in", ch("trunk-russia", 5), "", "BackGround", "2026-09-30 11:59:50",
                          "2026-09-30 11:59:50", "2026-09-30 12:00:30", 40, 40, "ANSWERED", "502.1"),
                 ["broken", "line"]]
        plan = self.build([], lines)
        self.assertEqual([o.group.key for o in plan.ops], ["500.1", "501.1"])
        self.assertEqual([o.group.source for o in plan.ops], ["csv", "csv"])
        self.assertEqual((plan.lines[3], plan.lines[4]), ("after_t0", "invalid:csv_shape"))
        self.assertEqual(plan.ops[1].payload()["rawStatus"], "NOANSWER")

    def test_d31_matching_of_csv_only_recordings(self):
        """The local minute and the caller of the file name; ±1 minute; the callee breaks ties; ambiguity attaches none."""
        start = "2026-07-02 08:00:30"  # local 10:00
        lines = [csv_line(NUM, "290001", "call-in", ch("trunk-russia", 1), ch("118", 2), "Dial", start,
                          "2026-07-02 08:00:40", "2026-07-02 08:02:00", 90, 80, "ANSWERED", "600.1"),
                 csv_line(NUM2, "290001", "call-in", ch("trunk-russia", 3), ch("118", 4), "Dial", "2026-07-02 08:05:59",
                          "2026-07-02 08:06:10", "2026-07-02 08:07:00", 61, 50, "ANSWERED", "601.1"),
                 csv_line("106", "+7" + NUM[1:], "call-out", ch("106", 5), ch("trunk-russia", 6), "Dial",
                          "2026-07-02 08:10:00", "2026-07-02 08:10:05", "2026-07-02 08:11:00", 60, 55, "ANSWERED",
                          "602.1"),
                 csv_line("106", "+7" + NUM[1:], "call-out", ch("106", 7), ch("trunk-russia", 8), "Dial",
                          "2026-07-02 08:10:40", "2026-07-02 08:10:45", "2026-07-02 08:11:30", 50, 45, "ANSWERED",
                          "603.1")]
        exact = wav("2026-07-02", "10-00", NUM, "290001")
        plus_one = wav("2026-07-02", "10-07", NUM2, "290001")      # the call started 10:05:59 — no exact minute
        twins = wav("2026-07-02", "10-10", "106", "+7" + NUM[1:])  # two calls of one minute, same caller and callee
        stray = wav("2026-07-02", "11-30", "999", "1")
        empty = wav("2026-07-02", "10-05", NUM2, "290001")
        inventory = {exact: (9000, "b" * 64), plus_one: (9000, "c" * 64), twins: (9000, "d" * 64),
                     stray: (9000, "e" * 64), empty: (44, "f" * 64), "2026/07/02/notes.txt": (5, "0" * 64)}
        plan = self.build([], lines, inventory)
        by_key = {o.group.key: o for o in plan.ops}
        self.assertEqual(by_key["600.1"].recording["path"], exact)
        self.assertIsNone(by_key["601.1"].recording)  # ±1 found the header-only file of 10:05 first
        self.assertEqual(plan.files[empty], "without_audio")
        self.assertEqual(plan.files[plus_one], "no_match")
        self.assertEqual(plan.files[twins], "ambiguous")
        self.assertEqual((by_key["602.1"].group.recording_reason, by_key["603.1"].group.recording_reason),
                         ("ambiguous_d31", "ambiguous_d31"))
        self.assertEqual((plan.files[stray], plan.files["2026/07/02/notes.txt"]), ("no_match", "name_unparsed"))

    def test_recording_claims_and_absent_files(self):
        path = "/var/spool/asterisk/monitor/2026/09/05/x.wav"
        rows = [mysql(1, "700.1", "700.1", 1, "2026-09-05 10:00:00", 30, 20, "105", "+7" + NUM[1:], "call-out",
                      ch("105", 1), ch("trunk-russia", 2), "Dial", "ANSWERED", path),
                mysql(2, "701.1", "701.1", 1, "2026-09-05 10:00:40", 30, 20, "105", "+7" + NUM[1:], "call-out",
                      ch("105", 3), ch("trunk-russia", 4), "Dial", "ANSWERED", path),
                mysql(3, "702.1", "702.1", 1, "2026-09-05 11:00:00", 30, 20, "105", "+7" + NUM[1:], "call-out",
                      ch("105", 5), ch("trunk-russia", 6), "Dial", "ANSWERED",
                      "/var/spool/asterisk/monitor/2026/09/05/gone.wav"),
                mysql(4, "703.1", "703.1", 1, "2026-09-05 12:00:00", 30, 20, "105", "555", "german-training",
                      ch("105", 7), "", "AGI", "ANSWERED", "/var/spool/asterisk/monitor/2026/09/05/t.wav")]
        plan = self.build(rows, [], {"2026/09/05/x.wav": (100, "1" * 64), "2026/09/05/t.wav": (100, "2" * 64)})
        reasons = {o.group.key: (o.recording, o.group.recording_reason) for o in plan.ops}
        self.assertEqual(reasons["700.1"], (None, "claimed_twice"))  # the same file name in one minute: no owner
        self.assertEqual(reasons["701.1"], (None, "claimed_twice"))
        self.assertEqual(reasons["702.1"], (None, "missing_in_snapshot"))
        self.assertEqual(plan.files, {"2026/09/05/x.wav": "claimed_twice", "2026/09/05/t.wav": "no_call:trainer"})

    def test_d31_never_gives_a_mysql_call_file_to_another_call(self):
        """A MySQL call without recordingpath and a CSV-only call of the same minute, caller and callee: the file
        has no certain owner; a file only a MySQL call matches is not given by D-31; a file MySQL names whose name was
        built for a CSV-only call too was written twice."""
        rows = [mysql(1, "910.1", "910.1", 1, "2026-08-12 10:00:10", 30, 20, "106", "+7" + NUM[1:], "call-out",
                      ch("106", 1), ch("trunk-russia", 2), "Dial", "ANSWERED"),
                mysql(2, "911.1", "911.1", 1, "2026-08-12 11:00:00", 30, 20, "107", "+7" + NUM2[1:], "call-out",
                      ch("107", 3), ch("trunk-russia", 4), "Dial", "ANSWERED"),
                mysql(3, "912.1", "912.1", 1, "2026-08-12 12:00:00", 30, 20, "105", "+7" + NUM[1:], "call-out",
                      ch("105", 5), ch("trunk-russia", 6), "Dial", "ANSWERED",
                      "/var/spool/asterisk/monitor/" + wav("2026-08-12", "12-00", "105", "+7" + NUM[1:]))]
        lines = [csv_line("106", "+7" + NUM[1:], "call-out", ch("106", 7), ch("trunk-russia", 8), "Dial",
                          "2026-08-12 08:00:40", "2026-08-12 08:00:45", "2026-08-12 08:01:20", 40, 35, "ANSWERED", "920.1"),
                 csv_line("105", "+7" + NUM[1:], "call-out", ch("105", 9), ch("trunk-russia", 10), "Dial",
                          "2026-08-12 10:00:30", "2026-08-12 10:00:35", "2026-08-12 10:01:00", 30, 25, "ANSWERED", "921.1")]
        shared = wav("2026-08-12", "10-00", "106", "+7" + NUM[1:])
        mysql_only = wav("2026-08-12", "11-00", "107", "+7" + NUM2[1:])
        named = wav("2026-08-12", "12-00", "105", "+7" + NUM[1:])
        plan = self.build(rows, lines, {shared: (900, "1" * 64), mysql_only: (900, "2" * 64), named: (900, "3" * 64)})
        self.assertEqual(plan.files, {shared: "ambiguous", mysql_only: "mysql_call_without_path", named: "claimed_twice"})
        self.assertEqual({o.group.key: o.recording for o in plan.ops}, {k: None for k in ("910.1", "911.1", "912.1",
                                                                                        "920.1", "921.1")})

    def test_callee_of_a_recording_name(self):
        """The CDR callee against the To of a file name: the menu loses the DID, the dialplan rewrites numbers."""
        m = cdr.callee_matches
        self.assertTrue(m("+7" + NUM[1:], "+7" + NUM[1:]) and m("555", ""))
        self.assertTrue(m("t", "290001") and m("i", "290001") and m("s", "290001") and m("1", "290001"))
        self.assertTrue(m("8" + NUM[1:], "+7" + NUM[1:]))                  # 8… → +7…
        self.assertTrue(m("0" + NUM2[1:], "+" + NUM2[1:]))                  # 0… → +…
        self.assertTrue(m(NUM[-6:], "78352" + NUM[-6:]))                    # local XXXXXX → 78352XXXXXX
        self.assertFalse(m("+7" + NUM2[1:], "+7" + NUM[1:]) or m("118", "218") or m("290001", "290002"))

    def test_a_named_file_another_call_may_have_written(self):
        """External review 2026-10-17 (B1): every call that may have built the name of a file a MySQL row names is its
        owner too — a line after T0 whose callee the menu lost, a call that started the minute before; a call of the
        next minute or to another number is not."""
        day = "2026-09-30"
        inbound = lambda i, uid, local, src, path: mysql(  # noqa: E731
            i, uid, uid, 1, local, 40, 30, src, "t", "chose-client", ch("trunk-russia", i), ch("118", 50 + i), "Dial",
            "ANSWERED", "/var/spool/asterisk/monitor/" + path)
        after_t0 = wav(day, "13-59", NUM, "290001")
        later = wav(day, "10-30", NUM, "290001")
        before = wav(day, "11-00", NUM2, "290001")
        other = wav(day, "11-30", "105", "+7" + NUM[1:])
        rewritten = wav(day, "11-45", "106", "+7" + NUM[1:])
        rows = [inbound(1, "930.1", f"{day} 13:59:05", NUM, after_t0),
                inbound(2, "931.1", f"{day} 10:30:10", NUM, later),
                inbound(3, "932.1", f"{day} 11:00:20", NUM2, before),
                mysql(4, "933.1", "933.1", 1, f"{day} 11:30:10", 30, 20, "105", "+7" + NUM[1:], "call-out",
                      ch("105", 4), ch("trunk-russia", 5), "Dial", "ANSWERED", "/var/spool/asterisk/monitor/" + other),
                mysql(5, "934.1", "934.1", 1, f"{day} 11:45:10", 30, 20, "106", "+7" + NUM[1:], "call-out",
                      ch("106", 6), ch("trunk-russia", 7), "Dial", "ANSWERED",
                      "/var/spool/asterisk/monitor/" + rewritten)]
        menu = lambda src, start, end, uid: csv_line(  # noqa: E731
            src, "t", "chose-client", ch("trunk-russia", 90), ch("118", 91), "Dial", start, "", end, 30, 0,
            "NO ANSWER", uid)
        lines = [menu(NUM, f"{day} 11:59:40", f"{day} 12:00:30", "940.1"),    # ends after T0 (12:00 UTC)
                 menu(NUM, f"{day} 08:31:05", f"{day} 08:31:35", "941.1"),    # local 10:31:05: the next minute
                 menu(NUM2, f"{day} 08:59:50", f"{day} 09:00:20", "942.1"),   # local 10:59:50: the minute before
                 csv_line("105", "+7" + NUM2[1:], "call-out", ch("105", 92), ch("trunk-russia", 93), "Dial",
                          f"{day} 09:30:30", f"{day} 09:30:35", f"{day} 09:31:00", 30, 25, "ANSWERED", "943.1"),
                 csv_line("106", "8" + NUM[1:], "call-out", ch("106", 94), ch("trunk-russia", 95), "Dial",
                          f"{day} 09:45:30", f"{day} 09:45:35", f"{day} 09:46:00", 30, 25, "ANSWERED", "944.1")]
        inventory = {rel: (900, str(n) * 64) for n, rel in enumerate((after_t0, later, before, other, rewritten), 1)}
        plan = self.build(rows, lines, inventory)
        self.assertEqual(plan.lines[1], "after_t0")
        self.assertEqual(plan.files, {after_t0: "claimed_twice", later: "candidate", before: "claimed_twice",
                                      other: "candidate", rewritten: "claimed_twice"})
        by_key = {o.group.key: o for o in plan.ops}
        self.assertEqual({k: (o.recording or {}).get("path") for k, o in by_key.items()},
                         {"930.1": None, "931.1": later, "932.1": None, "933.1": other, "934.1": None,
                          "941.1": None, "942.1": None, "943.1": None, "944.1": None})
        self.assertEqual({k: by_key[k].group.recording_reason for k in ("930.1", "932.1", "942.1", "944.1")},
                         dict.fromkeys(("930.1", "932.1", "942.1", "944.1"), "claimed_twice"))

    def test_recording_owners_never_depend_on_the_order_of_files(self):
        """A CSV-only call that may have written a file MySQL names gets no other file either (it wrote one name)."""
        day = "2026-09-30"
        named = wav(day, "12-00", NUM, "290001")
        own = wav(day, "11-59", NUM, "290001")
        rows = [mysql(1, "950.1", "950.1", 1, f"{day} 12:00:10", 40, 30, NUM, "t", "chose-client",
                      ch("trunk-russia", 1), ch("118", 2), "Dial", "ANSWERED", "/var/spool/asterisk/monitor/" + named)]
        lines = [csv_line(NUM, "t", "chose-client", ch("trunk-russia", 3), ch("118", 4), "Dial", f"{day} 09:59:50",
                          f"{day} 09:59:55", f"{day} 10:00:40", 50, 45, "ANSWERED", "951.1")]
        for inventory in ({named: (900, "1" * 64), own: (900, "2" * 64)}, {own: (900, "2" * 64), named: (900, "1" * 64)}):
            plan = self.build(rows, lines, inventory)
            self.assertEqual(plan.files, {named: "claimed_twice", own: "ambiguous"})
            self.assertEqual({o.group.key: (o.recording, o.group.recording_reason) for o in plan.ops},
                             {"950.1": (None, "claimed_twice"), "951.1": (None, "claimed_twice")})

    def test_ambiguous_composite_key_is_never_a_call(self):
        line = csv_line(NUM, "290001", "call-in", ch("trunk-russia", 1), "", "BackGround", "2026-07-03 08:00:00",
                        "2026-07-03 08:00:00", "2026-07-03 08:00:10", 10, 10, "ANSWERED", "800.1")
        plan = self.build([], [line, line])
        self.assertEqual((plan.ops, plan.lines), ([], {1: "ambiguous_key", 2: "ambiguous_key"}))

    def test_rules_and_keys(self):
        with self.assertRaises(cdr.CdrError):
            cdr.Rules({"extensionPattern": "("})
        with self.assertRaises(cdr.CdrError):  # (uniqueid, sequence) of the sealed table must be unique
            self.build([mysql(i, "900.1", "900.1", 1, "2026-09-06 10:00:00", 5, 0, "1", "2", "c", ch("105", 1), "",
                              "Hangup", "ANSWERED") for i in (1, 2)])
        click = self.build([mysql(1, "crm-abc", "crm-abc", 1, "2026-09-06 10:00:00", 30, 20, "105", "+7" + NUM[1:],
                                  "call-out", ch("105", 1), ch("trunk-russia", 2), "Dial", "ANSWERED")])
        self.assertTrue(click.ops[0].payload()["clickToCall"])


class TransformsTest(unittest.TestCase):
    def test_pbx_dates_and_numbers(self):
        self.assertEqual(T.pbx_datetime("2020-10-22 23:30:00"), "2020-10-22 21:30:00")  # Berlin (connector)
        self.assertEqual(T.pbx_datetime("2020-10-23 00:30:00"), "2020-10-22 21:30:00")  # Moscow (Vtiger epochs)
        self.assertEqual(T.pbx_datetime("2026-07-01 10:00:00"), "2026-07-01 10:00:00")  # UTC epoch

    def test_canonical_phone_equals_the_php_core(self):
        """transforms.canonical_phone is a port of Core/PhoneNumbers::canonical: both answer the same."""
        d = "000" + "0001"  # synthetic digits built at run time: no phone-shaped literal in Git
        samples = [f"8 (999) {d[:3]}-{d[3:5]}-{d[5:]}", f"+7 999 {d[:3]} {d[3:5]} {d[5:]}", "0049" + "30" + d * 1,
                   "999" + d, "54" + "3210", "105", f"+7 999 {d} доб. 5", "abc", "", "+12", "495" + d,
                   "8352 " + "54" + "3210"]
        script = ("require $argv[1]; foreach (json_decode($argv[2]) as $s) "
                  "{ echo json_encode(Espo\\Modules\\Itvolga\\Tools\\Telephony\\Core\\PhoneNumbers::canonical($s, '8352')), "
                  "\"\\n\"; }")
        out = subprocess.run(["php", "-r", script, str(REPO / "tests/telephony/bootstrap.php"), json.dumps(samples)],
                             capture_output=True, text=True, check=True).stdout.splitlines()
        self.assertEqual([json.loads(x) for x in out], [T.canonical_phone(s, "8352") for s in samples])


class PlaceRecordingsTest(unittest.TestCase):
    """scripts/stand/place_recordings.py without root: a temporary root owned by this user (the helper's uid)."""

    def test_statuses_and_links(self):
        import hashlib
        import os
        import shutil
        import tempfile
        base = Path(tempfile.mkdtemp(prefix="vtplace-"))
        self.addCleanup(shutil.rmtree, base, True)
        state, source, outside = base / "state", base / "src", base / "outside"
        root = state / "monitor"
        for d in (root, source / "2001/01/02", source / "2001/01/03", outside):
            d.mkdir(parents=True)
        (state / ".marker").write_text("")
        files = {"2001/01/02/a.wav": b"RIFF-a", "2001/01/02/b.wav": b"RIFF-b", "2001/01/03/c.wav": b"RIFF-c"}
        for rel, data in files.items():
            (source / rel).write_bytes(data)
        (source / "2001/01/02/link.wav").symlink_to(source / "2001/01/02/a.wav")

        def run(items):
            lines = "".join(json.dumps({"i": i, "rel": rel.encode().hex(), "size": len(data),
                                        "sha256": hashlib.sha256(data).hexdigest()}) + "\n"
                            for i, (rel, data) in enumerate(items))
            out = subprocess.run([sys.executable, "-I", str(REPO / "scripts/stand/place_recordings.py"),
                                  "--source", str(source), "--root", str(root), "--uid", str(os.getuid()),
                                  "--gid", str(os.getgid()), "--marker", str(state / ".marker")],
                                 input=lines, capture_output=True, text=True, check=True).stdout.splitlines()
            return [json.loads(x).get("status") for x in out]

        a, b = ("2001/01/02/a.wav", files["2001/01/02/a.wav"]), ("2001/01/02/b.wav", files["2001/01/02/b.wav"])
        self.assertEqual(run([a, b]), ["placed", "placed"])
        self.assertEqual((root / a[0]).read_bytes(), a[1])
        self.assertEqual(run([a]), ["present"])
        (root / b[0]).write_bytes(b"other")
        self.assertEqual(run([b]), ["conflict"])
        self.assertEqual((root / b[0]).read_bytes(), b"other", "never replaced")
        self.assertEqual(run([("2001/01/02/a.wav", b"tampered")]), ["source_mismatch"])
        self.assertEqual(run([("2001/01/02/link.wav", b"RIFF-a"), ("../x.wav", b"x")]), ["unsafe", "unsafe"])
        (root / "2001/01/03").symlink_to(outside, target_is_directory=True)  # a day directory replaced by a link
        self.assertEqual(run([("2001/01/03/c.wav", files["2001/01/03/c.wav"])]), ["unsafe"])
        self.assertEqual(list(outside.iterdir()), [], "nothing written through the link")
        self.assertEqual([p.name for p in root.rglob("*.part")], [])

    def test_a_short_write_is_never_published(self):
        """External review 2026-10-17 (B3): a partial os.write is completed; bytes the part file does not hold (a write
        reported done) are found by reading it back — `error`, nothing published, no part file left."""
        import hashlib
        import os
        import shutil
        import tempfile
        from unittest import mock
        sys.path.insert(0, str(REPO / "scripts" / "stand"))
        import place_recordings as P
        base = Path(tempfile.mkdtemp(prefix="vtplace-"))
        self.addCleanup(shutil.rmtree, base, True)
        root, source = base / "monitor", base / "src"
        (source / "2001/01/04").mkdir(parents=True)
        root.mkdir()
        data = b"RIFF" + bytes(range(256)) * 8
        (source / "2001/01/04/d.wav").write_bytes(data)
        real = os.write

        def place(rel, write):
            item = {"rel": rel.encode().hex(), "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            rfd, sfd = os.open(root, P.DIR_FLAGS), os.open(source, P.DIR_FLAGS)
            try:
                with mock.patch.object(P.os, "write", write):
                    return P.place(item, sfd, rfd, os.getuid(), os.getgid())
            finally:
                os.close(rfd)
                os.close(sfd)

        (source / "2001/01/04/e.wav").write_bytes(data)
        self.assertEqual(place("2001/01/04/d.wav", lambda fd, b: real(fd, bytes(b[:7]))), "placed")
        self.assertEqual((root / "2001/01/04/d.wav").read_bytes(), data)
        self.assertEqual(place("2001/01/04/e.wav", lambda fd, b: real(fd, bytes(b[:-1])) + 1), "error")
        self.assertFalse((root / "2001/01/04/e.wav").exists())
        self.assertEqual([p.name for p in root.rglob("*.part")], [])


class ReportTest(unittest.TestCase):
    def test_periods_mark_the_gap(self):
        rows = history.periods({"2024-07": {"pbx": 3}, "2024-09": {}, "2026-06": {"csv_lines": 2}})
        months = {r["month"]: r for r in rows}
        self.assertEqual(rows[0]["month"], "2024-07")
        self.assertEqual(months["2024-08"]["note"], "D-16")
        self.assertEqual(months["2026-05"]["note"], "D-16")
        self.assertNotIn("note", months["2026-06"])
        self.assertEqual(len(rows), 24)

    def test_ledger_of_the_telephony_schema(self):
        counts = {"asteriskcdrdb": {"cdr": {"src": [9, None], "zzz": [1, None]}, "cel": {"x": [2, None]}}}
        census = {"CDR": {"cdr.src": (9, 9), "cdr.zzz": (1, 1)}}
        columns = [{"module": "CDR", "column": "cdr.src", "category": "rule", "verified": 9, "mismatch": 0,
                    "unaccounted": 0}]
        out = ledger.build(counts, [], census, {}, columns, None)
        rows = {(r["table"], r["column"]): r for r in out["rows"]}
        self.assertEqual((rows[("cdr", "src")]["cls"], rows[("cdr", "src")]["verified"]), ("import", 9))
        self.assertEqual(out["problems"], {"no_fate": ["asteriskcdrdb.cdr.zzz", "asteriskcdrdb.cel.x"]})
        self.assertFalse(any(r["cls"].startswith("pending") for r in out["rows"]))


if __name__ == "__main__":
    unittest.main()
