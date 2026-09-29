#!/usr/bin/env python3
"""Run ON the source host as root (Q-05). stdin: `login_time` values from vtiger_loginhistory (recent window).
Compares them with Apache timestamps of Vtiger login POSTs and prints only the offset (DB - UTC) in hours."""
import glob
import gzip
import re
import sys
from collections import Counter
from datetime import datetime, timezone

logins = []
next(sys.stdin, None)
for line in sys.stdin:
    try:
        logins.append(datetime.strptime(line.strip()[:19].replace("/", "-"), "%Y-%m-%d %H:%M:%S"))
    except ValueError:
        pass
rx = re.compile(r'\[(\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2}) ([+-]\d{4})\] "POST /index\.php\?module=Users&(?:parent=Settings&)?action=Login')
events = []
for path in glob.glob("/var/log/apache2/server.itvolga_access.log*"):
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt", errors="replace") as fh:
        for line in fh:
            m = rx.search(line)
            if m:
                events.append(datetime.strptime(f"{m.group(1)} {m.group(2)}", "%d/%b/%Y:%H:%M:%S %z")
                              .astimezone(timezone.utc).replace(tzinfo=None))
off = Counter()
for e in events:
    if logins:
        best = min(logins, key=lambda t: abs((t - e).total_seconds()))
        off[round((best - e).total_seconds() / 3600)] += 1
print(f"login_posts\t{len(events)}")
print(f"db_minus_utc_hours\t{dict(off)}")
