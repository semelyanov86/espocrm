#!/usr/bin/env python3
"""Run ON the source host as root (Q-20). stdin: mysql --batch TSV `uniqueid, calldate, recordingpath, src, dst`
from asteriskcdrdb.cdr. Matches WAV files to Master.csv rows by the local start minute and the numbers encoded
in the file name (`<YYYY.MM.DD_HH-MM>_From.<src>_To.<dst>.wav`, written by sub-monitor in host-local time).
The method is first validated on MySQL rows whose recordingpath is known, then applied to WAVs without a
MySQL row. Prints only counts: no numbers, ids or file names."""
import csv
import os
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone

MASTER = "/var/log/asterisk/cdr-csv/Master.csv"
MONITOR = "/var/spool/asterisk/monitor"
NAME = re.compile(r"^(\d{4})\.(\d{2})\.(\d{2})_(\d{2})-(\d{2})_From\.(.*?)_To\.(.*?)\.wav$")


def local_minute_from_utc(ts):
    dt = datetime.fromisoformat(ts[:19]).replace(tzinfo=timezone.utc).astimezone()
    return dt.replace(second=0, microsecond=0, tzinfo=None)


def parse_wav(path):
    m = NAME.match(os.path.basename(path))
    if not m:
        return None
    y, mo, d, h, mi, frm, to = m.groups()
    return datetime(int(y), int(mo), int(d), int(h), int(mi)), frm, to


mysql = [l.rstrip("\n").split("\t") for l in sys.stdin][1:]
known = {r[2]: r[0] for r in mysql if len(r) >= 5 and r[2] not in ("", "NULL")}  # wav -> uniqueid
mysql_uids = {r[0] for r in mysql}

csv_rows = [r for r in csv.reader(open(MASTER, newline="", encoding="utf-8", errors="replace")) if len(r) > 16]
by_key = {}
for r in csv_rows:
    # fields: 1 src, 2 dst, 9 start (UTC), 16 uniqueid
    by_key.setdefault((local_minute_from_utc(r[9]), r[1]), []).append(r)
csv_only = [r for r in csv_rows if r[16] not in mysql_uids]

wavs = [os.path.join(dp, f) for dp, _d, fs in os.walk(MONITOR) for f in fs]
stats = Counter()


def candidates(parsed, tol_minutes):
    """Rows with the same local minute (± tolerance) and caller; the callee breaks ties if several remain."""
    when, frm, to = parsed
    out = []
    for delta in range(-tol_minutes, tol_minutes + 1):
        out += by_key.get((when + timedelta(minutes=delta), frm), [])
    if len({r[16] for r in out}) > 1:
        narrowed = [r for r in out if r[2] == to]
        out = narrowed or out
    return out


for w in wavs:
    parsed = parse_wav(w)
    if parsed is None:
        stats["name_unparsed"] += 1
        continue
    kind = "validation" if w in known else "unreferenced"
    exact = candidates(parsed, 0)
    near = exact or candidates(parsed, 1)
    uids = {r[16] for r in near}
    if kind == "validation":
        stats["validation_total"] += 1
        stats["validation_correct_uid" if known[w] in uids else "validation_wrong_or_none"] += 1
        stats["validation_ambiguous" if len(uids) > 1 else "validation_unique"] += 1
    else:
        stats["unreferenced_total"] += 1
        if not near:
            stats["unreferenced_no_csv_match"] += 1
        elif len(uids) == 1:
            stats["unreferenced_unique_match" + ("" if exact else "_pm1min")] += 1
            stats["unreferenced_match_in_csv_only_rows" if next(iter(uids)) not in mysql_uids else "unreferenced_match_in_mysql_rows"] += 1
        else:
            stats["unreferenced_ambiguous"] += 1

# legs of CSV-only calls: rows sharing uniqueid
uid_counts = Counter(r[16] for r in csv_only)
stats["csv_only_rows"] = len(csv_only)
stats["csv_only_distinct_uniqueid"] = len(uid_counts)
stats["csv_only_rows_in_multi_row_uniqueid"] = sum(v for v in uid_counts.values() if v > 1)
stats["csv_only_first_month"] = min(r[9][:7] for r in csv_only) if csv_only else ""
stats["csv_only_last_month"] = max(r[9][:7] for r in csv_only) if csv_only else ""
for k in sorted(stats):
    print(f"{k}\t{stats[k]}")
