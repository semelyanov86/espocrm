"""The Asterisk CDR history (stage 07.2, docs/migration/import.md «История звонков», D-175…D-177): the MySQL table
`asteriskcdrdb.cdr`, `Master.csv` and the monitor inventory of a verified snapshot → the calls to write and the fate
of every MySQL row, CSV line and recording file. Pure: no I/O, no values in messages or counters.

- A MySQL row is keyed by (uniqueid, sequence); a CSV line that matches one by the D-20 composite key (uniqueid, the
  CSV start converted from UTC to the host's local time, dst, dstchannel, billsec) is the same CDR row — it gives the
  row its exact UTC times and is not a call of its own.
- Legs of one call: MySQL by `linkedid`; CSV-only lines by `uniqueid` — the key of the call (the first channel's
  uniqueid is the linkedid: verified on the MySQL rows). Channel names are never matched across rows (PJSIP counters
  repeat within days). A CSV line that ended after the snapshot boundary T0 is left for the next snapshot.
- A call is written only as the live integration would write it (owner's answer 2026-10-17, D-165): the first channel
  is an inbound-class trunk (inbound), or a desk phone that dials a CRM trunk (outbound). Trainer, internal,
  conference, voicemail, Local-first calls get a reason. The rules are the installation's own (TrackerSettings).
- A human answer is a Dial leg with ANSWERED; an answer of the voice menu is not one.
- Recordings: the `recordingpath` of a MySQL row, else (CSV-only calls) D-31 — the local minute (±1) and the caller of
  the file name, the callee breaks ties. A file claimed by two calls, a header-only file (no audio, owner's answer
  2026-10-17), a file missing from the snapshot are attached to no call.
"""
import datetime as dt
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo

import transforms as T

CDR_TZ = ZoneInfo("Europe/Berlin")  # host time of `calldate` and of the recording names (/etc/localtime, 2026-10-17)
MONITOR = "/var/spool/asterisk/monitor/"
HEADER_ONLY = 44                    # a WAV of the header only: no audio
CSV_FIELDS = ("accountcode", "src", "dst", "dcontext", "clid", "channel", "dstchannel", "lastapp", "lastdata", "start",
              "answer", "end", "duration", "billsec", "disposition", "amaflags", "uniqueid", "userfield")
DISPOSITION = {"ANSWERED": "ANSWER", "NO ANSWER": "NOANSWER", "BUSY": "BUSY", "FAILED": "FAILED",
               "CONGESTION": "CONGESTION"}
TRAINER_NUMBERS, VOICEMAIL_NUMBERS, CONFERENCE_NUMBERS = ("555", "777"), ("808", "908"), ("811",)
NUMBER_RE = re.compile(r"^\+?[0-9]{1,30}$")
LINE_RE = re.compile(r"^[0-9]{3,15}$")
NAME_RE = re.compile(r"^(\d{4})\.(\d{2})\.(\d{2})_(\d{2})-(\d{2})_From\.(.*?)_To\.(.*?)\.wav$")
DATETIME = "%Y-%m-%d %H:%M:%S"
GAP_D16 = ("2024-08", "2026-05")    # months without any source (D-16): 2024-07-31 … 2026-06-12

# Fate of every column of asteriskcdrdb.cdr (the whole-snapshot ledger; prefixes of ledger.FATE_CLASSES).
COLUMN_FATES = {
    "id": "только ключ записи: номер строки CDR MySQL (в приватном отчёте)",
    "uniqueid": "только ключ записи: строка CDR (uniqueid, sequence), ключ звонка CSV",
    "sequence": "только ключ записи: строка CDR (uniqueid, sequence)",
    "linkedid": "только ключ записи: Call.cAsteriskLinkedId (плечи одного звонка)",
    "calldate": "перенос: Call.dateStart/dateEnd (местное время АТС Europe/Berlin → UTC; у строки с парой в CSV — время CSV)",
    "duration": "перенос: Call.dateEnd (начало + duration)",
    "billsec": "перенос: Call.cBillDuration, cAnsweredAt",
    "disposition": "перенос: Call.status, cCallStatusRaw",
    "src": "перенос: Call.cPhoneNumber входящего, звонящий для сопоставления записи (D-31)",
    "dst": "перенос: Call.cPhoneNumber исходящего, cIncomingLine",
    "channel": "перенос: направление звонка, внутренний номер звонящего",
    "dstchannel": "перенос: ответственный и участники (телефоны, которые звонили и ответили)",
    "dcontext": "перенос: признак класса звонка (тренажёр, конференция, линия), отдельного поля нет",
    "lastapp": "перенос: признак ответа человека (плечо Dial) и класса звонка, отдельного поля нет",
    "recordingpath": "перенос: Call.cRecordingPath/cRecording после проверки размера и sha256",
    "clid": "исключено: имя и номер звонящего — то же, что src (Call.cPhoneNumber)",
    "lastdata": "исключено: аргументы приложения диалплана (строки набора, параметры)",
    "amaflags": "исключено: служебный флаг учёта Asterisk",
    "accountcode": "исключено: диалпланом не заполняется",
    "peeraccount": "исключено: диалпланом не заполняется",
    "userfield": "исключено: диалпланом не заполняется",
}
CARRIED = ("calldate", "duration", "billsec", "disposition", "src", "dst", "channel", "dstchannel", "dcontext", "lastapp",
           "recordingpath")
