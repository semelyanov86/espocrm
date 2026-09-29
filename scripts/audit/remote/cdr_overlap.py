#!/usr/bin/env python3
"""Run ON the source host as root. stdin: mysql --batch TSV
`uniqueid, linkedid, calldate, recordingpath, dst, dstchannel, billsec, sequence` from asteriskcdrdb.cdr.
Compares with /var/log/asterisk/cdr-csv/Master.csv and the WAV files in the monitor directory.
`uniqueid` is NOT unique per CDR row (one call can produce several rows), so rows are compared by the
composite key (uniqueid, start time, dst, dstchannel, billsec). Verified on 2026-09-29: Master.csv stores
start time in UTC while MySQL calldate is host-local time, so CSV times are converted to local time first.
Prints only counts."""
import csv
import os
import sys
from collections import Counter
from datetime import datetime, timezone


def csv_local(ts):
    """Master.csv start (UTC) -> host-local 'YYYY-MM-DD HH:MM:SS' comparable with MySQL calldate."""
    try:
        return datetime.fromisoformat(ts[:19]).replace(tzinfo=timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return ts[:19]


MASTER = "/var/log/asterisk/cdr-csv/Master.csv"
MONITOR = "/var/spool/asterisk/monitor"

mysql_rows = []
next(sys.stdin)
for line in sys.stdin:
    parts = line.rstrip("\n").split("\t")
    if len(parts) >= 8:
        mysql_rows.append(parts)
mysql_uids = {r[0] for r in mysql_rows}
mysql_linked = {r[1] for r in mysql_rows}
rec_paths = {r[3] for r in mysql_rows if r[3] not in ("", "NULL")}
mysql_keys = Counter((r[0], r[2][:19], r[4], r[5], r[6]) for r in mysql_rows)
mysql_seq = Counter((r[0], r[7]) for r in mysql_rows)

csv_rows = []
csv_fields = Counter()
with open(MASTER, newline="", encoding="utf-8", errors="replace") as fh:
    for row in csv.reader(fh):
        csv_fields[len(row)] += 1
        if len(row) > 16:
            csv_rows.append(row)
# Default cdr_csv layout: 2 dst, 6 dstchannel, 9 start, 13 billsec, 16 uniqueid.
csv_uids = {r[16] for r in csv_rows}
csv_keys = Counter((r[16], csv_local(r[9]), r[2], r[6], r[13]) for r in csv_rows)
csv_keys_utc = Counter((r[16], r[9][:19], r[2], r[6], r[13]) for r in csv_rows)

wavs = set()
for dirpath, _d, files in os.walk(MONITOR):
    for fn in files:
        wavs.add(os.path.join(dirpath, fn))

mk, ck = set(mysql_keys), set(csv_keys)
print(f"mysql_rows\t{len(mysql_rows)}")
print(f"mysql_distinct_uniqueid\t{len(mysql_uids)}")
print(f"mysql_distinct_linkedid\t{len(mysql_linked)}")
print(f"mysql_distinct_row_key\t{len(mk)}")
print(f"mysql_rows_sharing_row_key\t{sum(v for v in mysql_keys.values() if v > 1)}")
print(f"mysql_distinct_uniqueid_sequence\t{len(mysql_seq)}")
print(f"csv_rows\t{len(csv_rows)}")
print(f"csv_field_counts\t{dict(csv_fields)}")
print(f"csv_distinct_uniqueid\t{len(csv_uids)}")
print(f"csv_distinct_row_key\t{len(ck)}")
print(f"csv_rows_sharing_row_key\t{sum(v for v in csv_keys.values() if v > 1)}")
print(f"uniqueid_in_both\t{len(mysql_uids & csv_uids)}")
print(f"uniqueid_csv_only\t{len(csv_uids - mysql_uids)}")
print(f"uniqueid_mysql_only\t{len(mysql_uids - csv_uids)}")
print(f"row_key_in_both_without_tz_conversion\t{len(mk & set(csv_keys_utc))}")
print(f"row_key_in_both\t{len(mk & ck)}")
print(f"row_key_csv_only\t{len(ck - mk)}")
print(f"row_key_mysql_only\t{len(mk - ck)}")
print(f"mysql_recordingpath_distinct\t{len(rec_paths)}")
print(f"mysql_recordingpath_exists\t{len([p for p in rec_paths if os.path.isfile(p)])}")
print(f"mysql_recordingpath_missing\t{len([p for p in rec_paths if not os.path.isfile(p)])}")
print(f"wav_total\t{len(wavs)}")
print(f"wav_not_referenced_by_mysql\t{len(wavs - rec_paths)}")
