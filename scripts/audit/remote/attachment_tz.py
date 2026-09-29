#!/usr/bin/env python3
"""Run ON the source host as root (Q-05). stdin: mysql --batch --raw TSV `attachmentsid, createdtime, path, name`
of live attachments. File mtimes (preserved by rsync from the old server) are an independent UTC reference, so
DB createdtime - mtime reveals the time zone Vtiger used when writing timestamps. Prints only offsets and dates
of the era boundaries (no names, ids or paths)."""
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

ROOT = sys.argv[1] if len(sys.argv) > 1 else "/var/www/serv_itvolga/vtiger7"
pts = []
next(sys.stdin, None)
for line in sys.stdin:
    p = line.rstrip("\n").split("\t")
    if len(p) < 4:
        continue
    aid, created, path, name = p[:4]
    f = os.path.join(ROOT, path, f"{aid}_{name}")
    if not os.path.isfile(f):
        continue
    ct = datetime.strptime(created[:19], "%Y-%m-%d %H:%M:%S")
    mt = datetime.fromtimestamp(os.path.getmtime(f), timezone.utc).replace(tzinfo=None)
    pts.append((ct, round((ct - mt).total_seconds() / 3600)))
pts.sort()
dist = defaultdict(Counter)
for ct, d in pts:
    dist[f"{ct.year}-{'H1' if ct.month <= 6 else 'H2'}"][d] += 1
for k in sorted(dist):
    print(f"offset_hours_by_halfyear\t{k}\t{dict(dist[k])}")
moscow = [c for c, d in pts if d == 3]
berlin = [c for c, d in pts if d in (1, 2)]
utc = [c for c, d in pts if d == 0]
print(f"last_utc_plus3\t{max(moscow).date() if moscow else ''}")
print(f"first_cet_cest\t{min(berlin).date() if berlin else ''}")
print(f"last_cet_cest\t{max(berlin).date() if berlin else ''}")
print(f"first_utc\t{min(utc).date() if utc else ''}")
