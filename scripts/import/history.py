"""Stage 07.2 glue of the importer (docs/migration/import.md «История звонков»): the CDR sources of a verified snapshot
(or of a synthetic directory in the stage tests), the placement of the recordings on the stand, and the
reconciliation of the call history — every MySQL row, CSV line, recording file and month accounted with a reason.
Values never leave the process: reports carry keys, counts, statuses and sha256 (a recording's name carries numbers).
"""
import csv
import datetime as dt
import json
import os
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import source  # noqa: F401  (puts scripts/snapshot on sys.path)
import cdr as CDR
import spec_telephony as P
import transforms as T
import verify  # noqa: E402
from common import Mysql, SnapshotError, read_json, sha256_file, write_private

REPO = Path(__file__).resolve().parents[2]
TELEPHONY = REPO / "scripts" / "stand" / "telephony.sh"
KEPT = ("placed", "present")
WRITTEN = ("created", "updated", "unchanged")


class Query:
    """A read-only writer operation without a record (`telephonyRules`, `callInventory`)."""

    entityType, module, file, skip, pending, vtigerId, outcomes = None, None, None, None, None, None, ()

    def __init__(self, name):
        self.name, self.key = name, f"telephony:{name}"

    def payload(self):
        return {"op": self.name, "key": self.key}


@dataclass
class Sources:
    csv_records: list      # [(line number, fields)]
    csv_present: bool
    inventory: dict        # relative path → (size, sha256)
    monitor_dir: Path
    t0: dt.datetime        # UTC, naive


def snapshot_sources(snapdir):
    """Master.csv checked against its sealed inventory before it is parsed; the monitor inventory; T0 of the tables."""
    manifest = read_json(snapdir / "MANIFEST.json")
    t0 = dt.datetime.strptime(manifest["db"]["begin_utc"][:19].replace("T", " "), CDR.DATETIME)
    sealed = verify.read_inventory(snapdir, "cdr-csv")
    path = snapdir / "files" / "cdr-csv" / "Master.csv"
    records, present = [], b"Master.csv" in sealed
    if present:
        size, _mtime, digest = sealed[b"Master.csv"]
        if not path.is_file() or path.stat().st_size != size or sha256_file(path) != digest:
            raise SnapshotError("Master.csv differs from the sealed inventory: nothing written")
        records = read_csv(path)
    inventory = {rel.decode("utf-8", "surrogateescape"): (size, digest)
                 for rel, (size, _mtime, digest) in verify.read_inventory(snapdir, "monitor").items()}
    return Sources(records, present, inventory, snapdir / "files" / "monitor", t0)


def directory_sources(root, t0):
    """A synthetic part (tests): `<root>/cdr-csv/Master.csv`, `<root>/monitor/YYYY/MM/DD/*.wav` — inventory computed."""
    root = Path(root)
    path = root / "cdr-csv" / "Master.csv"
    inventory = {}
    base = root / "monitor"
    for dirpath, _dirs, names in os.walk(base):
        for name in names:
            full = Path(dirpath) / name
            inventory[str(full.relative_to(base))] = (full.stat().st_size, sha256_file(full))
    return Sources(read_csv(path) if path.is_file() else [], path.is_file(), inventory, base, t0)


def read_csv(path):
    with open(path, newline="", encoding="utf-8", errors="surrogateescape") as fh:
        return list(enumerate(csv.reader(fh), 1))


def read_mysql(db):
    """Rows of `cdr` with the census of every column and the reader's own counts (transport check)."""
    rows = db.select("", ("cdr",))
    census = db.census("", ("cdr",), {})
    reader = Counter()
    for row in rows:
        for name, value in row.items():
            reader[name] += 0 if T.is_empty(value) else 1
    bad = [k for k, (n, _m) in census.items() if reader.get(k, 0) != n]
    if bad:
        raise SnapshotError(f"CDR reader and census disagree on {len(bad)} columns: nothing written")
    return rows, census


def stand_monitor_dir():
    out = subprocess.run(["bash", "-c", 'source "$0" >/dev/null && echo "$TELEPHONY_MONITOR_DIR"',
                          str(REPO / "scripts" / "stand" / "lib.sh")], capture_output=True, text=True, check=True)
    return out.stdout.strip()