KEYS = ("id", "uniqueid", "sequence", "linkedid")


class CdrError(Exception):
    """A plan-level problem (closed code, never a value)."""


# --- rules of the installation ---------------------------------------------------------------------------------------

class Rules:
    """TrackerSettings of the installation (the writer's `telephonyRules`): the same classification as the listener."""

    ENDPOINT_RE = re.compile(r"PJSIP/(.+)-[0-9a-f]{8}")

    def __init__(self, data):
        try:
            self.extension = re.compile(data["extensionPattern"])
        except (KeyError, TypeError, re.error):
            raise CdrError("extension_pattern") from None
        self.trunks = dict(data.get("trunks") or {})
        self.inbound_contexts = tuple(data.get("inboundContexts") or ())
        self.originate_prefix = data.get("originatePrefix") or "crm-"
        self.local_area_code = data.get("localAreaCode") or ""

    def endpoint_of(self, channel):
        m = self.ENDPOINT_RE.fullmatch(channel or "")
        return m.group(1) if m else None

    def is_extension(self, endpoint):
        return endpoint is not None and self.extension.search(endpoint) is not None

    def trunk_class(self, endpoint):
        return self.trunks.get(endpoint) if endpoint is not None else None

    def is_crm_trunk(self, endpoint):
        return self.trunk_class(endpoint) == "inbound"

    def is_inbound_context(self, context):
        return context in self.inbound_contexts


# --- rows ------------------------------------------------------------------------------------------------------------

@dataclass
class Leg:
    source: str                  # mysql | csv
    ref: tuple                   # ("mysql", id) | ("csv", line number)
    uniqueid: str
    linkedid: str | None
    sequence: int | None
    start: dt.datetime           # UTC, naive
    end: dt.datetime
    answer: dt.datetime | None   # UTC (CSV only)
    duration: int
    billsec: int
    src: str
    dst: str
    dcontext: str
    channel: str
    dstchannel: str
    lastapp: str
    disposition: str
    recordingpath: str | None = None
    calldate: str | None = None  # MySQL: the local time as stored (the D-20 key)
    alias: "Leg | None" = None   # MySQL: its CSV line
    exact_utc: bool = True       # MySQL without a CSV line: UTC derived from the host zone

    def order(self):
        return self.start, self.sequence or 0, self.ref


def _int(value, code):
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError):
        raise CdrError(code) from None
    if number < 0:
        raise CdrError(code)
    return number


def _utc(value, code):
    try:
        return dt.datetime.strptime((value or "")[:19], DATETIME)
    except ValueError:
        raise CdrError(code) from None


def local_text(utc):
    """UTC → the host's local 'YYYY-MM-DD HH:MM:SS' (the form of MySQL calldate)."""
    return utc.replace(tzinfo=dt.timezone.utc).astimezone(CDR_TZ).strftime(DATETIME)


def mysql_leg(row, flags):
    """A row of `cdr` read by source.SourceDb ({'cdr.<column>': str | None})."""
    g = lambda c: row.get(f"cdr.{c}")  # noqa: E731
    local = g("calldate")
    start = _utc(T.zone_to_utc(T.local_datetime(local), CDR_TZ, flags), "mysql_calldate")
    duration = _int(g("duration"), "mysql_duration")
    return Leg("mysql", ("mysql", _int(g("id"), "mysql_id")), g("uniqueid") or "", g("linkedid") or None,
               _int(g("sequence"), "mysql_sequence") if g("sequence") is not None else None, start,
               start + dt.timedelta(seconds=duration), None, duration, _int(g("billsec"), "mysql_billsec"),
               g("src") or "", g("dst") or "", g("dcontext") or "", g("channel") or "", g("dstchannel") or "",
               g("lastapp") or "", g("disposition") or "", g("recordingpath") or None, calldate=local[:19],
               exact_utc=False)


