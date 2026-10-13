"""Stage 07.1 acceptance tests: the live telephony on the stand with the isolated test PBX (task telephony:up).

Calls are real SIP calls between the three containers of the test PBX; the listener (systemd unit) writes the CRM.
Synthetic users with the test extensions, synthetic clients and numbers; cleanup by the ids of this run (harness.Run).
The tests run in order (test_NN_…): the inbound call of test_01 is the subject of the access tests that follow.
"""
import subprocess
import time
import unittest

from harness import (REPO, MONITOR, Client, Run, ast, desk, inbound, last_provider_call, must, phone, probe, provider,
                     reset_pbx, setup_check, sql, wait, wait_idle)

R = None
STATE = {}


def setUpModule():
    global R
    R = Run()
    unittest.addModuleCleanup(R.cleanup)
    t1, t2 = R.team("T1"), R.team("T2")
    STATE["teams"] = (t1, t2)
    # Desk phones of the test PBX → users with different roles (D-39 roles of the stand).
    R.user("u111", roles=["Директор"], teams=[t1], extension="111")
    R.user("u116", roles=["Менеджер по продажам"], teams=[t2], extension="116")
    R.user("u118", roles=["Менеджер по продажам"], teams=[t2], extension="118")
    R.user("u218", roles=["Заместитель директора"], teams=[t1], extension="218")
    R.user("u119", roles=["Директор"], teams=[t1], extension="119")
    R.user("mate", roles=["Менеджер по продажам"], teams=[t1])
    R.user("outsider", roles=["Менеджер по продажам"], teams=[t2])
    R.user("director", roles=["Директор"], teams=[t2])
    no_rec = R.role("no-recording", {"Call": {"create": "yes", "read": "all", "edit": "no", "delete": "no"}},
                    {"Call": {"cRecording": {"read": "no", "edit": "no"}}})
    R.user("norec", role_ids=[no_rec], teams=[t2])
    R.user("noext", roles=["Директор"], teams=[t1])
    # Clients of the main number: an account with its contact, and a lead with the same number.
    account = R.create("Account", {"name": f"{R.tag} Клиент", "assignedUserId": R.uid["u218"], "teamsIds": [t1]})
    contact = R.create("Contact", {"lastName": f"{R.tag} Контакт", "accountId": account,
                                   "phoneNumber": R.canonical(1), "assignedUserId": R.uid["u218"], "teamsIds": [t1]})
    lead = R.create("Lead", {"lastName": f"{R.tag} Лид", "phoneNumber": R.canonical(1),
                             "assignedUserId": R.uid["u118"], "teamsIds": [t2]})
    # A lead whose stored value is not one number: only a «possible» match for number 2.
    possible = R.create("Lead", {"lastName": f"{R.tag} Возможный", "assignedUserId": R.uid["u118"], "teamsIds": [t2]})
    # The API normalises a phone value; a raw «… доб. 5» exists only from the Vtiger import — stored the same way.
    assert probe({"phone": {"entityType": "Lead", "id": possible,
                            "value": f"+7 {R.number(2)[1:4]} {R.number(2)[4:]} доб. 5"}})["ok"]
    STATE.update(account=account, contact=contact, lead=lead, possible=possible)
    reset_pbx()


