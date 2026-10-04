"""Shared helpers of the stage 05.1 acceptance tests (reports module, D-84…D-102) on the local stand, synthetic data.

Every test module builds its own World in setUpModule and registers World.cleanup with unittest.addModuleCleanup
before anything is created: synthetic users of the stand roles (random passwords, never printed), temporary roles and
teams, records named «SYNTH-<run> …» and reports. The cleanup deletes the reports first, then everything else in reverse
order of creation, and reports what it could not delete.

reference_data() creates the data set with known sums (decimal strings, exact to the kopeck): three accounts, two
contacts, three products and seven invoices of this month and of the last month whose lines give the totals below.

  invoice  account  contact  status    date (dateDue)         lines (product qty × price)           grandTotal
  i1       a1       c1       Created   M0-01 (M0-15)          p1 1×15000, p2 2.5×1800                 19500.00
  i2       a1       —        Sent      M0-02 (M0-01: < date)  p1 1×1000.50                             1000.50
  i3       a2       c2       Created   M1-15 (M1-25)          p2 3×333.33, p3 1×10000                 10999.99
  i4       a2       —        Sent      M1-20 (M1-10: < date)  p3 2×1234.56                             2469.12
  i5       a3       —        Approved  M0-03 (M0-20)          p1 1×5, p1 1×2.77 (same product twice)     7.77
  i6       a3       —        Created   M1-05 (M1-19)          p2 1×0.01                                   0.01
  i7       a1       —        Created   M0-01 (M0-10)          p3 1×500 — assigned to «dir2», not «dir»   500.00

M0 is the first day of the current month and M1 of the previous one, in the time zone of the stand (a report run
resolves relative periods there). Every report of the tests filters on the «SYNTH-<run>» names (or ids), so data of
other runs or of the stand never enter the expected values.
"""
import json
import secrets
import sys
import time
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "stage03"))
from espo import Client, admin_credentials, espo_console, sql  # noqa: E402,F401

D = Decimal
REPO = Path(__file__).resolve().parents[2]
ROLE_NAMES = ("Директор", "Заместитель директора", "Менеджер по продажам", "Менеджер клиентов", "Доступы")
# Scopes a synthetic role needs to work with reports at all (EspoCRM 10 denies scopes no role grants).
REPORT_SCOPES = {"Report": {"create": "yes", "read": "own", "edit": "own", "delete": "own"},
                 "ReportFolder": {"create": "no", "read": "all", "edit": "no", "delete": "no"},
                 "User": {"read": "all", "edit": "no"}, "Team": {"read": "all"}}
READ = {"create": "no", "read": "all", "edit": "no", "delete": "no"}


def must(result, what="request"):
    status, payload, _ = result
    if status != 200:
        raise AssertionError(f"{what}: HTTP {status} {json.dumps(payload, ensure_ascii=False)[:400]}")
    return payload


def label(result):
    """Translation label of a refused request (Report.messages.* / ReportFolder.messages.*), or None."""
    payload = result[1] if isinstance(result[1], dict) else {}
    return (payload.get("messageTranslation") or {}).get("label")


def flat(prefix, value, out=None):
    """A nested structure as PHP query parameters: where[0][value][link]=… (GET lists of the core)."""
    out = {} if out is None else out
    if isinstance(value, dict):
        for key, item in value.items():
            flat(f"{prefix}[{key}]", item, out)
    elif isinstance(value, list):
        for i, item in enumerate(value):
            flat(f"{prefix}[{i}]", item, out)
    else:
        out[prefix] = ("true" if value else "false") if isinstance(value, bool) else value
    return out


def list_ids(client, entity, where, **params):
    """Ids of the core record list GET <entity> with the given where items (status, set of ids)."""
    status, payload, _ = client.get(entity, **flat("where", where), select="id", maxSize=200, **params)
    return status, ({r["id"] for r in payload["list"]} if status == 200 else None)


def drill_down(client, entity, report_id, path=(), **extra):
    """Records of a report group through the core list (where item `itvolgaReport`, D-98)."""
    value = json.dumps({"id": report_id, "path": list(path), **extra})
    return list_ids(client, entity, [{"type": "itvolgaReport", "attribute": "id", "value": value}])


def run(client, report_id, **body):
    """POST Report/:id/run → (status, payload, headers)."""
    return client.request("POST", f"Report/{report_id}/run", body)


def cond(field, type_, value=None, attribute=None):
    """One condition of a report: field ref + core-like where item (attribute defaults to the field name)."""
    item = {"type": type_, "attribute": attribute or field.split(".")[-1]}
    if value is not None:
        item["value"] = value
    return {"field": field, "where": item}