def place(ops, sources, states, logdir):
    """Copies the recordings of the calls the run writes (not live, not deleted in the target) into the stand's root
    (scripts/stand/place_recordings.py as root): {operation key: status}. Names and checksums go through stdin only."""
    skip = set(states.get("live", [])) | set(states.get("deleted", []))
    items = [op for op in ops if op.recording and op.group.key not in skip]
    if not items:
        return {}
    out, errors = {}, []

    def stream():
        for i, op in enumerate(items):
            rel = op.recording["path"].encode("utf-8", "surrogateescape").hex()
            yield (json.dumps({"i": i, "rel": rel, "size": op.recording["size"],
                               "sha256": op.recording["sha256"]}) + "\n").encode()

    def consume(line):
        data = json.loads(line)
        if "error" in data:
            errors.append(data["error"])
        else:
            out[items[data["i"]].key] = data["status"]

    Mysql([str(TELEPHONY), "place-recordings", str(sources.monitor_dir)], "place-recordings").session(
        stream(), consume, logdir / "place-recordings.log")
    if errors or len(out) != len(items):
        raise SnapshotError("placing the recordings failed (see the run's logs): nothing more written")
    return out


# --- reconciliation ------------------------------------------------------------------------------------------------

def report(rep, plan, cdr_plan, applied, checked, placement, cdr_census, before, after, rundir, check_only, mode):
    """The call-history section of the run report; CDR value rows join report["columns"]; problems and findings join
    the run's; private machine reports per call, row, line and file."""
    problems, findings = Counter(rep["problems"]), Counter(rep["findings"])
    problem_columns = defaultdict(list, rep["problem_columns"])
    pbx = pbx_section(plan, checked)
    section = {"read": cdr_plan is not None, "pbx": pbx, "recordings_mode": mode}
    month_rows = defaultdict(Counter)
    for op in plan.ops + plan.held:
        if op.module == "PBXManager" and op.attributes.get("dateStart"):
            month_rows[op.attributes["dateStart"][:7]]["pbx_internal" if op.skip == P.EXCLUDED else "pbx"] += 1
    if cdr_plan is None:
        section["periods"] = periods(month_rows)
        rep.update(telephony=section)
        return
    calls, files, row_fates, line_fates = [], dict(cdr_plan.files), {}, dict(cdr_plan.lines)
    status_of, recording_of = {}, {}
    for group in cdr_plan.groups:
        key = f"cdr:{group.key}"
        a, c = applied.get(key, {}), checked.get(key, {})
        written = group.direction is not None
        state = c.get("status") if written else None
        status_of[group.key] = state
        rec = c.get("recording") if written else None
        recording_of[group.key] = rec
        calls.append({"key": group.key, "source": group.source, "month": group.month, "legs": len(group.legs),
                      "class": group.direction or group.reason, "id": c.get("id") or a.get("id"),
                      "apply": a.get("status"), "check": state, "error": a.get("error") or c.get("error"),
                      "differs": c.get("differs"), "assignee": a.get("assignee"),
                      "recording": {"planned": group.recording is not None, "reason": group.recording_reason,
                                    "placement": placement.get(key), "writer": rec}})
        if written:
            if a.get("status") == "error" or c.get("status") == "error":
                problems["cdr_call_errors"] += 1
            elif c.get("status") == "differs" or (c.get("status") == "missing" and not check_only):
                problems["cdr_call_not_equal"] += 1
            elif c.get("status") in ("live_call", "deleted_in_target"):
                findings[c["status"]] += 1
        month_rows[group.month]["calls" if written else "calls_not_imported"] += 1
        for leg in group.legs:
            fate = (state if state in ("live_call", "deleted_in_target") else "call") if written \
                else f"not_imported:{group.reason}"
            if leg.source == "mysql":
                row_fates[leg.ref] = fate
                month_rows[group.month]["mysql_rows"] += 1
            else:
                line_fates[leg.ref[1]] = fate
        if written and group.recording is not None:
            p = placement.get(key)
            if state in ("live_call", "deleted_in_target"):
                files[group.recording] = f"call_untouched:{state}"
            elif p is not None and p not in KEPT:
                files[group.recording] = f"not_attached:placement_{p}"
                (problems if p == "source_mismatch" else findings)[f"recording_placement_{p}"] += 1
            elif rec == "attached":
                files[group.recording] = "attached"
            elif check_only and state == "missing":
                files[group.recording] = "candidate"
            else:
                files[group.recording] = f"not_attached:{rec}"
                bucket = findings if rec in ("claimed_in_target", "claim_kept") or mode == "verify" else problems
                bucket[f"recording_{rec}"] += 1
        elif written and group.recording_reason not in (None, "none"):
            findings[f"recording_unavailable:{group.recording_reason}"] += 1
    for number, month in cdr_plan.line_month.items():
        month_rows[month]["csv_lines"] += 1
        if line_fates.get(number) == "after_t0":
            findings["csv_after_t0"] += 1
    if not cdr_plan.csv_present:
        findings["cdr_csv_missing"] += 1
    if cdr_plan.flags.get("csv_leg_joined_mysql"):  # a leg the MySQL table lost: joined its call, the table is short
        findings["cdr_csv_leg_joined_mysql"] = cdr_plan.flags["csv_leg_joined_mysql"]
    conflicts = sum(1 for f in line_fates.values() if f == "conflict_with_mysql")
    if conflicts:
        findings["cdr_csv_conflict_with_mysql"] = conflicts
    invalid = sum(1 for f in line_fates.values() if f.startswith("invalid"))
    if invalid:
        findings["csv_invalid_lines"] = invalid
    for rel, fate in files.items():
        month = rel[:7].replace("/", "-")
        month_rows[month]["files"] += 1
        month_rows[month]["files_attached" if fate == "attached" else "files_not_attached"] += 1
    for group in cdr_plan.groups:
        if group.reason == "no_first_channel":
            findings["cdr_no_first_channel"] += 1
    keys = {g.key for g in cdr_plan.groups}
    absent = sorted(set((after or before or {}).get("history", [])) - keys)
    if absent:
        findings["cdr_absent_from_source"] = len(absent)  # never removed (owner's answer 2026-10-17)
    columns, col_problems = cdr_columns(cdr_plan, cdr_census, row_fates, status_of, recording_of, checked, check_only)
    for name, cols in col_problems.items():
        problems[name] += len(cols)
        problem_columns[name] += cols
    rep["columns"] = rep["columns"] + columns
    section.update(
        t0=cdr_plan.t0, csv_present=cdr_plan.csv_present,
        mysql={"rows": len(cdr_plan.nonempty), "fates": dict(Counter(row_fates.values()))},
        csv={"lines": len(line_fates), "fates": dict(Counter(line_fates.values()))},
        groups={"total": len(cdr_plan.groups), "classes": dict(Counter(g.direction or g.reason for g in cdr_plan.groups)),
                "by_source": dict(Counter(f"{g.source}:{'call' if g.direction else 'not_imported'}"
                                          for g in cdr_plan.groups))},
        calls={k: v for k, v in Counter(f"{'apply' if p == 0 else 'check'}:{s}" for c in calls
                                         for p, s in enumerate((c["apply"], c["check"])) if s).items()},
        recordings={"files": len(files), "fates": dict(Counter(files.values())),
                    "unavailable_for_calls": dict(Counter(
                        c["recording"]["reason"] for c in calls if c["class"] in ("Inbound", "Outbound")
                        and c["recording"]["reason"] not in (None, "none")))},
        d31_check={k.split(":", 1)[0][10:] or k: v for k, v in cdr_plan.flags.items() if k.startswith("d31_check")},
        absent_from_source=len(absent), absent_keys=absent,  # Asterisk keys (not personal data), private report
        flags={k: v for k, v in sorted(cdr_plan.flags.items()) if not k.startswith(("class:", "d31_check"))},
        periods=periods(month_rows))
    rep.update(problems=dict(problems), problem_columns=dict(problem_columns),
               findings={k: v for k, v in findings.items() if v}, telephony=section)
    if problems:
        rep["status"] = "fail"
    elif rep["status"] == "pass" and rep["findings"]:
        rep["status"] = "findings"
    write_private(rundir / "telephony-calls.jsonl", "".join(json.dumps(c, sort_keys=True) + "\n" for c in calls))
    write_private(rundir / "telephony-rows.jsonl", "".join(
        json.dumps({"row": ref[1], "fate": fate}) + "\n" for ref, fate in sorted(row_fates.items())))
    write_private(rundir / "telephony-lines.jsonl", "".join(
        json.dumps({"line": n, "fate": fate}) + "\n" for n, fate in sorted(line_fates.items())))
    inventory = cdr_plan.inventory
    write_private(rundir / "telephony-files.jsonl", "".join(
        json.dumps({"month": rel[:7].replace("/", "-"), "size": inventory.get(rel, (None, None))[0],
                    "sha256": inventory.get(rel, (None, None))[1], "fate": fate,
                    "call": next((g.key for g in cdr_plan.groups if g.recording == rel), None)}, sort_keys=True) + "\n"
        for rel, fate in sorted(files.items())))


