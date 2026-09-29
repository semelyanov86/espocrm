#!/usr/bin/env python3
"""Run ON the source host. Reads mysql --batch (escaped) TSV `kind, id, name, module, company, body`
and prints, per template, only metadata: size, sha256 prefix, placeholder tokens and counts of
number patterns that look like hard-coded requisites. Template text itself is never printed."""
import hashlib
import re
import sys

TOKEN_DOLLAR = re.compile(r"\$[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)?\$")
TOKEN_BRACE = re.compile(r"\{\$?[A-Za-z_][A-Za-z0-9_.|:]*\}")
TOKEN_LOOP = re.compile(r"(?i)(?:\{(?:foreach|if|/foreach|/if)[^}]{0,60}\}|#[A-Z_]{3,}#)")
PATTERNS = {
    "digits20": re.compile(r"(?<!\d)\d{20}(?!\d)"),   # bank/correspondent account
    "digits9": re.compile(r"(?<!\d)\d{9}(?!\d)"),     # BIC / KPP
    "digits10_12": re.compile(r"(?<!\d)(?:\d{10}|\d{12})(?!\d)"),  # INN
    "img_tags": re.compile(r"(?i)<img\b"),
    "tables": re.compile(r"(?i)<table\b"),
}


def unescape(value):
    return (value.replace("\\n", "\n").replace("\\t", "\t").replace("\\0", "\0").replace("\\\\", "\\"))


print("kind\tid\tname\tmodule\tcompany\tbytes\tsha256_12\t" + "\t".join(PATTERNS) + "\ttokens\tcontrol")
header = True
for line in sys.stdin:
    if header:
        header = False
        continue
    parts = line.rstrip("\n").split("\t")
    if len(parts) < 6:
        continue
    kind, tid, name, module, company = parts[:5]
    body = unescape("\t".join(parts[5:]))
    if body == "NULL":
        body = ""
    tokens = sorted(set(TOKEN_DOLLAR.findall(body)) | set(TOKEN_BRACE.findall(body)))
    control = sorted(set(m.strip() for m in TOKEN_LOOP.findall(body)))
    counts = [str(len(p.findall(body))) for p in PATTERNS.values()]
    digest = hashlib.sha256(body.encode("utf-8", "surrogateescape")).hexdigest()[:12]
    print("\t".join([kind, tid, name, module, company, str(len(body.encode("utf-8", "surrogateescape"))), digest]
                    + counts + [" ".join(tokens), " ".join(control)]))