class TelephonyTest(unittest.TestCase):
    maxDiff = None

    # --- inbound ---------------------------------------------------------------------------------------------------

    def test_01_inbound_answered_by_second_phone(self):
        """108 → 208 in production: 118 does not answer, 218 answers. Cards follow the ringing; the Call is stored."""
        phone("118", "noanswer")
        phone("218", "answer,1,4")
        inbound(R.number(1), 40)

        ringing = wait(lambda: [c for c in R.cards("u118") if c["data"]["state"] == "ringing"], 30, "118 ringing")[0]
        self.assertEqual("Inbound", ringing["data"]["direction"])
        self.assertEqual(R.canonical(1), ringing["data"]["number"])
        clients = {(c["entityType"], c["id"]) for c in ringing["data"]["clients"]}
        self.assertEqual({("Lead", STATE["lead"])}, clients, "a sales manager sees the lead, not the contact")
        self.assertIsNotNone(ringing["data"]["call"], "the ringing user is a participant and may open the call")
        self.assertEqual([], R.cards("u218"), "218 does not ring yet")
        self.assertEqual([], R.cards("outsider"))

        talking = wait(lambda: [c for c in R.cards("u218") if c["data"]["state"] == "talking"], 30, "218 talking")[0]
        clients = {(c["entityType"], c["id"]): c for c in talking["data"]["clients"]}
        self.assertEqual({("Contact", STATE["contact"])}, set(clients), "the deputy sees the contact, not the lead")
        self.assertEqual(f"{R.tag} Клиент", clients[("Contact", STATE["contact"])]["accountName"])
        closed = [c for c in R.cards("u118") if c["id"] == ringing["id"]]
        self.assertEqual("closed", closed[0]["data"]["state"] if closed else "closed")

        call = R.final_call(1)
        STATE["call"] = call["id"]
        self.assertEqual(("Inbound", "Held", "ended", "ANSWER"),
                         (call["direction"], call["status"], call["c_live_state"], call["c_call_status_raw"]))
        self.assertEqual("218", call["c_extension"])
        self.assertEqual(R.uid["u218"], call["assigned_user_id"])
        self.assertEqual(LINE_DID, call["c_incoming_line"])
        self.assertIn(int(call["c_bill_duration"]), range(3, 7))
        self.assertGreaterEqual(int(call["length"]), int(call["c_bill_duration"]))
        self.assertEqual(("Account", STATE["account"]), (call["parent_type"], call["parent_id"]))
        self.assertEqual([STATE["contact"]], R.related("call_contact", call["id"], "contact_id"))
        self.assertEqual([STATE["lead"]], R.related("call_lead", call["id"], "lead_id"))
        self.assertEqual(sorted([R.uid["u118"], R.uid["u218"]]), R.related("call_user", call["id"], "user_id"))
        self.assertEqual("1", call["c_recording"])
        self.assertTrue(call["c_recording_path"].endswith(".wav"))
        teams = [r[0] for r in sql(f"SELECT team_id FROM entity_team WHERE entity_type = 'Call' "
                                   f"AND entity_id = '{call['id']}' AND deleted = 0")]
        self.assertEqual([STATE["teams"][0]], teams, "the team of the assignee")
        linked = sql(f"SELECT COUNT(*) FROM `call` WHERE c_asterisk_linked_id = '{call['c_asterisk_linked_id']}'")
        self.assertEqual("1", linked[0][0])
        wait_idle()

    def test_02_card_dismissed_on_the_server(self):
        card = wait(lambda: [c for c in R.cards("u218") if c["data"]["state"] == "ended"], 15, "ended card")[0]
        self.assertEqual(STATE["call"], card["data"]["call"]["id"])
        self.assertEqual(404, R.clients["outsider"].post(f"Telephony/cards/{card['id']}/dismiss", {})[0],
                         "a card of another user")
        must(R.clients["u218"].post(f"Telephony/cards/{card['id']}/dismiss", {}), "dismiss")
        self.assertEqual([], [c for c in R.cards("u218") if c["id"] == card["id"]])

    def test_03_missed_call_is_assigned_to_the_first_phone_that_rang(self):
        phone("118", "noanswer")
        inbound(R.number(3), 7)
        call = R.final_call(3)
        self.assertEqual(("Not Held", "CANCEL"), (call["status"], call["c_call_status_raw"]))
        self.assertEqual(R.uid["u118"], call["assigned_user_id"])
        self.assertEqual("0", call["c_bill_duration"])
        wait_idle()

    def test_04_hang_up_in_the_voice_menu_goes_to_the_fallback_extension(self):
        inbound(R.number(4), 1)
        call = R.final_call(4)
        self.assertEqual(("Not Held", "NODIAL"), (call["status"], call["c_call_status_raw"]))
        self.assertEqual(R.uid["u119"], call["assigned_user_id"], "fallback extension 119")
        self.assertEqual([], R.cards("u119"), "no phone rang: no cards")
        wait_idle()

    def test_05_possible_match_is_shown_but_not_linked(self):
        phone("118", "noanswer")
        inbound(R.number(2), 6)
        card = wait(lambda: [c for c in R.cards("u118") if c["data"]["number"] == R.canonical(2)], 30, "card")[0]
        self.assertEqual([(STATE["possible"], True)],
                         [(c["id"], c["possible"]) for c in card["data"]["clients"]])
        call = R.final_call(2)
        self.assertEqual([], R.related("call_lead", call["id"], "lead_id"))
        self.assertIn(call["parent_id"], ("NULL", ""), "a possible match is never the parent")
        wait_idle()

    # --- outbound --------------------------------------------------------------------------------------------------

    def test_06_outbound_from_desk_phone(self):
        provider(R.canonical(5), "answer,1,3")
        desk("111", "8" + R.number(5)[1:], 20)
        call = R.final_call(5)
        self.assertEqual(("Outbound", "Held", "ANSWER"), (call["direction"], call["status"], call["c_call_status_raw"]))
        self.assertEqual(R.uid["u111"], call["assigned_user_id"])
        self.assertEqual("0", call["c_click_to_call"])
        self.assertEqual(("nedost", R.canonical(5)), last_provider_call(), "the dialplan route of 111")
        wait_idle()

        provider(R.canonical(6), "busy")
        desk("116", R.canonical(6), 20)
        call = R.final_call(6)
        self.assertEqual(("Not Held", "BUSY"), (call["status"], call["c_call_status_raw"]))
        self.assertEqual(R.uid["u116"], call["assigned_user_id"])
        wait_idle()

    def test_07_internal_and_service_calls_are_not_stored(self):
        time.sleep(1.5)  # created_at has whole seconds: the previous call may end in the second of the mark
        mark = sql("SELECT UTC_TIMESTAMP()")[0][0]
        phone("116", "answer,1,2")
        desk("111", "116", 3)
        wait_idle()
        desk("111", "811", 2)
        wait_idle()
        count = sql(f"SELECT COUNT(*) FROM `call` WHERE c_asterisk_linked_id IS NOT NULL AND created_at > '{mark}'")
        self.assertEqual("0", count[0][0])

    # --- click-to-call ---------------------------------------------------------------------------------------------

    def test_08_click_to_call_takes_the_route_of_a_manual_call(self):
        # A director calls from the contact, a sales manager (no access to contacts) from the lead.
        for ext, n, route, parent in (("111", 7, "nedost", "contact"), ("116", 8, "russia", "lead")):
            phone(ext, "answer,1,8")
            provider(R.canonical(n), "answer,1,2")
            result = must(R.clients[f"u{ext}"].post("Telephony/dial", {
                "phoneNumber": f"+7 ({R.number(n)[1:4]}) {R.number(n)[4:7]}-{R.number(n)[7:9]}-{R.number(n)[9:]}",
                "entityType": parent.capitalize(), "entityId": STATE[parent]}), "dial")
            self.assertEqual(ext, result["extension"])
            card = wait(lambda: [c for c in R.cards(f"u{ext}") if c["data"]["viaCrm"]
                                 and c["data"]["state"] in ("dialing", "talking")], 20, "click-to-call card")[0]
            self.assertEqual("Outbound", card["data"]["direction"])
            call = R.final_call(n)
            self.assertEqual(("1", "Held"), (call["c_click_to_call"], call["status"]))
            self.assertTrue(call["c_asterisk_linked_id"].startswith("crm-"))
            self.assertEqual((parent.capitalize(), STATE[parent]), (call["parent_type"], call["parent_id"]),
                             "the record the user called from")
            crm_route = last_provider_call()
            self.assertEqual((route, R.canonical(n)), crm_route)
            wait_idle()
            reset_pbx()
            provider(R.canonical(n), "answer,1,1")
            desk(ext, R.canonical(n), 4)
            wait(lambda: last_provider_call()[0] is not None, 30, "manual call")
            self.assertEqual(crm_route, last_provider_call(), f"manual call from {ext} takes the same route")
            wait_idle()
            time.sleep(5)  # one click-to-call per user every 5 s

    def test_09_click_to_call_refusals(self):
        """Refused requests; a record the user may not read is not kept as the parent."""
        def dial(key, number, **extra):
            client = R.admin if key == "admin" else R.clients[key]
            return client.post("Telephony/dial", {"phoneNumber": number, **extra})[0]

        self.assertEqual(403, dial("noext", R.canonical(9)), "no extension")
        self.assertEqual(400, dial("u218", f"{R.canonical(9)} доб. 12"), "number with an extension")
        self.assertEqual(400, dial("u218", "123"))
        self.assertEqual(400, dial("u218", f"{R.canonical(9)}\r\nAction: Command"))
        anonymous = Client("synth-nobody", "wrong-password-Aa1!")
        self.assertEqual(401, anonymous.post("Telephony/dial", {"phoneNumber": R.canonical(9)})[0])
        phone("218", "busy")
        self.assertEqual(200, dial("u218", R.canonical(9)))
        self.assertEqual(403, dial("u218", R.canonical(9)), "one request per 5 s")
        # The desk phone is busy: no external dial, no Call; the card closes, the request is unanswered.
        time.sleep(8)
        wait_idle()
        self.assertEqual([], [r for r in R.call_rows() if r["c_phone_number"] == R.canonical(9)])
        intent = sql(f"SELECT status FROM telephony_call_intent WHERE user_id = '{R.uid['u218']}' "
                     f"ORDER BY created_at DESC LIMIT 1")
        self.assertEqual("unanswered", intent[0][0])
        self.assertEqual([], [c for c in R.cards("u218") if c["data"]["state"] in ("dialing", "talking")])

        # A record the caller may not read is not kept: a sales manager has no access to contacts.
        phone("116", "busy")
        self.assertEqual(200, R.clients["u116"].post("Telephony/dial", {
            "phoneNumber": R.canonical(12), "entityType": "Contact", "entityId": STATE["contact"]})[0])
        intent = sql(f"SELECT IFNULL(parent_type, '-'), IFNULL(parent_id, '-') FROM telephony_call_intent "
                     f"WHERE user_id = '{R.uid['u116']}' ORDER BY created_at DESC LIMIT 1")
        self.assertEqual(["-", "-"], intent[0])
        time.sleep(3)
        wait_idle()

    # --- recordings ------------------------------------------------------------------------------------------------

    def test_10_recording_access_matrix(self):
        call_id = STATE["call"]
        expected = {"u218": 200, "u118": 200, "mate": 200, "director": 200, "outsider": 403, "norec": 403}

        for key, status in expected.items():
            got, body, headers = R.clients[key].entry_point("itvolgaRecording", id=call_id)
            self.assertEqual(status, got, key)
            if status == 200:
                self.assertEqual("audio/wav", headers.get("Content-Type"))
                self.assertTrue(body.startswith(b"RIFF"), key)
                self.assertIn("no-store", headers.get("Cache-Control", ""))
                self.assertEqual("nosniff", headers.get("X-Content-Type-Options"))

        self.assertEqual(200, R.admin.entry_point("itvolgaRecording", id=call_id)[0])
        anonymous = Client("synth-nobody", "wrong-password-Aa1!")
        self.assertEqual(401, anonymous.entry_point("itvolgaRecording", id=call_id)[0])
        self.assertEqual(404, R.clients["u218"].entry_point("itvolgaRecording", id="nosuchcall000001")[0])

    def test_11_recording_ranges_and_log(self):
        call_id = STATE["call"]
        client = R.clients["u218"]
        status, body, headers = client._send(
            f"{_site()}/?entryPoint=itvolgaRecording&id={call_id}", "GET", None, {"Range": "bytes=100-199"})
        self.assertEqual(206, status)
        self.assertEqual(100, len(body))
        self.assertTrue(headers.get("Content-Range", "").startswith("bytes 100-199/"))
        status, _, headers = client._send(
            f"{_site()}/?entryPoint=itvolgaRecording&id={call_id}", "GET", None, {"Range": "bytes=999999999-"})
        self.assertEqual(416, status)
        self.assertTrue(headers.get("Content-Range", "").startswith("bytes */"))

        logged = sql(f"SELECT user_id, COUNT(*) FROM action_history_record WHERE action = 'listen' "
                     f"AND target_type = 'Call' AND target_id = '{call_id}' GROUP BY user_id")
        counts = dict((u, int(c)) for u, c in logged)
        for key in ("u218", "u118", "mate", "director"):
            self.assertEqual(1, counts.get(R.uid[key]), f"one playback logged for {key} (repeats within 10 min)")
        self.assertNotIn(R.uid["outsider"], counts)
        self.assertNotIn(R.uid["norec"], counts)

    def test_12_recording_path_is_never_served_outside_the_root(self):
        call_id = STATE["call"]
        original = sql(f"SELECT c_recording_path FROM `call` WHERE id = '{call_id}'")[0][0]
        day = "/".join(original.split("/")[:3])
        link = MONITOR / day / f"synth-{R.run_id}.wav"
        subprocess.run(["sudo", "-n", "ln", "-sf", "/etc/hostname", str(link)], check=True)
        try:
            for path in ("../../../../etc/hostname", f"{day}/synth-{R.run_id}.wav", f"{day}/missing-{R.run_id}.wav"):
                sql(f"UPDATE `call` SET c_recording_path = '{path}' WHERE id = '{call_id}'")
                self.assertEqual(404, R.clients["u218"].entry_point("itvolgaRecording", id=call_id)[0], path)
            sql(f"UPDATE `call` SET c_recording_path = '{original}', c_live_state = 'talking' WHERE id = '{call_id}'")
            self.assertEqual(404, R.clients["u218"].entry_point("itvolgaRecording", id=call_id)[0],
                             "no playback of a call in progress")
        finally:
            sql(f"UPDATE `call` SET c_recording_path = '{original}', c_live_state = 'ended' WHERE id = '{call_id}'")
            subprocess.run(["sudo", "-n", "rm", "-f", str(link)], check=False)
        self.assertEqual(200, R.clients["u218"].entry_point("itvolgaRecording", id=call_id)[0])

    def test_13_api_never_shows_the_recording_path(self):
        call = must(R.admin.get(f"Call/{STATE['call']}"), "call")
        self.assertNotIn("cRecordingPath", call)
        self.assertTrue(call["cRecording"])
        listed = must(R.admin.get("Call", select="id,cRecordingPath", **{
            "where[0][type]": "equals", "where[0][attribute]": "id", "where[0][value]": STATE["call"]}), "list")["list"]
        self.assertEqual([STATE["call"]], [c["id"] for c in listed])
        self.assertNotIn("cRecordingPath", listed[0])
        self.assertNotIn("cRecording", must(R.clients["norec"].get(f"Call/{STATE['call']}"), "norec call"),
                         "a role without the field does not get it")

    # --- facts and guards ------------------------------------------------------------------------------------------

    def test_14_facts_are_closed(self):
        call_id = STATE["call"]
        before = must(R.admin.get(f"Call/{call_id}"), "call")
        must(R.clients["u218"].put(f"Call/{call_id}", {
            "name": f"{R.tag} переименован", "description": "заметка", "status": "Planned", "direction": "Outbound",
            "dateStart": "2020-01-01 00:00:00", "dateEnd": "2020-01-01 00:10:00", "cBillDuration": 1}), "edit")
        after = must(R.admin.get(f"Call/{call_id}"), "call")
        self.assertEqual(f"{R.tag} переименован", after["name"])
        self.assertEqual("заметка", after["description"])
        for field in ("status", "direction", "dateStart", "dateEnd", "cBillDuration", "cPhoneNumber"):
            self.assertEqual(before[field], after[field], field)

        R.admin.post("MassAction", {"entityType": "Call", "action": "update",
                                   "params": {"ids": [call_id]}, "data": {"status": "Planned"}})
        self.assertEqual(before["status"], must(R.admin.get(f"Call/{call_id}"), "call")["status"], "mass update")

        answer = probe({"guard": call_id})
        self.assertEqual(("Forbidden", "Forbidden", "Forbidden", before["status"]),
                         (answer["plain"], answer["import"], answer["create"], answer["statusAfter"]))

        self.assertEqual(403, R.clients["director"].delete(f"Call/{call_id}")[0], "only administrators delete")

    def test_15_extension_is_set_by_administrators_only_and_unique(self):
        client = R.clients["u116"]
        client.put(f"User/{R.uid['u116']}", {"cPhoneExtension": "218"})
        self.assertEqual("116", must(R.admin.get(f"User/{R.uid['u116']}"), "user")["cPhoneExtension"])
        status = R.admin.put(f"User/{R.uid['mate']}", {"cPhoneExtension": "218"})[0]
        self.assertEqual(409, status, "two active users never share an extension")
        self.assertEqual(400, R.admin.put(f"User/{R.uid['mate']}", {"cPhoneExtension": "1x"})[0])

    # --- AMI and the listener --------------------------------------------------------------------------------------

    def test_16_ami_rights_and_isolation(self):
        check = setup_check()
        self.assertEqual(0, check.returncode, check.stdout)
        self.assertIn("listener.Originate: denied", check.stdout)
        self.assertIn("dialer.Command: denied", check.stdout)
        reach = subprocess.run(["docker", "exec", "itvolga-espo-telephony-pstn-1", "bash", "-c",
                                "exec 3<>/dev/tcp/pbx/5038"], capture_output=True, text=True)
        self.assertNotEqual(0, reach.returncode, "the AMI listens on the PBX loopback only")
        published = subprocess.run(["docker", "port", "itvolga-espo-telephony-pbx-1"], capture_output=True, text=True)
        self.assertEqual("", published.stdout.strip(), "no port of the PBX is published")

    def test_17_listener_restart_during_a_call(self):
        phone("118", "answer,1,15")
        inbound(R.number(10), 40)
        wait(lambda: [c for c in R.cards("u118") if c["data"]["state"] == "talking"], 30, "talking")
        subprocess.run(["sudo", "-n", "systemctl", "restart", "itvolga-espo-telephony"], check=True)
        call = R.final_call(10, timeout=60)
        self.assertEqual(("ended", "Held", "ANSWER"), (call["c_live_state"], call["status"], call["c_call_status_raw"]))
        self.assertIn(int(call["c_bill_duration"]), range(13, 19))
        wait_idle()

    def test_18_call_that_ended_while_the_listener_was_down(self):
        phone("118", "answer,1,4")
        inbound(R.number(11), 30)
        wait(lambda: [c for c in R.cards("u118") if c["data"]["state"] == "talking"], 30, "talking")
        subprocess.run(["sudo", "-n", "systemctl", "stop", "itvolga-espo-telephony"], check=True)
        try:
            wait_idle(60)
        finally:
            subprocess.run(["sudo", "-n", "systemctl", "start", "itvolga-espo-telephony"], check=True)
        call = R.final_call(11, timeout=60)
        self.assertEqual(("lost", "Held", "ANSWER"), (call["c_live_state"], call["status"], call["c_call_status_raw"]))
        wait(lambda: R.cards("u118") is not None, 5, "cards")
        self.assertEqual([], [c for c in R.cards("u118") if c["data"]["state"] in ("ringing", "talking")],
                         "no card stays «talking»")


    def test_19_a_phone_without_a_crm_user_is_skipped(self):
        """The first phone that rang has no active user: the next phone that rang gets the missed call."""
        must(R.admin.put(f"User/{R.uid['u118']}", {"isActive": False}), "deactivate 118")
        try:
            phone("118", "noanswer")
            phone("218", "noanswer")
            inbound(R.number(13), 12)
            call = R.final_call(13)
            self.assertEqual(("Not Held", "CANCEL"), (call["status"], call["c_call_status_raw"]))
            self.assertEqual(R.uid["u218"], call["assigned_user_id"])
            self.assertEqual("218", call["c_extension"])
        finally:
            must(R.admin.put(f"User/{R.uid['u118']}", {"isActive": True}), "reactivate 118")
            wait_idle()

    def test_20_the_fallback_setting_applies_without_a_restart(self):
        must(R.admin.put("Settings", {"itvolgaTelephonyFallbackExtension": "218"}), "fallback 218")
        try:
            time.sleep(17)  # the listener re-reads the settings every 15 s
            inbound(R.number(14), 1)
            call = R.final_call(14)
            self.assertEqual(("NODIAL", R.uid["u218"]), (call["c_call_status_raw"], call["assigned_user_id"]))
        finally:
            must(R.admin.put("Settings", {"itvolgaTelephonyFallbackExtension": "119"}), "fallback 119")
            wait_idle()

LINE_DID = "290001"


def _site():
    from espo import BASE
    return BASE


if __name__ == "__main__":
    unittest.main()
