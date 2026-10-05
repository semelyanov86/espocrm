"""Stage 05.3 acceptance tests: scheduled mailing of reports (D-121…D-124, D-126) on the local stand, synthetic data.

The settings are never read back by the API nor matched by a filter (`internal`); an editor gets them as
`mailingSettings`, another reader only when the letters go; a save checks them (the time grid, «generate for» links,
recipients, the owner's export permission) and computes the next run in the owner's time zone like the preview does.
The job (forced by `run-job`) sends a mailing with the owner's rights as one letter per address with the same files,
«generate for» as one letter per found user with his own slice — skipping users without rights to the report's data,
without an address of their own, inactive ones — skips an empty report, records the outcome as codes and counts and
moves the next run; without SMTP the letters stay «Failed» with their files; a second or a parallel job sends nothing
again; the job never saves the report (its modification time stays).
"""
import subprocess
import time
import unittest
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from output import (JOB, REPO, SUM_ALL, D, Letters, World, all_of, cond, csv_rows, dec, download, due, espo_console,
                    hold_report_row, label, mail_fixture, ok, reference_data, run_job, runtime, sql)

S = {}
OWN = {"Invoice": {"create": "no", "read": "own", "edit": "no", "delete": "no"}, "Account": {"read": "all"},
       "InvoiceItem": {"read": "all"}, "Contact": {"read": "own"}}
STAND_ZONE = ZoneInfo("Europe/Moscow")


def mailing(**extra):
    return {"enabled": True, "frequency": "daily", "time": "09:00", "formats": ["csv"], **extra}


def setUpModule():
    world = World()
    letters = Letters(world)
    # Cleanups run in reverse: letters and files, then the world, then its notifications.
    unittest.addModuleCleanup(letters.purge_notifications)
    unittest.addModuleCleanup(world.cleanup)
    unittest.addModuleCleanup(letters.purge)
    S["w"] = world
    S["letters"] = letters
    for key in ("dir", "dir2", "leaving"):
        world.user(key, roles=["Директор"])
    own = world.role("own invoices", OWN)
    blind = world.role("no invoices", {"Account": {"read": "all"}})
    no_export = world.role("no export", OWN)
    sql(f"UPDATE role SET export_permission = 'no' WHERE id = '{no_export}'")
    team = world.team("получатели")
    world.user("own1", role_ids=[own])
    world.user("own2", role_ids=[own], teams=[team])
    world.user("blind", role_ids=[blind])
    world.user("twina", role_ids=[own])
    world.user("twinb", role_ids=[own])
    world.user("gone", role_ids=[own])
    world.user("noexp", role_ids=[no_export])
    world.user("sender", role_ids=[own])
    ok(world.admin.put(f"User/{world.uid['dir2']}", {"teamsIds": [team]}), "team of dir2")
    S["team"] = team
    S["addr"] = {key: letters.give_address(key) for key in ("dir", "dir2", "own1", "own2", "blind", "gone", "leaving",
                                                            "sender")}
    for key in ("twina", "twinb"):
        letters.give_address(key, "twin")
    S["ext"] = letters.address("external")
    S["ref"] = ref = reference_data(world)
    # Owners of the invoices for «generate for»: each found user gets his own slice.
    for invoice, owner in (("i1", "own1"), ("i2", "own1"), ("i3", "own2"), ("i4", "blind"), ("i5", "twina"),
                           ("i6", "gone")):
        ok(world.admin.put(f"Invoice/{ref[invoice]}", {"assignedUserId": world.uid[owner]}), "invoice owner")
    ok(world.admin.put(f"User/{world.uid['gone']}", {"isActive": False}), "inactive user")

    def report(owner, name, **extra):
        return world.report(owner, name, type="tabular", entityType="Invoice", columns=["name", "grandTotal"],
                            filters=all_of(world.name_filter()), rowLimit=None, **extra)

    S["owner"] = report("dir", "владельца", accessType="private", mailing=mailing(
        users=[world.uid["own1"]], teams=[team], emails=[S["ext"]], formats=["csv", "xlsx", "pdf"]))
    # A condition naming contacts: its text in a letter shows their names only to who may read them (D-124).
    contacts = {"type": "or", "items": [cond("contact", "in", [ref["c1"], ref["c2"]], attribute="contactId"),
                                        cond("contact", "isNull", attribute="contactId")]}
    S["generate"] = world.report("dir", "каждому", type="tabular", entityType="Invoice",
                                 columns=["name", "grandTotal"], rowLimit=None, accessType="public",
                                 filters=all_of(world.name_filter(), contacts),
                                 mailing=mailing(generateFor=["assignedUser"]))
    S["empty"] = report("dir", "пустой", accessType="public", mailing=mailing(emails=[S["ext"]], skipEmpty=True),
                        quickFilters=[])
    ok(world.admin.put(f"Report/{S['empty']['id']}",
                       {"filters": all_of(cond("name", "equals", f"{world.tag} нет такого"))}), "empty conditions")
    S["leaving"] = report("leaving", "уходящего", accessType="public", mailing=mailing(emails=[S["ext"]]))
    S["mine"] = world.report("dir", "мои счета", type="tabular", entityType="Invoice", columns=["name", "grandTotal"],
                             rowLimit=None, accessType="public",
                             filters=all_of(world.name_filter(),
                                            cond("assignedUser", "isCurrentUser", attribute="assignedUserId")),
                             mailing=mailing(generateFor=["assignedUser"]))
    S["parallel"] = report("dir", "параллельно", accessType="public", mailing=mailing(emails=[S["ext"]]))
    S["sending"] = report("dir", "отправка", accessType="private", mailing=mailing(users=[world.uid["own1"]],
                                                                                    generateFor=[]))


