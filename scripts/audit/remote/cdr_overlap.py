#!/usr/bin/env python3
"""Run ON the source host as root. stdin: mysql --batch TSV `uniqueid, linkedid, calldate, recordingpath`
from asteriskcdrdb.cdr. Compares with /var/log/asterisk/cdr-csv/Master.csv and the WAV files in the
monitor directory. Prints only counts (no numbers, ids or file names)."""
import csv
import os
import sys
from collections import Counter

MASTER = "/var/log/asterisk/cdr-csv/Master.csv"
MONITOR = "/var/spool/asterisk/monitor"

mysql_rows = []
next(sys.stdin)
for line in sys.stdin:
    parts = line.rstrip("\n").split("\t")
    if len(parts) >= 4:
        mysql_rows.append(parts)
mysql_uids = {r[0] for r in mysql_rows}
mysql_linked = {r[1] for r in mysql_rows}
rec_paths = {r[3] for r in mysql_rows if r[3] not in ("", "NULL")}

csv_uids = set()
csv_rows = 0
csv_fields = Counter()
with open(MASTER, newline="", encoding="utf-8", errors="replace") as fh:
    for row in csv.reader(fh):
        csv_rows += 1
        csv_fields[len(row)] += 1
        # Default cdr_csv layout: uniqueid is field 17 (index 16).
        if len(row) > 16:
            csv_uids.add(row[16])

wavs = set()
for dirpath, _d, files in os.walk(MONITOR):
    for fn in files:
        wavs.add(os.path.join(dirpath, fn))

print(f"mysql_rows\t{len(mysql_rows)}")
print(f"mysql_distinct_uniqueid\t{len(mysql_uids)}")
print(f"mysql_distinct_linkedid\t{len(mysql_linked)}")
print(f"csv_rows\t{csv_rows}")
print(f"csv_field_counts\t{dict(csv_fields)}")
print(f"csv_distinct_uniqueid\t{len(csv_uids)}")
print(f"uniqueid_in_both\t{len(mysql_uids & csv_uids)}")
print(f"uniqueid_csv_only\t{len(csv_uids - mysql_uids)}")
print(f"uniqueid_mysql_only\t{len(mysql_uids - csv_uids)}")
print(f"mysql_recordingpath_distinct\t{len(rec_paths)}")
print(f"mysql_recordingpath_exists\t{len([p for p in rec_paths if os.path.isfile(p)])}")
print(f"mysql_recordingpath_missing\t{len([p for p in rec_paths if not os.path.isfile(p)])}")
print(f"wav_total\t{len(wavs)}")
print(f"wav_not_referenced_by_mysql\t{len(wavs - rec_paths)}")