def csv_leg(number, fields):
    if len(fields) != len(CSV_FIELDS):
        raise CdrError("csv_shape")
    r = dict(zip(CSV_FIELDS, fields))
    start = _utc(r["start"], "csv_start")
    duration = _int(r["duration"], "csv_duration")
    end = max(_utc(r["end"], "csv_end"), start + dt.timedelta(seconds=duration))
    answer = _utc(r["answer"], "csv_answer") if r["answer"].strip() else None
    if not r["uniqueid"]:
        raise CdrError("csv_uniqueid")
    return Leg("csv", ("csv", number), r["uniqueid"], None, None, start, end, answer, duration,
               _int(r["billsec"], "csv_billsec"), r["src"], r["dst"], r["dcontext"], r["channel"], r["dstchannel"],
               r["lastapp"], r["disposition"])


def mysql_key(leg):
    return leg.uniqueid, leg.calldate, leg.dst, leg.dstchannel, leg.billsec


def csv_key(leg):
    return leg.uniqueid, local_text(leg.start), leg.dst, leg.dstchannel, leg.billsec


# --- groups, classes, facts ------------------------------------------------------------------------------------------

@dataclass
class Group:
    key: str                      # cAsteriskLinkedId: MySQL linkedid, CSV-only uniqueid
    source: str                   # mysql | csv
    legs: list
    direction: str | None = None  # Inbound | Outbound when written
    reason: str | None = None     # why not written
    facts: dict = field(default_factory=dict)
    recording: str | None = None  # relative path of the attached candidate
    recording_reason: str | None = None

    @property
    def first(self):
        """Rows of the first channel: its uniqueid is the key (every CSV-only row of the group)."""
        return [l for l in self.legs if l.uniqueid == self.key] if self.source == "mysql" else list(self.legs)

    @property
    def month(self):
        return min(l.start for l in self.legs).strftime("%Y-%m")


def label(group, rules):
    """Why a call that is neither external inbound nor outbound is not written (report only)."""
    legs = group.legs
    if any(l.dcontext == "german-training" or l.lastapp == "AGI" or l.dst in TRAINER_NUMBERS for l in legs):
        return "trainer"
    if any(l.dcontext == "conf-room" or l.lastapp == "ConfBridge" or l.dst in CONFERENCE_NUMBERS for l in legs):
        return "conference"
    if any(l.lastapp == "VoiceMail" or l.dst in VOICEMAIL_NUMBERS for l in legs):
        return "voicemail"
    if any(rules.is_extension(l.dst) for l in legs):
        return "internal"
    return None


def classify(group, rules):
    """→ (direction, None) or (None, reason): the first channel decides, as in the live tracker (D-165)."""
    first = group.first
    if not first:
        return None, "no_first_channel"
    root = first[0]
    if root.channel.startswith("Local/"):
        return None, label(group, rules) or "local_first"
    endpoint = rules.endpoint_of(root.channel)
    trunk = rules.trunk_class(endpoint)
    if trunk == "inbound":
        return "Inbound", None
    if trunk == "ignored":
        return None, "trainer"
    if rules.is_extension(endpoint):
        for leg in first:
            if leg.lastapp != "Dial" or not leg.dstchannel:
                continue
            target = rules.endpoint_of(leg.dstchannel)
            if rules.is_crm_trunk(target):
                return "Outbound", None
            if rules.trunk_class(target) == "ignored":
                return None, "trainer"
            if rules.is_extension(target):
                return None, "internal"
        return None, label(group, rules) or "not_dialled"
    return None, "other"


def _fmt(value):
    return value.strftime(DATETIME) if value is not None else None


