#!/usr/bin/env python3
"""Run ON the source host with read access to Apache logs. Aggregates Vtiger usage from the
serv.itvolga.com access logs: counts per module/view|action and per PDF template id, plus the
date range covered. No IPs, user names, record ids or query values other than module/view/action
names and template ids are printed."""
import glob
import gzip
import re
import sys
from collections import Counter
from urllib.parse import parse_qs, urlsplit

pattern = sys.argv[1] if len(sys.argv) > 1 else "/var/log/apache2/server.itvolga_access.log*"
line_re = re.compile(r'\[(\d{2}/\w{3}/\d{4}):[^\]]+\] "(?:GET|POST) (\S+) [^"]*" (\d{3})')
usage = Counter()
templates = Counter()
dates = []
for path in sorted(glob.glob(pattern)):
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = line_re.search(line)
            if not m:
                continue
            day, url, status = m.groups()
            dates.append(day)
            qs = parse_qs(urlsplit(url).query)
            module = qs.get("module", [""])[0]
            if not module:
                continue
            what = qs.get("view", qs.get("action", [""]))[0]
            mode = qs.get("mode", [""])[0]
            usage[(module, what, mode, status[0] + "xx")] += 1
            for key in ("templateid", "template_id", "pdftemplateid"):
                if key in qs:
                    templates[(module, what, qs[key][0])] += 1

print("kind\tmodule\tview_or_action\tmode\tstatus\tcount")
for (module, what, mode, st), n in sorted(usage.items()):
    print(f"usage\t{module}\t{what}\t{mode}\t{st}\t{n}")
for (module, what, tid), n in sorted(templates.items()):
    print(f"template\t{module}\t{what}\t{tid}\t\t{n}")
if dates:
    print(f"range\t{dates[0]}\t{dates[-1]}\t\t\t{len(dates)}")