def all_of(*conditions):
    return {"type": "and", "items": list(conditions)}


def num(cell):
    """Decimal of a result cell (`v` is a decimal string; COUNT an int), None for an empty cell."""
    if cell is None or cell.get("v") is None:
        return None
    return D(str(cell["v"]))


def stand_today():
    tz = Client(*admin_credentials()).get("Settings")[1].get("timeZone") or "UTC"
    return datetime.now(ZoneInfo(tz)).date()


def month_start(day, shift=0):
    y, m = day.year, day.month + shift
    while m < 1:
        y, m = y - 1, m + 12
    while m > 12:
        y, m = y + 1, m - 12
    return date(y, m, 1)


def period_key(day, granularity):
    """Group key of a date as the report engine makes it (D-89)."""
    if granularity == "day":
        return day.isoformat()
    if granularity == "week":
        year, week, _ = day.isocalendar()
        return f"{year}/{week}"
    if granularity == "month":
        return f"{day.year}-{day.month:02d}"
    if granularity == "quarter":
        return f"{day.year}_{(day.month - 1) // 3 + 1}"
    if granularity == "halfYear":
        return f"{day.year}_{1 if day.month <= 6 else 2}"
    return str(day.year)


class World:
    """Users, roles, teams and records of one test module, removed by cleanup()."""

    def __init__(self):
        self.run_id = secrets.token_hex(3)
        self.tag = f"SYNTH-{self.run_id}"
        self.admin = Client(*admin_credentials())
        self.created = []
        self.uid, self.clients = {}, {}
        roles = {r["name"]: r["id"] for r in must(self.admin.get("Role", maxSize=200), "roles")["list"]}
        missing = [n for n in ROLE_NAMES if n not in roles]
        if missing:
            raise AssertionError(f"stand roles missing (task espo -- itvolga-setup-acl): {missing}")
        self.roles = roles

    # --- registry --------------------------------------------------------------------------------------------
    def register(self, entity, rid):
        self.created.append((entity, rid))
        return rid

    def forget(self, entity, rid):
        self.created = [c for c in self.created if c != (entity, rid)]

    def cleanup(self):
        failures = []
        order = [c for c in reversed(self.created) if c[0] == "Report"] + \
                [c for c in reversed(self.created) if c[0] != "Report"]
        for entity, rid in order:
            status = None
            for _ in range(3):
                status = self.admin.delete(f"{entity}/{rid}")[0]
                if status in (200, 404):
                    break
                time.sleep(1)
            if status not in (200, 404):
                failures.append(f"{entity}/{rid}: HTTP {status}")
        self.created = []
        if failures:
            raise AssertionError("cleanup failed: " + ", ".join(failures))

    # --- users, roles, teams -------------------------------------------------------------------------------
    def role(self, key, data, field_data=None, with_reports=True):
        payload = must(self.admin.post("Role", {"name": f"{self.tag} {key}",
                                                "data": {**(REPORT_SCOPES if with_reports else {}), **data},
                                                "fieldData": field_data or {}}), f"role {key}")
        return self.register("Role", payload["id"])

    def team(self, key):
        return self.register("Team", must(self.admin.post("Team", {"name": f"{self.tag} {key}"}), "team")["id"])

    def user(self, key, roles=(), role_ids=(), teams=()):
        """A synthetic user of stand roles (by name) and/or synthetic roles (by id); returns its client."""
        password = secrets.token_urlsafe(18) + "Aa1!"
        payload = must(self.admin.post("User", {
            "userName": f"synth-{self.run_id}-{key}", "firstName": "Отчёт", "lastName": f"{self.tag} {key}",
            "type": "regular", "isActive": True, "password": password, "passwordConfirm": password,
            "rolesIds": [self.roles[r] for r in roles] + list(role_ids), "teamsIds": list(teams),
            "sendAccessInfo": False}), f"user {key}")
        self.register("User", payload["id"])
        self.uid[key] = payload["id"]
        self.clients[key] = Client(f"synth-{self.run_id}-{key}", password)
        return self.clients[key]

    def client(self, key):
        return self.admin if key == "admin" else self.clients[key]

    # --- records ---------------------------------------------------------------------------------------------
    def create(self, entity, data, by="admin"):
        payload = must(self.client(by).post(entity, data), f"create {entity}")
        self.register(entity, payload["id"])
        return payload

    def try_create(self, entity, data, by="admin"):
        result = self.client(by).post(entity, data)
        if result[0] == 200 and isinstance(result[1], dict) and result[1].get("id"):
            self.register(entity, result[1]["id"])
        return result

    def report_body(self, owner, name, **definition):
        body = {"name": f"{self.tag} {name}", "type": "tabular", "accessType": "private", **definition}
        if owner != "admin" and "assignedUserId" not in body:
            body["assignedUserId"] = self.uid[owner]
        elif "assignedUserId" not in body:
            body["assignedUserId"] = must(self.admin.get("App/user"), "admin user")["user"]["id"]
        return body

    def report(self, owner, name, **definition):
        """Creates a report as `owner` (a user key or "admin"), owned by that user unless assignedUserId is given."""
        return self.create("Report", self.report_body(owner, name, **definition), by=owner)

    def try_report(self, owner, name, **definition):
        return self.try_create("Report", self.report_body(owner, name, **definition), by=owner)

    def name_filter(self):
        return cond("name", "startsWith", self.tag)