def pbx_section(plan, checked):
    ops = [o for o in plan.ops + plan.held if o.module == "PBXManager"]
    carriers = list(plan.merged)
    return {"records": len(ops), "imported": sum(1 for o in ops if not (o.skip or o.pending)),
            "excluded_internal": sum(1 for o in ops if o.skip == P.EXCLUDED),
            "held_other": sum(1 for o in ops if (o.skip or o.pending) and o.skip != P.EXCLUDED),
            "popups": len(carriers), "popups_merged": sum(1 for c in carriers if not c.skip),
            "legacy_recording_urls": sum(1 for o in ops if o.attributes.get("cLegacyRecordingUrl")),
            "lookup": {k.split(":", 1)[1]: v for k, v in plan.flags.items() if k.startswith("pbx_lookup:")},
            "check": dict(Counter(checked.get(o.key, {}).get("status") for o in ops if not (o.skip or o.pending)))}


def cdr_columns(cdr_plan, census, row_fates, status_of, recording_of, checked, check_only):
    """Every non-empty value of every column of asteriskcdrdb.cdr gets one outcome (the whole-snapshot ledger reads
    these rows like the other modules' columns)."""
    group_of = {leg.ref: g for g in cdr_plan.groups for leg in g.legs if leg.source == "mysql"}
    entries = defaultdict(lambda: {"outcomes": Counter(), "verified": 0, "mismatch": 0, "exempt": 0})
    for ref, cols in cdr_plan.nonempty.items():
        group = group_of[ref]
        state = status_of.get(group.key)
        for col in cols:
            e = entries[col]
            fate = CDR.COLUMN_FATES.get(col, "")
            if col in CDR.KEYS:
                e["outcomes"]["key"] += 1
            elif fate.startswith("исключено") or not fate:
                e["outcomes"]["excluded" if fate else "no_fate"] += 1
            elif group.direction is None:
                e["outcomes"][f"not_applicable:{group.reason}"] += 1
            elif state in ("live_call", "deleted_in_target"):
                e["outcomes"]["protected"] += 1
                e["exempt"] += 1
            elif col == "recordingpath" and recording_of.get(group.key) != "attached" and not (
                    check_only and state == "missing"):
                e["outcomes"][f"not_applicable:recording_{group.recording_reason or recording_of.get(group.key)}"] += 1
            else:
                e["outcomes"]["carried"] += 1
                if check_only and state == "missing":
                    continue
                e["verified" if state == "equal" else "mismatch"] += 1
    out, problems = [], defaultdict(list)
    for name, (nonempty, meaningful) in sorted(census.items()):
        col = name.split(".", 1)[1]
        fate = CDR.COLUMN_FATES.get(col, "")
        e = entries.get(col, {"outcomes": Counter(), "verified": 0, "mismatch": 0, "exempt": 0})
        accounted = sum(e["outcomes"].values())
        item = {"module": "CDR", "column": name, "fate": fate, "nonempty": nonempty, "meaningful": meaningful,
                "category": "key" if col in CDR.KEYS else "rule" if fate else "unmapped",
                "outcomes": dict(e["outcomes"]), "verified": e["verified"], "mismatch": e["mismatch"],
                "exempt": e["exempt"], "unaccounted": nonempty - accounted}
        if not fate and nonempty:
            problems["cdr_column_without_fate"].append(name)
        if nonempty != accounted:
            problems["cdr_values_unaccounted"].append(name)
        if e["mismatch"]:
            problems["cdr_values_mismatch"].append(name)
        out.append(item)
    return out, problems