def W():
    return S["w"]


def L():
    return S["letters"]


class Case(unittest.TestCase):
    def refused(self, result, status, key=None):
        self.assertEqual(status, result[0], f"expected HTTP {status}, got {result[0]}: {result[1]}")
        if key:
            self.assertEqual(key, label(result))

    def letters_of(self, report_key):
        return L().read(S[report_key]["name"])


def local_slot(settings, now):
    """The next slot of the stand rules (D-121) computed independently: wall clock of Moscow, strictly after now."""
    h, m = map(int, settings["time"].split(":"))
    local = now.astimezone(STAND_ZONE)
    for days in range(0, 800):
        day = (local + timedelta(days=days)).date()
        freq = settings["frequency"]
        if freq in ("weekly", "biweekly") and day.isoweekday() != settings["weekday"]:
            continue
        if freq == "monthly":
            last = ((day.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)).day
            if day.day != min(settings["day"], last):
                continue
        if freq == "yearly":
            if day.month != settings["month"]:
                continue
            last = ((day.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)).day
            if day.day != min(settings["day"], last):
                continue
        slot = datetime(day.year, day.month, day.day, h, m, tzinfo=STAND_ZONE)
        if slot > now:
            return slot.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    raise AssertionError("no slot")


class SettingsTest(Case):
    def test_settings_are_private(self):
        own = ok(W().client("dir").get(f"Report/{S['owner']['id']}"))
        self.assertNotIn("mailing", own, "the stored part is never read back")
        settings = own["mailingSettings"]
        self.assertEqual([W().uid["own1"]], settings["users"])
        self.assertEqual([S["ext"]], settings["emails"])
        self.assertIn(W().uid["own1"], settings["names"]["users"])

        public = ok(W().client("own1").get(f"Report/{S['generate']['id']}"))
        self.assertEqual({"enabled", "frequency", "time", "weekday", "day", "month", "formats"},
                         set(public["mailingSettings"]))
        for key in ("mailing", "mailingLastResult", "mailingLastRunAt"):
            self.assertNotIn(key, public)
        self.refused(W().client("own1").get(f"Report/{S['owner']['id']}"), 403)

        for client in (W().client("own1"), W().admin):
            status, payload, _ = client.get("Report", **{"where[0][type]": "like", "where[0][attribute]": "mailing",
                                                         "where[0][value]": "%example%", "select": "id"})
            self.assertNotEqual(200, status, "no filter by the stored part")

        duplicate = ok(W().client("dir").request("POST", "Report/action/getDuplicateAttributes",
                                                 {"id": S["owner"]["id"]}))
        self.assertFalse({"mailing", "mailingNextRunAt", "mailingLastRunAt", "mailingLastResult"} & set(duplicate))

    def test_a_new_owner_does_not_inherit_a_mailing(self):
        """Only an administrator gives a report away; a mailing left as it was then stops — the new owner's rights are
        not lent to recipients chosen by the previous one — until it is switched on in the same or a later save."""
        rid = W().report("dir", "передача", entityType="Invoice", columns=["name"],
                         mailing=mailing(emails=[S["ext"]]))["id"]
        self.refused(W().client("dir").put(f"Report/{rid}", {"assignedUserId": W().uid["dir2"]}), 403)
        self.assertIsNotNone(runtime(rid)["next"])
        ok(W().admin.put(f"Report/{rid}", {"assignedUserId": W().uid["dir2"]}))
        self.assertIsNone(runtime(rid)["next"])
        self.assertFalse(ok(W().client("dir2").get(f"Report/{rid}"))["mailingSettings"]["enabled"])
        ok(W().admin.put(f"Report/{rid}", {"assignedUserId": W().uid["dir"], "mailing": mailing(emails=[S["ext"]])}))
        self.assertIsNotNone(runtime(rid)["next"])
        self.assertTrue(ok(W().client("dir").get(f"Report/{rid}"))["mailingSettings"]["enabled"])

    def test_a_report_given_away_during_a_save_is_not_saved(self):
        """The owner's save passes the access check, then waits for the row while an administrator gives the report
        away: under the lock the committed owner is not the user any more — 403, no mailing with the new owner's rights
        (external review 05.3 B1)."""
        rid = W().report("dir", "гонка владельца", entityType="Invoice", columns=["name"])["id"]
        holder = hold_report_row(rid, 3, f"UPDATE report SET assigned_user_id = '{W().uid['dir2']}' WHERE id = '{rid}'")
        try:
            result = W().client("dir").put(f"Report/{rid}", {"mailing": mailing(emails=[S["ext"]])})
        finally:
            self.assertEqual(0, holder.wait(timeout=60), holder.stderr.read())
        self.refused(result, 403)
        self.assertEqual([["NULL", "NULL"]], sql(f"SELECT mailing, mailing_next_run_at FROM report WHERE id = '{rid}'"))

    def test_refusals(self):
        dir_ = W().client("dir")
        rid = S["owner"]["id"]
        self.refused(dir_.put(f"Report/{rid}", {"mailing": mailing(time="09:10", emails=[S["ext"]])}), 400,
                     "badMailingTime")
        self.refused(dir_.put(f"Report/{rid}", {"mailing": mailing(generateFor=["status"])}), 400, "badGenerateFor")
        self.refused(dir_.put(f"Report/{rid}", {"mailing": mailing(generateFor=["assignedUser"],
                                                                   emails=[S["ext"]])}), 400,
                     "mailingGenerateForExclusive")
        self.refused(dir_.put(f"Report/{rid}", {"mailing": mailing(users=["synthnosuchuser"])}), 400,
                     "mailingUnknownRecipient")
        self.refused(dir_.put(f"Report/{rid}", {"mailing": mailing()}), 400, "mailingNoRecipients")
        self.refused(W().try_report("noexp", "без экспорта", entityType="Invoice", columns=["name"],
                                    mailing=mailing(emails=[S["ext"]])), 403, "mailingNeedsExport")
        # Writes of the runtime are ignored.
        ok(dir_.put(f"Report/{rid}", {"mailingNextRunAt": "2000-01-01 00:00:00", "mailingLastResult": {"x": 1}}))
        self.assertNotEqual("2000-01-01 00:00:00", runtime(rid)["next"])
        self.assertNotEqual({"x": 1}, runtime(rid)["result"])

    def test_next_run_of_every_frequency_and_the_preview(self):
        report = W().report("dir", "расписание", entityType="Invoice", columns=["name"])
        dir_ = W().client("dir")
        cases = [{"frequency": "daily", "time": "23:45"}, {"frequency": "weekly", "time": "06:15", "weekday": 3},
                 {"frequency": "biweekly", "time": "12:00", "weekday": 7},
                 {"frequency": "monthly", "time": "09:30", "day": 31},
                 {"frequency": "yearly", "time": "10:00", "month": 2, "day": 29}]
        for case in cases:
            with self.subTest(frequency=case["frequency"]):
                settings = mailing(emails=[S["ext"]], **case)
                before = datetime.now(timezone.utc)
                saved = ok(dir_.put(f"Report/{report['id']}", {"mailing": settings}))
                preview = ok(dir_.request("POST", "Report/mailingPreview", {"mailing": settings}))
                self.assertEqual(saved["mailingNextRunAt"], preview["nextRunAt"])
                self.assertEqual(local_slot(case, before), saved["mailingNextRunAt"])
                self.assertIn("Europe/Moscow", preview["text"])

        # A new subject keeps the slot (it may be an anchor of every two weeks, not the first slot after now);
        # switching off clears it; the preview of a refused setting says why.
        anchored = "2031-01-06 06:00:00"
        sql(f"UPDATE report SET mailing_next_run_at = '{anchored}' WHERE id = '{report['id']}'")
        ok(dir_.put(f"Report/{report['id']}", {"mailing": mailing(emails=[S["ext"]], subject="Итоги",
                                                                  **cases[-1])}))
        self.assertEqual(anchored, runtime(report["id"])["next"])
        ok(dir_.put(f"Report/{report['id']}", {"mailing": {**mailing(emails=[S["ext"]]), "enabled": False}}))
        self.assertIsNone(runtime(report["id"])["next"])
        refused = ok(dir_.request("POST", "Report/mailingPreview", {"mailing": mailing(time="7:00")}))
        self.assertIsNone(refused["nextRunAt"])
        self.assertTrue(refused["error"])
        self.refused(W().client("own1").request("POST", "Report/mailingPreview",
                                                {"mailing": mailing(), "assignedUserId": W().uid["dir"]}), 403)