def facts(group, rules):
    """The facts of a written call (HistoryCall on the PHP side validates them again)."""
    legs = sorted(group.legs, key=Leg.order)
    first = sorted(group.first, key=Leg.order)
    root = first[0]
    dials = [l for l in legs if l.lastapp == "Dial" and l.dstchannel]
    caller = answered_ext = line = None
    rung = []
    if group.direction == "Outbound":
        caller = rules.endpoint_of(root.channel)
        dials = [l for l in dials if rules.is_crm_trunk(rules.endpoint_of(l.dstchannel))]
        number = dials[0].dst if dials else root.dst
        answered = next((l for l in dials if l.disposition == "ANSWERED"), None)
    else:
        number = root.src
        for leg in dials:
            ext = rules.endpoint_of(leg.dstchannel)
            if rules.is_extension(ext) and ext not in rung:
                rung.append(ext)
        answered = next((l for l in dials if l.disposition == "ANSWERED"), None)
        ext = rules.endpoint_of(answered.dstchannel) if answered else None
        answered_ext = ext if rules.is_extension(ext) else None  # the mobile of the overflow: a human, not a phone
        entry = next((l for l in first if rules.is_inbound_context(l.dcontext)), None)
        line = entry.dst if entry is not None and LINE_RE.match(entry.dst) else None
    if answered is not None:
        raw = "ANSWER"
        answer_at = answered.alias.answer if answered.alias is not None and answered.alias.answer else answered.answer
        answer_at = answer_at or answered.end - dt.timedelta(seconds=answered.billsec)
        bill = answered.billsec
    else:
        raw = DISPOSITION.get(dials[-1].disposition, "FAILED") if dials else "NODIAL"
        answer_at, bill = None, 0
    start, end = min(l.start for l in legs), max(l.end for l in legs)
    answer_at = min(max(answer_at, start), end) if answer_at is not None else None
    bill = min(bill, int((end - start).total_seconds()))
    return {
        "direction": group.direction, "dateStart": _fmt(start), "dateEnd": _fmt(end), "answeredAt": _fmt(answer_at),
        "billSeconds": bill, "rawStatus": raw, "numberRaw": number if NUMBER_RE.match(number or "") else None,
        "line": line, "clickToCall": group.key.startswith(rules.originate_prefix),
        "callerExtension": caller, "answeredExtension": answered_ext, "rungExtensions": rung,
    }


# --- recordings ------------------------------------------------------------------------------------------------------

def parse_name(rel):
    m = NAME_RE.match(rel.rsplit("/", 1)[-1])
    if not m:
        return None
    y, mo, d, h, mi, frm, to = m.groups()
    try:
        return dt.datetime(int(y), int(mo), int(d), int(h), int(mi)), frm, to
    except ValueError:
        return None


def local_minute(utc):
    return utc.replace(tzinfo=dt.timezone.utc).astimezone(CDR_TZ).replace(second=0, tzinfo=None)


def d31_candidates(index, parsed):
    """D-31: the local minute and the caller of the file name; the callee breaks ties; ±1 minute only when the exact
    minute gives nothing. → candidate (key, callee) pairs."""
    when, frm, to = parsed

    def around(tolerance):
        out = []
        for delta in range(-tolerance, tolerance + 1):
            out += index.get((when + dt.timedelta(minutes=delta), frm), [])
        if len({k for k, _ in out}) > 1:
            out = [c for c in out if c[1] == to] or out
        return out

    return around(0) or around(1)


# --- the plan --------------------------------------------------------------------------------------------------------

class HistoryOp:
    """The writer operation of one call (`callHistory`); quacks like spec.Op for importer.bridge."""

    entityType, module, file, skip, pending, vtigerId = "Call", "CDR", None, None, None, None

    def __init__(self, group, recording):
        self.group = group
        self.key = f"cdr:{group.key}"
        self.recording = recording    # {"path", "size", "sha256"} | None (the importer may drop it after placement)
        self.outcomes = []

    def payload(self):
        return {"op": "callHistory", "key": self.key, "linkedId": self.group.key, "source": self.group.source,
                **self.group.facts, "recording": dict(self.recording) if self.recording else None}


@dataclass
class CdrPlan:
    ops: list
    groups: list
    rows: dict        # ("mysql", id) → fate
    lines: dict       # line number → fate
    files: dict       # relative path → fate
    flags: Counter
    problems: list = field(default_factory=list)
    census: dict = field(default_factory=dict)
    t0: str | None = None
    nonempty: dict = field(default_factory=dict)     # ("mysql", id) → its non-empty columns (value accounting)
    line_month: dict = field(default_factory=dict)   # line number → month of its start (UTC)
    inventory: dict = field(default_factory=dict)    # relative path → (size, sha256) of the monitor part
    csv_present: bool = True


