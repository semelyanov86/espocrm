#!/usr/bin/env python3
"""Synthetic fixture for the stage-05.3 browser check (export, print, mailing; Playwriter, evidence.md).

  python3 tests/stage05_3/ui_fixture.py create   → the users and records of the stage-05.1 fixture, e-mail addresses of
                                                   the managers, reports of every type and reports with mailings;
                                                   passwords → <private>/ui-users.env (600)
  python3 tests/stage05_3/ui_fixture.py delete   → removes the letters, files and notifications of the fixture, its
                                                   reports, records, team and users (export in the browser as a fixture
                                                   user: files of other users, the admin too, are not touched)

<private> is /data/itvolga/espo-private/stand/evidence/stage05.3 (UI_FIXTURE_DIR overrides it), mode 700. Users are
those of tests/stage05_1/ui_fixture.py: synth-rep-manager and -manager2 (Директор, export allowed; addresses
synth-rep-manager…@example.com), synth-rep-access, synth-rep-deputy, and synth-rep-noexport (a role reading invoices
and reports without the export permission). Reports of
the manager (public): «SYNTH-REP Счета список» (tabular, totals), «SYNTH-REP Счета по статусам» (summaries),
«SYNTH-REP Счета статус × месяц» (matrix), «SYNTH-REP Рассылка» (a weekly mailing to manager2 and an extra address,
CSV + XLSX + PDF), «SYNTH-REP Каждому» (my invoices: responsible = current user, generate for the responsible), «SYNTH-REP Пустой» (no records, skip
an empty report). Only ids and counts are printed.
"""
import json
import os
import secrets
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("UI_FIXTURE_DIR", "/data/itvolga/espo-private/stand/evidence/stage05.3")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "stage05_1"))
import ui_fixture as base  # noqa: E402
from fixture import Client, admin_credentials, sql  # noqa: E402

TAG = base.TAG
REPO = Path(__file__).resolve().parents[2]
ADDRESSES = {"manager": "synth-rep-manager@example.com", "manager2": "synth-rep-manager2@example.com"}
EXTRA = "synth-rep-extra@example.com"


def name_filter():
    return {"type": "and", "items": [{"field": "name", "where": {"type": "startsWith", "attribute": "name",
                                                                  "value": TAG}}]}


def no_export_user(admin, state):
    """A user whose role reads invoices and reports but may not export (the buttons are absent, the API refuses)."""
    role = base.must(admin.post("Role", {
        "name": f"{TAG} без экспорта", "exportPermission": "no",
        "data": {"Invoice": {"create": "no", "read": "all", "edit": "no", "delete": "no"}, "Account": {"read": "all"},
                 "Report": {"create": "no", "read": "all", "edit": "no", "delete": "no"},
                 "ReportFolder": {"create": "no", "read": "all", "edit": "no", "delete": "no"}}}))
    state["records"].append(["Role", role["id"]])
    password = secrets.token_urlsafe(14) + "Aa1!"
    user = base.must(admin.post("User", {
        "userName": "synth-rep-noexport", "firstName": "Отчёты", "lastName": f"{TAG} noexport", "type": "regular",
        "isActive": True, "password": password, "passwordConfirm": password, "rolesIds": [role["id"]],
        "sendAccessInfo": False}))
    state["users"]["noexport"] = user["id"]
    base.save_state(state)
    with base.USERS_ENV.open("a", encoding="utf-8") as env:
        env.write(f"UI_NOEXPORT_USERNAME=synth-rep-noexport\nUI_NOEXPORT_PASSWORD={password}\n")


