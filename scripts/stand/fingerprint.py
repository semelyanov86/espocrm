#!/usr/bin/env python3
"""Whole-stand fingerprint (stage 06.4, docs/migration/import.md «Прерывание и повтор»): `CHECKSUM TABLE` of every base
table of the stand database except the journals the stand writes by itself (VOLATILE), and size + sha256 of every file
of the upload storage. Two fingerprints are equal when nothing of the stand changed between them — the proof that a
repeated import wrote nothing. Private JSON only (file names are attachment ids); the console shows counts and the
digest of the fingerprint.

  fingerprint.py take LABEL            → /data/itvolga/espo-private/stand/fingerprints/<time>-<label>.json
  fingerprint.py diff A.json B.json    → tables and files that differ (names and counts)
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "snapshot"))
from common import Mysql, SnapshotError, write_private  # noqa: E402

ROOT = Path(os.environ.get("FINGERPRINT_ROOT", "/data/itvolga/espo-private/stand/fingerprints"))
DATABASE = "espocrm"
# Tables the stand writes on its own while nobody works with it (cron, scheduler, sessions); calibrated on the idle
# stand 2026-10-12 (two fingerprints minutes apart, cron running) — evidence.md «Этап 06.4».
VOLATILE = ("job", "scheduled_job", "scheduled_job_log_record", "auth_token", "auth_log_record")
NAME_RE = re.compile(r"^[a-z0-9_]+$")
LABEL_RE = re.compile(r"^[A-Za-z0-9_-]{1,40}$")
UPLOAD = REPO / "data" / "upload"


def tables():
    sql = ("SET SESSION TRANSACTION READ ONLY;\nSELECT table_name FROM information_schema.tables "
           f"WHERE table_schema = '{DATABASE}' AND table_type = 'BASE TABLE' ORDER BY table_name;\n")
    names = [line.decode("ascii") for line in Mysql.stand().lines(sql, ROOT / "logs" / "stand.log")]
    if any(not NAME_RE.match(n) for n in names):
        raise SnapshotError("unexpected table name")
    return names


def checksums(names):
    sql = "".join(f"CHECKSUM TABLE `{DATABASE}`.`{n}` EXTENDED;\n" for n in names)
    out = {}
    for line in Mysql.stand().lines(sql, ROOT / "logs" / "stand.log"):
        table, value = line.decode("ascii").split("\t")
        if value == "NULL":
            raise SnapshotError(f"CHECKSUM TABLE gave NULL for {table}")
        out[table.split(".", 1)[1]] = value
    if set(out) != set(names):
        raise SnapshotError("CHECKSUM TABLE did not answer for every table")
    return out


def uploads():
    """relative path → [size, sha256] of every file of data/upload (read as root: the files belong to the stand); a
    fresh installation has no data/upload until its first file (stage 08) — an empty storage."""
    script = ('[ -d "$0" ] || exit 0; '
              'cd "$0" && find . -type f -printf "%s\\t%P\\0" | while IFS=$\'\\t\' read -r -d "" size path; do '
              'printf "%s\\t%s\\t%s\\n" "$size" "$(sha256sum -- "$path" | cut -d" " -f1)" '
              '"$(printf %s "$path" | od -An -tx1 | tr -d " \\n")"; done')
    res = subprocess.run(["sudo", "-n", "bash", "-c", script, str(UPLOAD)], capture_output=True, text=True,
                         check=False)
    if res.returncode != 0:
        raise SnapshotError("listing data/upload failed")
    out = {}
    for line in res.stdout.splitlines():
        size, digest, path_hex = line.split("\t")
        out[bytes.fromhex(path_hex).decode("utf-8", "replace")] = [int(size), digest]
    return out


def take(label):
    if not LABEL_RE.match(label):
        raise SnapshotError("bad label")
    names = tables()
    data = {"taken_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "volatile": list(VOLATILE),
            "tables": checksums([n for n in names if n not in VOLATILE]), "uploads": uploads()}
    data["digest"] = hashlib.sha256(json.dumps({k: data[k] for k in ("tables", "uploads")},
                                               sort_keys=True).encode()).hexdigest()
    ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = ROOT / f"{time.strftime('%Y%m%dT%H%M%S')}-{label}.json"
    write_private(path, json.dumps(data, sort_keys=True))
    return path, data


def diff(a, b):
    tables_changed = sorted(t for t in set(a["tables"]) | set(b["tables"]) if a["tables"].get(t) != b["tables"].get(t))
    files = {"added": len(b["uploads"].keys() - a["uploads"].keys()),
             "removed": len(a["uploads"].keys() - b["uploads"].keys()),
             "changed": sum(1 for k in a["uploads"].keys() & b["uploads"].keys() if a["uploads"][k] != b["uploads"][k])}
    return {"equal": not tables_changed and not any(files.values()), "tables": tables_changed, "files": files}


def main():
    os.umask(0o077)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("take")
    t.add_argument("label")
    d = sub.add_parser("diff")
    d.add_argument("a")
    d.add_argument("b")
    args = ap.parse_args()
    try:
        if args.cmd == "take":
            path, data = take(args.label)
            print(f"[fingerprint] {len(data['tables'])} tables, {len(data['uploads'])} files, digest "
                  f"{data['digest'][:16]} → {path}", file=sys.stderr)
            return 0
        result = diff(*(json.loads(Path(p).read_text(encoding="utf-8")) for p in (args.a, args.b)))
        print(f"[fingerprint] equal: {result['equal']}; tables: {', '.join(result['tables']) or 'none'}; "
              f"files: {result['files']}", file=sys.stderr)
        return 0 if result["equal"] else 2
    except SnapshotError as e:
        print(f"[fingerprint] ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
