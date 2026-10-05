"""Shared helpers of the stage 05.3 acceptance tests (export, print, mailing — D-116…D-126) on the local stand.

They reuse the world of the stage 05.1 tests (tests/stage05_1/fixture.py: synthetic users, roles, the reference invoices
with known sums, cleanup registered before anything is created) and add what files and letters need: downloads and
readers of CSV, XLSX and PDF, the forced run of the mailing job, the cron run of queued jobs, the letters of a test and
the removal of the letters, files, notifications and addresses a test made (tests/stage05_3/mail_fixture.php — the
records are removed through the ORM as the stand user, a stored file with its last copy).

Expected values of the reference data (stage 05.1): seven invoices, SUM of grandTotal 34477.39; by status — Created 4
(31000.00), Sent 2 (3469.62), Approved 1 (7.77); i1…i6 assigned to the first director, i7 (500.00) to the second.
"""
import csv
import io
import json
import re
import subprocess
import sys
import time
import zipfile
from decimal import Decimal
from pathlib import Path
from xml.etree import ElementTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "stage05_1"))
from fixture import (D, Client, World, admin_credentials, all_of, cond, espo_console, label, must,  # noqa: E402,F401
                     reference_data, run, sql)

REPO = Path(__file__).resolve().parents[2]
JOB = "ItvolgaReportMailing"
BOM = "﻿"
SUM_ALL = D("34477.39")
BY_STATUS = {"Created": (4, D("31000.00")), "Sent": (2, D("3469.62")), "Approved": (1, D("7.77"))}
XLSX_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
EXPORT_FORMATS = ("csv", "xlsx", "pdf")
MIME = {"csv": "text/csv", "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "pdf": "application/pdf"}


def ok(result, what="request"):
    return must(result, what)


def export(client, report_id, fmt, **body):
    """POST Report/:id/export → (status, payload, headers)."""
    return client.request("POST", f"Report/{report_id}/export", {"format": fmt, **body})


def download(client, attachment_id):
    """The file of an attachment through the core entry point → (status, bytes, headers)."""
    return client.entry_point("download", id=attachment_id)


def export_file(client, report_id, fmt, track=None, **body):
    """Export and download: (attachment payload, bytes, headers); `track` (a set) gets the file id to remove."""
    payload = ok(export(client, report_id, fmt, **body), f"export {fmt}")
    if track is not None:
        track.add(payload["id"])
    status, data, headers = download(client, payload["id"])
    if status != 200:
        raise AssertionError(f"download {fmt}: HTTP {status}")
    return payload, data, headers


def csv_rows(data, delimiter=","):
    """Rows of a CSV file of the module: UTF-8 with a byte order mark."""
    text = data.decode("utf-8")
    if not text.startswith(BOM):
        raise AssertionError("no byte order mark")
    return list(csv.reader(io.StringIO(text[1:], newline=""), delimiter=delimiter))


def xlsx_rows(data):
    """Cells of the first sheet as rows of (type, value): t='n' numbers, 's'/'inlineStr' texts, style of dates kept."""
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        sheet = ElementTree.fromstring(archive.read("xl/worksheets/sheet1.xml"))
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            for item in ElementTree.fromstring(archive.read("xl/sharedStrings.xml")).findall("m:si", XLSX_NS):
                shared.append("".join(t.text or "" for t in item.iter(f"{{{XLSX_NS['m']}}}t")))
        rows = []
        for row in sheet.findall("m:sheetData/m:row", XLSX_NS):
            cells = []
            for cell in row.findall("m:c", XLSX_NS):
                kind = cell.get("t", "n")
                if cell.find("m:f", XLSX_NS) is not None:
                    kind = "formula"
                if kind == "inlineStr":
                    value = "".join(t.text or "" for t in cell.iter(f"{{{XLSX_NS['m']}}}t"))
                elif kind == "s":
                    value = shared[int(cell.find("m:v", XLSX_NS).text)]
                else:
                    v = cell.find("m:v", XLSX_NS)
                    value = v.text if v is not None else None
                cells.append((kind, value, cell.get("s")))
            rows.append(cells)
        return rows, sheet


def poppler(tool, data, *args):
    return subprocess.run([tool, *args, "-", "-"] if tool == "pdftotext" else [tool, *args, "-"], input=data,
                          capture_output=True, check=True).stdout.decode("utf-8")


def pdf_text(data):
    return poppler("pdftotext", data, "-layout")


def pdf_size(data):
    info = poppler("pdfinfo", data)
    match = re.search(r"Page size:\s+([\d.]+) x ([\d.]+)", info)
    return float(match.group(1)), float(match.group(2))


def dec(value):
    return None if value in (None, "") else Decimal(value)


# --- mailing ---------------------------------------------------------------------------------------------------------
def due(report_id):
    """Moves the next run of a report to the past (the job takes it at its next run)."""
    sql(f"UPDATE report SET mailing_next_run_at = '2000-01-01 00:00:00' WHERE id = '{report_id}'")


def runtime(report_id):
    row = sql(f"SELECT mailing_next_run_at, mailing_last_run_at, mailing_last_result FROM report "
              f"WHERE id = '{report_id}'")[0]
    return {"next": row[0] if row[0] != "NULL" else None, "last": row[1] if row[1] != "NULL" else None,
            "result": json.loads(row[2]) if row[2] not in ("NULL", "") else None}


def run_job(report_id, timeout=120):
    """Runs the mailing job now and waits until the report's attempt has an outcome (cron may take it first)."""
    espo_console("run-job", JOB)
    deadline = time.time() + timeout
    while True:
        state = runtime(report_id)
        if state["result"] and state["result"].get("status") != "running" and state["next"] != "2000-01-01 00:00:00":
            return state
        if time.time() > deadline:
            raise AssertionError(f"mailing of {report_id} has no outcome: {state}")
        time.sleep(2)
        espo_console("run-job", JOB)


def php_bin():
    return subprocess.run(["bash", "-c", f"source {REPO}/scripts/stand/lib.sh && echo $PHP_BIN"], capture_output=True,
                          text=True, check=True).stdout.strip()


def run_cron():
    """One run of cron.php as the stand user: the queued jobs (a background export) are executed."""
    subprocess.run(["sudo", "-n", "-u", "espocrm", "env", f"PATH={Path(php_bin()).parent}:/usr/bin:/bin", php_bin(),
                    str(REPO / "cron.php")], cwd=REPO, capture_output=True, check=True, timeout=300)


def mail_fixture(payload):
    """tests/stage05_3/mail_fixture.php as the stand user → its JSON answer."""
    out = subprocess.run(["sudo", "-n", "-u", "espocrm", "env", f"ESPO_ROOT={REPO}", php_bin(), "--", json.dumps(payload)],
                         input=(REPO / "tests/stage05_3/mail_fixture.php").read_text(encoding="utf-8"),
                         capture_output=True, text=True, check=True).stdout
    answer = json.loads(out.strip().splitlines()[-1])
    if not answer.get("ok"):
        raise AssertionError(f"mail fixture: {answer}")
    return answer


class Letters:
    """The letters of a test world (subjects start with its tag or carry a given marker) and their removal."""

    def __init__(self, world):
        self.world = world
        self.addresses = set()
        self.extra_attachments = set()

    def address(self, key):
        address = f"synth-{self.world.run_id}-{key}@example.com"
        self.addresses.add(address)
        return address

    def give_address(self, user_key, key=None):
        address = self.address(key or user_key)
        ok(self.world.admin.put(f"User/{self.world.uid[user_key]}", {"emailAddress": address}), "user address")
        return address

    def ids(self, marker=None):
        like = (marker or self.world.tag).replace("'", "")
        return [r[0] for r in sql(f"SELECT id FROM email WHERE deleted = 0 AND name LIKE '%{like}%' ORDER BY created_at")]

    def read(self, marker=None):
        """Letters as the admin reads them: to, subject, status, attachments, body."""
        letters = []
        for email_id in self.ids(marker):
            payload = ok(self.world.admin.get(f"Email/{email_id}"), "email")
            letters.append(payload)
        return letters

    def notifications(self, user_key):
        return [{"id": r[0], "message": r[1]} for r in sql(
            f"SELECT id, message FROM notification WHERE user_id = '{self.world.uid[user_key]}' AND deleted = 0 "
            "ORDER BY created_at")]

    def purge(self):
        uids = list(self.world.uid.values())
        emails = self.ids()
        notifications = []
        attachments = list(self.extra_attachments)
        if uids:
            in_users = "('" + "','".join(uids) + "')"
            notifications = [r[0] for r in sql(f"SELECT id FROM notification WHERE user_id IN {in_users}")]
            attachments += [r[0] for r in sql(f"SELECT id FROM attachment WHERE role = 'Export File' "
                                              f"AND created_by_id IN {in_users}")]
            emails += [r[0] for r in sql(
                "SELECT DISTINCT e.id FROM email e JOIN email_email_address x ON x.email_id = e.id "
                "JOIN email_address a ON a.id = x.email_address_id "
                f"WHERE a.lower LIKE 'synth-{self.world.run_id}-%'")]
        mail_fixture({"emails": sorted(set(emails)), "attachments": sorted(set(attachments)),
                      "notifications": notifications, "addresses": sorted(self.addresses)})

    def purge_notifications(self):
        """Notifications the core sends while the world is removed («record removed» to its synthetic users)."""
        uids = list(self.world.uid.values())
        if uids:
            sql("DELETE FROM notification WHERE user_id IN ('" + "','".join(uids) + "')")