def build(mysql_rows, csv_records, inventory, rules, t0):
    """`mysql_rows`: rows of `cdr` ({'cdr.<column>': …}); `csv_records`: [(line number, fields)] of Master.csv;
    `inventory`: {relative path: (size, sha256)} of the monitor part; `rules`: Rules; `t0`: the snapshot boundary (UTC,
    naive datetime) — CSV lines that ended later wait for the next snapshot."""
    flags, rows, lines, files, problems = Counter(), {}, {}, {}, []
    mysql, nonempty = [], {}
    for row in mysql_rows:
        leg = mysql_leg(row, flags)  # a broken row of the sealed table is a problem: CdrError stops the plan
        mysql.append(leg)
        nonempty[leg.ref] = sorted(k.split(".", 1)[1] for k, v in row.items() if not T.is_empty(v))
    if len({(l.uniqueid, l.sequence) for l in mysql}) != len(mysql):
        raise CdrError("mysql_key_not_unique")
    csv = []
    for number, fields in csv_records:
        try:
            csv.append(csv_leg(number, fields))
        except CdrError as e:
            lines[number] = f"invalid:{e}"
    # D-20: a CSV line with the composite key of a MySQL row is that row
    by_key = defaultdict(list)
    for leg in mysql:
        by_key[mysql_key(leg)].append(leg)
    csv_by_key = defaultdict(list)
    for leg in csv:
        csv_by_key[csv_key(leg)].append(leg)
    csv_only = []
    for key, legs in csv_by_key.items():
        twins = by_key.get(key, [])
        if len(legs) > 1 or len(twins) > 1:
            for leg in legs:
                lines[leg.ref[1]] = "ambiguous_key"
            continue
        if twins:
            twins[0].alias = legs[0]
            twins[0].start, twins[0].end = legs[0].start, max(legs[0].end, twins[0].end)
            twins[0].exact_utc = True
            lines[legs[0].ref[1]] = "duplicate_of_mysql"
        else:
            csv_only.append(legs[0])
    flags["mysql_utc_from_csv"] = sum(1 for l in mysql if l.alias is not None)
    owners = defaultdict(set)  # a channel's uniqueid (or a call's linkedid) → the MySQL calls it belongs to
    groups = defaultdict(list)
    for leg in mysql:
        groups[("mysql", leg.linkedid or leg.uniqueid)].append(leg)
        owners[leg.uniqueid].add(leg.linkedid or leg.uniqueid)
        owners[leg.linkedid or leg.uniqueid].add(leg.linkedid or leg.uniqueid)
    after_t0 = []
    for leg in csv_only:
        if leg.end > t0:
            lines[leg.ref[1]] = "after_t0"
            after_t0.append(leg)
        elif len(owners.get(leg.uniqueid, ())) == 1:
            # a leg of a MySQL call the table does not have (no row with its composite key): it joins that call
            groups[("mysql", next(iter(owners[leg.uniqueid])))].append(leg)
            flags["csv_leg_joined_mysql"] += 1
        elif leg.uniqueid in owners:
            lines[leg.ref[1]] = "conflict_with_mysql"  # its uniqueid belongs to several MySQL calls: never guessed
        else:
            groups[("csv", leg.uniqueid)].append(leg)
    plan_groups = []
    for (source, key), legs in sorted(groups.items(), key=lambda kv: min(l.order() for l in kv[1])):
        group = Group(key, source, sorted(legs, key=Leg.order))
        group.direction, group.reason = classify(group, rules)
        if group.direction:
            group.facts = facts(group, rules)
        plan_groups.append(group)
    match_recordings(plan_groups, after_t0, inventory, files, flags)
    ops = []
    for group in plan_groups:
        if group.direction is None:
            continue
        recording = None
        if group.recording is not None:
            size, sha256 = inventory[group.recording]
            recording = {"path": group.recording, "size": size, "sha256": sha256}
        ops.append(HistoryOp(group, recording))
    for group in plan_groups:
        for leg in group.legs:
            fate = "call" if group.direction else f"not_imported:{group.reason}"
            if leg.source == "mysql":
                rows[leg.ref] = fate
            else:
                lines[leg.ref[1]] = fate
    flags.update(f"class:{g.direction or g.reason}" for g in plan_groups)
    return CdrPlan(ops, plan_groups, rows, lines, files, flags, problems, t0=t0.strftime(DATETIME), nonempty=nonempty,
                   line_month={leg.ref[1]: leg.start.strftime("%Y-%m") for leg in csv}, inventory=inventory)


