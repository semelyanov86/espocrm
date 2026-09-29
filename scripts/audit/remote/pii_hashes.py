#!/usr/bin/env python3
"""Run ON the source host. stdin: mysql --batch TSV `kind, value` with personal/secret values.
Prints only sha256 hashes of normalised values (one per line, deduplicated), never the values.
The hash list is stored privately and used by scripts/check_secrets.py to prove that no real
personal data from the CRM ended up in Git."""
import hashlib
import re
import sys

MIN_TEXT = 5
MIN_DIGITS = 7


def norm_text(v):
    return re.sub(r"\s+", " ", v.strip().lower())


def digits(v):
    return re.sub(r"\D", "", v)


def h(v):
    return hashlib.sha256(v.encode("utf-8")).hexdigest()


out = set()
next(sys.stdin, None)
for line in sys.stdin:
    parts = line.rstrip("\n").split("\t", 1)
    if len(parts) != 2:
        continue
    kind, value = parts
    if kind == "kind":  # header row of the UNION query
        continue
    value = value.replace("\\n", " ").replace("\\t", " ")
    if value in ("", "NULL"):
        continue
    t = norm_text(value)
    # Whole normalised values only: hashing single words of values gives too many generic hits.
    if len(t) >= MIN_TEXT and not t.isdigit():
        out.add("t:" + h(t))
    d = digits(value)
    if kind in ("phone", "number", "secret") and len(d) >= MIN_DIGITS:
        out.add("d:" + h(d))
        if len(d) > 10:
            out.add("d:" + h(d[-10:]))
for x in sorted(out):
    print(x)