def periods(month_rows):
    """One row per month from the first source month to the last, the D-16 gap and months without a source marked."""
    if not month_rows:
        return []
    first, last = min(month_rows), max(month_rows)
    out, y, m = [], int(first[:4]), int(first[5:7])
    while f"{y:04d}-{m:02d}" <= last:
        month = f"{y:04d}-{m:02d}"
        counts = dict(month_rows.get(month, {}))
        note = "D-16" if CDR.GAP_D16[0] <= month <= CDR.GAP_D16[1] else ("" if counts else "no_source")
        out.append({"month": month, **counts, **({"note": note} if note else {})})
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


# --- summary -------------------------------------------------------------------------------------------------------

def render(rep):
    t = rep.get("telephony")
    if not t:
        return []
    pbx = t.get("pbx", {})
    lines = ["", "## История звонков (этап 07.2)", "",
             f"PBXManager: записей {pbx.get('records', 0)}, перенесено {pbx.get('imported', 0)}, внутренних не "
             f"переносится {pbx.get('excluded_internal', 0)}, удержано по другим причинам {pbx.get('held_other', 0)}; "
             f"SPCallPopup {pbx.get('popups', 0)} (слито {pbx.get('popups_merged', 0)}); архивных ссылок коннектора "
             f"(не аудио, D-10) {pbx.get('legacy_recording_urls', 0)}; клиенты по номеру — "
             + (", ".join(f"{k} {v}" for k, v in sorted(pbx.get("lookup", {}).items())) or "нет") + "."]
    if t.get("read"):
        lines += [
            "",
            f"CDR (граница T0 снимка {t.get('t0')} UTC; записи — режим `{t.get('recordings_mode')}`): строк MySQL "
            f"{t['mysql']['rows']}, строк CSV {t['csv']['lines']}; звонков (групп плеч) {t['groups']['total']}.",
            "",
            "| Что | Счётчики |", "|---|---|",
            "| Строки MySQL | " + _pairs(t["mysql"]["fates"]) + " |",
            "| Строки CSV | " + _pairs(t["csv"]["fates"]) + " |",
            "| Звонки по классам | " + _pairs(t["groups"]["classes"]) + " |",
            "| Звонки по источнику | " + _pairs(t["groups"]["by_source"]) + " |",
            "| Запись и проверка | " + _pairs(t["calls"]) + " |",
            "| Файлы записей | " + _pairs(t["recordings"]["fates"]) + " |",
            "| Нет записи у звонка | " + (_pairs(t["recordings"]["unavailable_for_calls"]) or "—") + " |",
            "| D-31 на известных парах | " + (_pairs(t.get("d31_check", {})) or "—") + " |",
            f"| Нет в источнике (не удаляются) | {t.get('absent_from_source', 0)} |",
        ]
    lines += ["", "По месяцам (звонки — месяц начала по UTC, файлы — каталог записи; D-16 — источников нет):", "",
              "| Месяц | PBXManager | внутр. | строк MySQL | строк CSV | звонков | не переносится | файлов | "
              "привязано | не привязано | Примечание |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
    for row in t.get("periods", []):
        lines.append("| " + " | ".join(str(row.get(k, "")) for k in (
            "month", "pbx", "pbx_internal", "mysql_rows", "csv_lines", "calls", "calls_not_imported", "files",
            "files_attached", "files_not_attached", "note")) + " |")
    return lines


def _pairs(counter):
    return ", ".join(f"{k} {v}" for k, v in sorted((counter or {}).items(), key=lambda kv: str(kv[0])))
