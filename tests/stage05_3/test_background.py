"""Stage 05.3 acceptance tests: background export of a report result (D-125) on the local stand, synthetic data.

A queued export is made when the queue runs, with the rights the requester has then and the conditions of his
request: the file comes to him alone — a letter to his address with the file (created by him) and a notification with
the download link; without an address — the link only; when the access is gone by then — a notification of the
failure without the report's name and no file.
"""
import time
import unittest

from output import (SUM_ALL, Letters, World, all_of, cond, csv_rows, dec, download, export, label, ok,
                    reference_data, run_cron, sql)

S = {}


def setUpModule():
    world = World()
    letters = Letters(world)
    unittest.addModuleCleanup(letters.purge_notifications)
    unittest.addModuleCleanup(world.cleanup)
    unittest.addModuleCleanup(letters.purge)
    S["w"], S["letters"] = world, letters
    world.user("dir", roles=["Директор"])
    world.user("dir2", roles=["Директор"])
    world.user("plain", role_ids=[world.role("plain", {"Account": {"read": "all"}})])
    # Exports; reads contacts but not their names, and no user but himself.
    narrow = world.role("narrow", {"Invoice": {"read": "all"}, "Account": {"read": "all"}, "Contact": {"read": "all"},
                                   "User": {"read": "own", "edit": "own"}},
                        field_data={"Contact": {"name": {"read": "no", "edit": "no"}}})
    sql(f"UPDATE role SET export_permission = 'yes' WHERE id = '{narrow}'")
    world.user("narrow", role_ids=[narrow])
    S["addr"] = letters.give_address("dir")
    S["narrow"] = letters.give_address("narrow")
    S["ref"] = reference_data(world)
    S["report"] = world.report("dir", "в фоне", type="tabular", entityType="Invoice", columns=["name", "grandTotal"],
                               rowLimit=2, accessType="public", filters=all_of(world.name_filter()),
                               quickFilters=["status"])
    S["shared"] = world.report("dir2", "чужой", type="tabular", entityType="Invoice", columns=["name"],
                               accessType="public", filters=all_of(world.name_filter()))


def W():
    return S["w"]


def L():
    return S["letters"]


def wait_notifications(user_key, count, timeout=180):
    deadline = time.time() + timeout
    while True:
        found = L().notifications(user_key)
        if len(found) >= count:
            return found
        if time.time() > deadline:
            raise AssertionError(f"no notification for {user_key} within {timeout} s")
        run_cron()
        time.sleep(3)


class BackgroundTest(unittest.TestCase):
    def test_file_by_mail_and_notification(self):
        before = len(L().notifications("dir"))
        result = ok(export(W().client("dir"), S["report"]["id"], "csv", background=True, variant="all"))
        self.assertEqual({"scheduled": True}, result)
        message = wait_notifications("dir", before + 1)[-1]["message"]
        self.assertIn("?entryPoint=download&id=", message)
        attachment_id = message.split("?entryPoint=download&id=")[1].split(")")[0]

        letters = [letter for letter in L().read(S["report"]["name"]) if letter["to"] == S["addr"]]
        self.assertEqual(1, len(letters))
        self.assertEqual({attachment_id}, set(letters[0]["attachmentsIds"]))
        row = sql(f"SELECT role, parent_type, created_by_id FROM attachment WHERE id = '{attachment_id}'")[0]
        self.assertEqual(["Attachment", "Email", W().uid["dir"]], row)

        status, data, _ = download(W().client("dir"), attachment_id)
        self.assertEqual(200, status)
        records = [r for r in csv_rows(data)[1:] if r and r[0].startswith(W().tag)]
        self.assertEqual((7, SUM_ALL), (len(records), sum(dec(r[1]) for r in records)), "variant «all»")
        self.assertEqual(403, download(W().client("plain"), attachment_id)[0], "a user without the letter")
        # A role reading all e-mail reads the letter and its file (accepted by the owner, D-123).
        self.assertEqual(200, download(W().client("dir2"), attachment_id)[0])

    def test_one_off_conditions_and_no_address(self):
        before = len(L().notifications("dir2"))
        quick = [{"field": "status", "mode": "in", "values": ["Sent"], "includeEmpty": False}]
        ok(export(W().client("dir2"), S["report"]["id"], "csv", background=True, quickFilters=quick, variant="all"))
        message = wait_notifications("dir2", before + 1)[-1]["message"]
        attachment_id = message.split("?entryPoint=download&id=")[1].split(")")[0]
        self.assertEqual(["Export File", W().uid["dir2"]],
                         sql(f"SELECT role, created_by_id FROM attachment WHERE id = '{attachment_id}'")[0])
        status, data, _ = download(W().client("dir2"), attachment_id)
        records = [r for r in csv_rows(data)[1:] if r and r[0].startswith(W().tag)]
        self.assertEqual(2, len(records), "the quick filter of the request")

    def test_letter_names_only_what_the_requester_reads(self):
        """«Сведения об отчёте» in the letter name the owner and the records of the conditions only when the requester
        may read them and their name field (external review 05.3 B3, B4); the owner reading all sees them."""
        contact = ok(W().admin.get(f"Contact/{S['ref']['c1']}"))["name"]
        owner = ok(W().admin.get(f"User/{W().uid['dir']}"))["name"]
        report = W().report("dir", "сведения", type="tabular", entityType="Invoice", columns=["name"],
                            accessType="public", filters=all_of(W().name_filter(), cond(
                                "contact", "in", [S["ref"]["c1"]], attribute="contactId")))
        bodies = {}
        for key, address in (("dir", S["addr"]), ("narrow", S["narrow"])):
            before = len(L().notifications(key))
            ok(export(W().client(key), report["id"], "csv", background=True))
            wait_notifications(key, before + 1)
            letters = [letter for letter in L().read(report["name"]) if letter["to"] == address]
            self.assertEqual(1, len(letters), key)
            bodies[key] = letters[0]["body"]
        self.assertIn(contact, bodies["dir"])
        self.assertIn(owner, bodies["dir"])
        self.assertNotIn(contact, bodies["narrow"])
        self.assertNotIn(owner, bodies["narrow"])
        self.assertEqual(2, bodies["narrow"].count("(нет доступа)"), "the owner and the contact")

    def test_refused_when_the_access_is_gone(self):
        before = len(L().notifications("dir"))
        ok(export(W().client("dir"), S["shared"]["id"], "csv", background=True))
        ok(W().client("dir2").put(f"Report/{S['shared']['id']}", {"accessType": "private"}))
        message = wait_notifications("dir", before + 1)[-1]["message"]
        self.assertNotIn("entryPoint=download", message)
        self.assertNotIn(S["shared"]["name"], message)
        self.assertEqual([], L().read(S["shared"]["name"]))

    def test_refused_at_once(self):
        self.assertEqual("badExportFormat", label(export(W().client("dir"), S["report"]["id"], "doc",
                                                         background=True)))
        result = export(W().client("dir"), S["report"]["id"], "csv", background=True,
                        quickFilters=[{"field": "name", "values": ["x"]}])
        self.assertEqual(400, result[0], "conditions are checked before queueing")


if __name__ == "__main__":
    unittest.main()