class JobTest(Case):
    def test_owner_rights_one_letter_per_address(self):
        rid = S["owner"]["id"]
        modified = sql(f"SELECT modified_at FROM report WHERE id = '{rid}'")[0][0]
        due(rid)
        state = run_job(rid)
        self.assertEqual("failed", state["result"]["status"], state)
        self.assertEqual(4, state["result"]["letters"])
        self.assertEqual(4, state["result"]["noSmtp"], "no SMTP on the stand: the letters stay failed")
        self.assertGreater(state["next"], datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
        self.assertEqual(modified, sql(f"SELECT modified_at FROM report WHERE id = '{rid}'")[0][0],
                         "the job does not save the report")

        letters = self.letters_of("owner")
        self.assertEqual(4, len(letters))
        self.assertEqual({S["addr"]["own1"], S["addr"]["own2"], S["addr"]["dir2"], S["ext"]},
                         {letter["to"] for letter in letters}, "users, team members, the extra address; one each")
        name = S["owner"]["name"]
        for letter in letters:
            self.assertEqual("Failed", letter["status"])
            self.assertTrue(letter["name"].startswith(name + " — "), letter["name"])
            self.assertEqual({f"{name}.csv", f"{name}.xlsx", f"{name}.pdf"},
                             set(letter["attachmentsNames"].values()))
            self.assertIn(f"#Report/view/{rid}", letter["body"])
            self.assertIn("Условия", letter["body"])
        # The owner's data: every reference invoice (the director reads all).
        csv_id = next(i for i, n in letters[0]["attachmentsNames"].items() if n.endswith(".csv"))
        rows = csv_rows(download(W().admin, csv_id)[1])
        records = [r for r in rows[1:] if r and r[0].startswith(W().tag)]
        self.assertEqual(SUM_ALL, sum(dec(r[1]) for r in records))

        # Nothing more for the same slot.
        subprocess.run([str(REPO / "scripts/stand/espo.sh"), "run-job", JOB], check=True, capture_output=True)
        self.assertEqual(4, len(self.letters_of("owner")))

    def test_generate_for_each_user_his_slice(self):
        rid = S["generate"]["id"]
        due(rid)
        result = run_job(rid)["result"]
        self.assertEqual(3, result["letters"], result)
        self.assertEqual({"noRights": 1, "sharedEmail": 1, "inactive": 1}, result["skipped"])

        by_address = {letter["to"]: letter for letter in self.letters_of("generate")}
        self.assertEqual({S["addr"]["own1"], S["addr"]["own2"], S["addr"]["dir2"]}, set(by_address))
        expected = {"own1": (2, D("20500.50")), "own2": (1, D("10999.99")), "dir2": (7, SUM_ALL)}
        for key, (count, total) in expected.items():
            letter = by_address[S["addr"][key]]
            (attachment_id, file_name), = letter["attachmentsNames"].items()
            rows = csv_rows(download(W().admin, attachment_id)[1])
            records = [r for r in rows[1:] if r and r[0].startswith(W().tag)]
            self.assertEqual((count, total), (len(records), sum(dec(r[1]) for r in records)), key)
            created_by = sql(f"SELECT created_by_id FROM attachment WHERE id = '{attachment_id}'")[0][0]
            self.assertEqual(W().uid[key], created_by, "a slice is the recipient's file")
            self.assertEqual(200, download(W().client(key), attachment_id)[0], "the recipient downloads it")
            self.assertEqual(403, download(W().client("own1" if key != "own1" else "own2"), attachment_id)[0],
                             "another user does not")
            # The contacts of the conditions belong to the director: own users do not read them.
            contact = f"{W().tag} c1"
            if key == "dir2":
                self.assertIn(contact, letter["body"])
            else:
                self.assertNotIn(contact, letter["body"])
                self.assertIn("(нет доступа)", letter["body"])

    def test_generate_for_a_current_user_report(self):
        """«My invoices» for each responsible: the search ignores «current user» (it would be the owner), each run
        applies it to the recipient (D-122)."""
        rid = S["mine"]["id"]
        due(rid)
        result = run_job(rid)["result"]
        self.assertEqual(3, result["letters"], result)
        expected = {"own1": (2, D("20500.50")), "own2": (1, D("10999.99")), "dir2": (1, D("500"))}
        by_address = {letter["to"]: letter for letter in self.letters_of("mine")}
        self.assertEqual({S["addr"][k] for k in expected}, set(by_address))
        for key, (count, total) in expected.items():
            (attachment_id, _), = by_address[S["addr"][key]]["attachmentsNames"].items()
            records = [r for r in csv_rows(download(W().admin, attachment_id)[1])[1:] if r and r[0].startswith(W().tag)]
            self.assertEqual((count, total), (len(records), sum(dec(r[1]) for r in records)), key)

    def test_skip_an_empty_report(self):
        rid = S["empty"]["id"]
        due(rid)
        result = run_job(rid)["result"]
        self.assertEqual("skipped", result["status"])
        self.assertEqual({"empty": 1}, result["skipped"])
        self.assertEqual([], self.letters_of("empty"))

    def test_inactive_owner(self):
        rid = S["leaving"]["id"]
        ok(W().admin.put(f"User/{W().uid['leaving']}", {"isActive": False}))
        due(rid)
        state = run_job(rid)
        self.assertEqual({"status": "failed", "error": "ownerInactive"}, state["result"])
        self.assertNotEqual("2000-01-01 00:00:00", state["next"], "the slot moves on")
        self.assertEqual([], self.letters_of("leaving"))

    def test_parallel_jobs_send_once(self):
        rid = S["parallel"]["id"]
        due(rid)
        jobs = [subprocess.Popen([str(REPO / "scripts/stand/espo.sh"), "run-job", JOB], stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL) for _ in range(3)]
        for job in jobs:
            job.wait(timeout=180)
        run_job(rid)
        self.assertEqual(1, len(self.letters_of("parallel")))


class SenderTest(Case):
    """The send path with SMTP — a synthetic group account of the system address on a closed local port, so the send
    fails — and the system sender address owned by a user: that user is never linked to the report letters."""

    def setUp(self):
        self.saved = espo_console("config:get", "outboundEmailFromAddress").strip()
        self.account = mail_fixture({"createGroupAccount": {"name": f"{W().tag} отправка",
                                                           "emailAddress": S["addr"]["sender"],
                                                           "smtpHost": "127.0.0.1", "smtpPort": 1}})["id"]
        espo_console("config:set", "outboundEmailFromAddress", S["addr"]["sender"])
        time.sleep(3)

    def tearDown(self):
        if self.saved in ("", "null", "NULL"):
            espo_console("config:set", "outboundEmailFromAddress", "null", "--type=json")
        else:
            espo_console("config:set", "outboundEmailFromAddress", self.saved)
        mail_fixture({"groupAccounts": [self.account]})
        time.sleep(3)

    def test_the_sender_user_is_not_linked_to_letters(self):
        rid = S["sending"]["id"]
        due(rid)
        result = run_job(rid)["result"]
        self.assertEqual({"letters": 1, "failed": 1, "sent": 0, "noSmtp": 0},
                         {k: result[k] for k in ("letters", "failed", "sent", "noSmtp")}, result)
        ids = L().ids(S["sending"]["name"])
        self.assertEqual(1, len(ids))
        sender = W().uid["sender"]
        self.assertEqual([["Failed"]], sql(f"SELECT status FROM email WHERE id = '{ids[0]}'"))
        self.assertEqual([["0"]], sql(f"SELECT COUNT(*) FROM email_user WHERE email_id = '{ids[0]}' "
                                      f"AND user_id = '{sender}'"), "the owner of the sender address is not a user")
        self.assertEqual([["0"]], sql(f"SELECT COUNT(*) FROM entity_user WHERE entity_id = '{ids[0]}' "
                                      f"AND user_id = '{sender}'"))
        self.assertEqual("1", sql(f"SELECT COUNT(*) FROM email_user WHERE email_id = '{ids[0]}' "
                                  f"AND user_id = '{W().uid['own1']}'")[0][0], "the recipient is")


if __name__ == "__main__":
    unittest.main()