def create():
    base.create()
    state = json.loads(base.STATE.read_text(encoding="utf-8"))
    admin = Client(*admin_credentials())
    no_export_user(admin, state)
    for key, address in ADDRESSES.items():
        base.must(admin.put(f"User/{state['users'][key]}", {"emailAddress": address}))
    manager, manager2 = state["users"]["manager"], state["users"]["manager2"]
    reports = {}

    def report(key, body):
        payload = base.must(admin.post("Report", {"accessType": "public", "assignedUserId": manager,
                                                  "filters": name_filter(), **body}))
        reports[key] = payload["id"]
        state.setdefault("reports", {})[key] = payload["id"]
        base.save_state(state)

    report("list", {"name": f"{TAG} Счета список", "type": "tabular", "entityType": "Invoice",
                    "columns": ["name", "account", "status", "grandTotal", "dateInvoiced"],
                    "totals": [{"column": "grandTotal", "functions": ["SUM", "AVG"]}], "rowLimit": 20,
                    "quickFilters": ["status"]})
    report("byStatus", {"name": f"{TAG} Счета по статусам", "type": "summaries", "entityType": "Invoice",
                        "groups": [{"field": "status"}],
                        "aggregates": [{"function": "COUNT"}, {"function": "SUM", "field": "grandTotal"}]})
    report("matrix", {"name": f"{TAG} Счета статус × месяц", "type": "matrix", "entityType": "Invoice",
                      "groups": [{"field": "status"}, {"field": "dateInvoiced", "granularity": "month"}],
                      "aggregates": [{"function": "SUM", "field": "grandTotal"}]})
    report("mailing", {"name": f"{TAG} Рассылка", "type": "tabular", "entityType": "Invoice",
                       "columns": ["name", "grandTotal"], "rowLimit": None,
                       "mailing": {"enabled": True, "frequency": "weekly", "weekday": 1, "time": "09:00",
                                   "users": [manager2], "emails": [EXTRA], "formats": ["csv", "xlsx", "pdf"]}})
    report("each", {"name": f"{TAG} Каждому", "type": "tabular", "entityType": "Invoice",
                    "columns": ["name", "grandTotal"], "rowLimit": None,
                    "filters": {"type": "and", "items": [*name_filter()["items"], {"field": "assignedUser", "where": {
                        "type": "isCurrentUser", "attribute": "assignedUserId"}}]},
                    "mailing": {"enabled": True, "frequency": "daily", "time": "08:00", "formats": ["csv"],
                                "generateFor": ["assignedUser"]}})
    report("empty", {"name": f"{TAG} Пустой", "type": "tabular", "entityType": "Invoice", "columns": ["name"],
                     "filters": {"type": "and", "items": [{"field": "name", "where": {
                         "type": "equals", "attribute": "name", "value": f"{TAG} нет такого"}}]},
                     "mailing": {"enabled": True, "frequency": "monthly", "day": 31, "time": "18:00",
                                 "emails": [EXTRA], "formats": ["xlsx"], "skipEmpty": True}})
    print(json.dumps({"reports": reports}, indent=2))


def purge_letters(state):
    user_ids = list(state.get("users", {}).values())
    in_users = "('" + "','".join(user_ids) + "')"
    emails = [r[0] for r in sql(f"SELECT id FROM email WHERE name LIKE '{TAG}%'")]
    emails += [r[0] for r in sql(
        "SELECT DISTINCT e.id FROM email e JOIN email_email_address x ON x.email_id = e.id "
        "JOIN email_address a ON a.id = x.email_address_id WHERE a.lower LIKE 'synth-rep-%@example.com'")]
    attachments = [r[0] for r in sql(f"SELECT id FROM attachment WHERE role = 'Export File' AND "
                                     f"created_by_id IN {in_users}")] if user_ids else []
    notifications = [r[0] for r in sql(f"SELECT id FROM notification WHERE user_id IN {in_users}")] if user_ids else []
    php = subprocess.run(["bash", "-c", f"source {REPO}/scripts/stand/lib.sh && echo $PHP_BIN"], capture_output=True,
                         text=True, check=True).stdout.strip()
    payload = json.dumps({"emails": sorted(set(emails)), "attachments": attachments, "notifications": notifications,
                          "addresses": [*ADDRESSES.values(), EXTRA]})
    out = subprocess.run(["sudo", "-n", "-u", "espocrm", "env", f"ESPO_ROOT={REPO}", php, "--", payload],
                         input=(REPO / "tests/stage05_3/mail_fixture.php").read_text(encoding="utf-8"),
                         capture_output=True, text=True, check=True).stdout
    print(out.strip())


def delete():
    admin = Client(*admin_credentials())
    state = json.loads(base.STATE.read_text(encoding="utf-8"))
    purge_letters(state)
    for rid in state.get("reports", {}).values():
        admin.delete(f"Report/{rid}")
    user_ids = list(state.get("users", {}).values())
    base.delete()
    if user_ids:
        sql("DELETE FROM notification WHERE user_id IN ('" + "','".join(user_ids) + "')")


if __name__ == "__main__":
    {"create": create, "delete": delete}[sys.argv[1]]()