def invoice_lines(*rows):
    return [{"productId": product, "quantity": qty, "unitPrice": price} for product, qty, price in rows]


def reference_data(world, owner="dir", other="dir2"):
    """The data set of the module docstring, created as the director `owner`; returns ids, dates and sums."""
    tag, uid = world.tag, world.uid
    today = stand_today()
    m0, m1 = month_start(today), month_start(today, -1)
    ref = {"today": today, "m0": m0, "m1": m1}
    for key, name, inn in (("a1", "Альфа", "77-SYNTH-A1"), ("a2", "Бета", "77-SYNTH-B2"), ("a3", "Гамма", None)):
        ref[key] = world.create("Account", {"name": f"{tag} {name}", "cInn": inn, "assignedUserId": uid[owner]},
                                by=owner)["id"]
    for key, account in (("c1", "a1"), ("c2", "a2")):
        ref[key] = world.create("Contact", {"firstName": "Иван", "lastName": f"{tag} {key}", "accountId": ref[account],
                                            "assignedUserId": uid[owner]}, by=owner)["id"]
    for key, name in (("p1", "1 Обслуживание"), ("p2", "2 Настройка"), ("p3", "3 Лицензия")):
        ref[key] = world.create("Product", {"name": f"{tag} {name}", "type": "service"}, by=owner)["id"]
    p1, p2, p3 = ref["p1"], ref["p2"], ref["p3"]
    day = lambda base, n: base + timedelta(days=n - 1)  # noqa: E731
    specs = {
        "i1": ("a1", "c1", "Created", day(m0, 1), day(m0, 15), [(p1, "1", "15000"), (p2, "2.5", "1800")], owner),
        "i2": ("a1", None, "Sent", day(m0, 2), day(m0, 1), [(p1, "1", "1000.50")], owner),
        "i3": ("a2", "c2", "Created", day(m1, 15), day(m1, 25), [(p2, "3", "333.33"), (p3, "1", "10000")], owner),
        "i4": ("a2", None, "Sent", day(m1, 20), day(m1, 10), [(p3, "2", "1234.56")], owner),
        "i5": ("a3", None, "Approved", day(m0, 3), day(m0, 20), [(p1, "1", "5"), (p1, "1", "2.77")], owner),
        "i6": ("a3", None, "Created", day(m1, 5), day(m1, 19), [(p2, "1", "0.01")], owner),
        "i7": ("a1", None, "Created", day(m0, 1), day(m0, 10), [(p3, "1", "500")], other),
    }
    ref["invoices"] = {}
    for key, (account, contact, status, dated, due, rows, assigned) in specs.items():
        payload = world.create("Invoice", {
            "name": f"{tag} {key}", "accountId": ref[account], "contactId": ref[contact] if contact else None,
            "status": status, "dateInvoiced": dated.isoformat(), "dateDue": due.isoformat(),
            "assignedUserId": uid[assigned], "itemList": invoice_lines(*rows)}, by=owner)
        ref[key] = payload["id"]
        ref["invoices"][key] = {"id": payload["id"], "account": account, "contact": contact, "status": status,
                                "date": dated, "due": due, "owner": assigned, "total": D(str(payload["grandTotal"])),
                                "lines": [(p, D(q) * D(pr)) for p, q, pr in rows]}
    expected = {"i1": "19500", "i2": "1000.50", "i3": "10999.99", "i4": "2469.12", "i5": "7.77", "i6": "0.01",
                "i7": "500"}
    for key, total in expected.items():
        got = ref["invoices"][key]["total"]
        if got != D(total):
            raise AssertionError(f"reference invoice {key}: grandTotal {got}, expected {total}")
    return ref