def match_recordings(groups, after_t0, inventory, files, flags):
    """The recording of every call (`group.recording` or `group.recording_reason`) and the fate of every file."""
    claims, referenced = defaultdict(list), set()
    by_key = {g.key: g for g in groups}
    for group in groups:
        paths = {l.recordingpath for l in group.legs if l.recordingpath}
        if not paths:
            continue
        rels = {p[len(MONITOR):] for p in paths if p.startswith(MONITOR)}
        referenced |= rels
        if len(paths) > 1:
            group.recording_reason = "ambiguous_paths"
            for rel in rels:
                claims[rel].append(None)  # claimed by a call that cannot have it
            continue
        if not rels:
            group.recording_reason = "outside_monitor"
            continue
        rel = rels.pop()
        if rel not in inventory:
            group.recording_reason = "missing_in_snapshot"
            continue
        claims[rel].append(group.key)
    # D-31 sees every call (and the CSV lines after T0) as a candidate owner of a file name; a file no MySQL row names
    # goes only to a CSV-only call — the file of a MySQL call without recordingpath is never given to another call
    index, roots = defaultdict(list), {}
    for group in groups:
        first = group.first or group.legs
        root = first[0].alias or first[0]
        roots[group.key] = (local_minute(root.start), root.src, root.dst)
        index[(roots[group.key][0], root.src)].append((group.key, root.dst))
    for leg in after_t0:
        key = f"after_t0:{leg.ref[1]}"
        roots[key] = (local_minute(leg.start), leg.src, leg.dst)
        index[(roots[key][0], leg.src)].append((key, leg.dst))
    validation, ambiguous = Counter(), set()
    for rel in sorted(inventory):
        parsed = parse_name(rel)
        if rel in referenced:
            # the same name built for another call (same local minute, caller and callee): the file was written twice
            if parsed is not None:
                claims[rel] += [k for k, r in roots.items() if r == parsed and k not in claims[rel]]
            continue
        if parsed is None:
            files[rel] = "name_unparsed"
            continue
        keys = {k for k, _ in d31_candidates(index, parsed)}
        if not keys:
            files[rel] = "no_match"
        elif len(keys) > 1:
            files[rel] = "ambiguous"
            ambiguous |= keys
        else:
            key = keys.pop()
            if key in by_key and by_key[key].source != "csv":
                files[rel] = "mysql_call_without_path"  # D-31 is for CSV-only calls (D-31, D-177)
            else:
                claims[rel].append(key)
    # D-31 checked on the files MySQL names (the audit's validation, counts only)
    full = defaultdict(list)
    for group in groups:
        for leg in group.legs:
            root = leg.alias or leg
            full[(local_minute(root.start), root.src)].append((group.key, root.dst))
    for rel in referenced:
        parsed = parse_name(rel) if rel in inventory else None
        owners = {k for k in claims.get(rel, []) if k}
        if parsed is None or len(owners) != 1:
            continue
        found = {k for k, _ in d31_candidates(full, parsed)}
        validation["d31_check_correct" if found == owners else "d31_check_ambiguous" if owners <= found
                   else "d31_check_wrong"] += 1
    flags.update(validation)
    for rel, keys in claims.items():
        owners = set(keys)
        if len(owners) > 1 or None in owners:
            files[rel] = "claimed_twice"
            for k in owners - {None}:
                if k in by_key:
                    by_key[k].recording_reason = "claimed_twice"
                    by_key[k].recording = None
            continue
        key = owners.pop()
        if key.startswith("after_t0:"):
            files[rel] = "call_after_t0"
            continue
        group = by_key[key]
        if inventory[rel][0] <= HEADER_ONLY:
            files[rel] = "without_audio"
            group.recording_reason = "without_audio"
        elif group.direction is None:
            files[rel] = f"no_call:{group.reason}"
        else:
            files[rel] = "candidate"
            group.recording = rel
    for rel in inventory:
        files.setdefault(rel, "no_match")
    for group in groups:
        if group.direction and group.recording is None and group.recording_reason is None:
            group.recording_reason = "ambiguous_d31" if group.key in ambiguous else "none"
