#!/usr/bin/env python3
"""Run ON the source host. Reads TSV `attachmentsid, setype, deleted, path, name` from stdin
(produced by mysql) and prints only aggregate counts: which attachment rows have a file on
disk, how much space they use, and which storage files are not referenced by any row.
No file names, paths or contents are printed."""
import html
import os
import sys
from collections import Counter, defaultdict

ROOT = sys.argv[1] if len(sys.argv) > 1 else "/var/www/serv_itvolga/vtiger7"

found = Counter()
missing = Counter()
sizes = defaultdict(int)
variant_used = Counter()
referenced = set()

next(sys.stdin)  # header
for line in sys.stdin:
    parts = line.rstrip("\n").split("\t")
    if len(parts) < 5:
        continue
    att_id, setype, deleted, path, name = parts[:5]
    key = f"{setype}|deleted={deleted}"
    candidates = [name, html.unescape(name), name.replace(" ", "_"), html.unescape(name).replace(" ", "_")]
    hit = None
    for idx, cand in enumerate(candidates):
        p = os.path.join(ROOT, path, f"{att_id}_{cand}")
        if os.path.isfile(p):
            hit = p
            variant_used[idx] += 1
            break
    if hit is None:
        # 7.2+ style: stored name is just the id (with optional extension); check prefix match.
        d = os.path.join(ROOT, path)
        if os.path.isdir(d):
            for fn in os.listdir(d):
                if fn == att_id or fn.startswith(att_id + "_"):
                    hit = os.path.join(d, fn)
                    variant_used["prefix"] += 1
                    break
    if hit:
        found[key] += 1
        sizes[key] += os.path.getsize(hit)
        referenced.add(os.path.realpath(hit))
    else:
        missing[key] += 1

print("kind\tkey\tfound\tmissing\tbytes_found")
for key in sorted(set(found) | set(missing)):
    print(f"attachment\t{key}\t{found[key]}\t{missing[key]}\t{sizes[key]}")
print(f"match_variant\t{dict(variant_used)}\t\t\t")

storage = os.path.join(ROOT, "storage")
orphans = Counter()
orphan_bytes = Counter()
total = Counter()
total_bytes = Counter()
for dirpath, _dirs, files in os.walk(storage):
    rel = os.path.relpath(dirpath, storage).split(os.sep)
    year = rel[0] if rel and rel[0] != "." else "(root)"
    for fn in files:
        p = os.path.join(dirpath, fn)
        if fn in (".htaccess", "index.html"):
            continue
        sz = os.path.getsize(p)
        total[year] += 1
        total_bytes[year] += sz
        if os.path.realpath(p) not in referenced:
            orphans[year] += 1
            orphan_bytes[year] += sz
for year in sorted(total):
    print(f"storage_year\t{year}\t{total[year]}\t{orphans[year]}\t{total_bytes[year]}\t{orphan_bytes[year]}")
