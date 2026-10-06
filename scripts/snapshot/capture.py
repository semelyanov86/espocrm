"""Capture: the database parts in one READ ONLY consistent-snapshot session, then the file parts.

Production is only read: SELECT / SHOW CREATE TABLE inside `START TRANSACTION WITH CONSISTENT
SNAPSHOT, READ ONLY`; files are listed by an inline script and copied by rsync (sudo rsync is the
sender). Nothing is written on the server. See docs/migration/snapshot.md, «Границы согласованности».
"""
import base64
import gzip
import os
import re
import secrets
import shlex
import shutil
import subprocess
import time
from decimal import Decimal
from pathlib import Path

import codec
from common import (SOURCE_HOST, SSH_OPTS, SnapshotError, log, mib, sha256_file, ssh_argv, write_json,
                    write_private)

HERE = Path(__file__).resolve().parent
FILE_LIST = HERE / "remote" / "file_list.py"
MAX_ROW_BYTES = 24 * 1048576       # hex doubles a row; the server's max_allowed_packet is 64M

# File parts: source root, paths below it, whether files newer than the database boundary are left out.
FILE_PARTS = [
    {"name": "vtiger", "root": "/var/www/serv_itvolga/vtiger7", "paths": ["storage", "test/logo", "test/upload"],
     "boundary": True},
    {"name": "cdr-csv", "root": "/var/log/asterisk/cdr-csv", "paths": ["."], "boundary": False},
    {"name": "monitor", "root": "/var/spool/asterisk/monitor", "paths": ["."], "boundary": True},
]
ALLOWED_STATEMENT = re.compile(
    r"^(SET SESSION (TRANSACTION READ ONLY|TRANSACTION ISOLATION LEVEL REPEATABLE READ|time_zone='\+00:00'|"
    r"net_write_timeout=\d+)|START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY|COMMIT|"
    r"SHOW CREATE TABLE `\w+`\.`\w+`|SELECT .*);$")
FORBIDDEN = re.compile(r"(?i)\b(INTO|FOR UPDATE|FOR SHARE|LOCK|GET_LOCK|SLEEP|INSERT|UPDATE|DELETE|DROP|CREATE TABLE)\b")


def lint(script):
    """The capture script is generated; refuse anything that is not a read (defence in depth)."""
    for n, stmt in enumerate(script.splitlines(), 1):
        if not ALLOWED_STATEMENT.match(stmt):
            raise SnapshotError(f"capture script line {n}: statement not allowed")
        body = re.sub(r"`[^`]*`", "``", re.sub(r"'[^']*'", "''", stmt))  # literals and identifiers aside
        if stmt.startswith("SELECT") and FORBIDDEN.search(body):
            raise SnapshotError(f"capture script line {n}: forbidden keyword")


class Sections:
    """Splits client output into marker-delimited sections: `#vtsnap#<nonce>#kind#arg...[\\tvalue...]`."""

    def __init__(self, nonce, on_section):
        self.prefix = f"#vtsnap#{nonce}#".encode()
        self.on_section = on_section
        self.head = None
        self.body = []

    def __call__(self, line):
        if line.startswith(self.prefix):
            self.flush()
            parts = line.split(b"\t")
            self.head = (parts[0][len(self.prefix):].decode("ascii").split("#"),
                         [p.decode("ascii") for p in parts[1:]])
            self.body = []
        elif self.head is None:
            raise SnapshotError("unexpected client output outside a section")
        else:
            self.body.append(line)

    def flush(self):
        if self.head is not None:
            (kind, *args), values = self.head
            self.on_section(kind, args, values, self.body)
            self.head, self.body = None, []


def _marker(nonce, *parts):
    return "#vtsnap#" + nonce + "#" + "#".join(parts)


# --- plan ------------------------------------------------------------------------------------

def plan(mysql, schemas, logdir):
    """Server settings and the structural catalogue (one READ ONLY session), then the longest row
    of every table (second session). Refuses unsupported schema objects before any data is read."""
    nonce = secrets.token_hex(8)
    script = ["SET SESSION TRANSACTION READ ONLY;",
              f"SELECT '{_marker(nonce, 'server')}',VERSION(),@@global.time_zone,@@system_time_zone,"
              "@@global.sql_mode,@@lower_case_table_names,@@max_allowed_packet,@@global.transaction_isolation,"
              "@@innodb_strict_mode,@@explicit_defaults_for_timestamp,@@log_bin,@@gtid_mode;"]
    for s in schemas:
        script.append(codec.catalogue_sql(s, _marker(nonce, "catalogue", "plan", s)))
    script.append(f"SELECT '{_marker(nonce, 'eos')}';")
    got = {}

    def on_section(kind, args, values, body):
        got[(kind, *args)] = (values, body)

    sink = Sections(nonce, on_section)
    mysql.session("\n".join(script) + "\n", sink, logdir / "plan.log")
    sink.flush()
    if ("eos",) not in got:
        raise SnapshotError("plan session ended without its end marker")
    keys = ["version", "time_zone", "system_time_zone", "sql_mode", "lower_case_table_names", "max_allowed_packet",
            "transaction_isolation", "innodb_strict_mode", "explicit_defaults_for_timestamp", "log_bin", "gtid_mode"]
    server = dict(zip(keys, got[("server",)][0]))
    if not re.fullmatch(r"[A-Z_,]*", server["sql_mode"]):
        raise SnapshotError("unexpected sql_mode format")
    catalogues = {}
    for s in schemas:
        cat = codec.parse_catalogue(got[("catalogue", "plan", s)][1])
        if not cat["tables"]:
            raise SnapshotError(f"schema {s}: no tables")
        problems = codec.unsupported(cat)
        if problems:
            raise SnapshotError(f"schema {s}: unsupported objects: " + "; ".join(problems[:10]))
        catalogues[s] = cat

    # Longest row bound (sum of the longest string/binary values): hex must fit the packet limit.
    nonce2 = secrets.token_hex(8)
    script = ["SET SESSION TRANSACTION READ ONLY;"]
    for s, cat in catalogues.items():
        for t, cols in sorted(cat["columns"].items()):
            wide = [c for c in cols if c["class"] in ("string", "binary")]
            if wide:
                expr = "+".join(f"IFNULL(MAX(LENGTH({codec.ident(c['name'])})),0)" for c in wide)
                script.append(f"SELECT '{_marker(nonce2, 'maxrow', s, t)}',{expr} FROM {codec.ident(s)}.{codec.ident(t)};")
    script.append(f"SELECT '{_marker(nonce2, 'eos')}';")
    widest = {"bytes": 0, "table": ""}

    def on_max(kind, args, values, body):
        if kind == "eos":
            widest["eos"] = True
        elif int(values[0]) > widest["bytes"]:
            widest.update(bytes=int(values[0]), table=".".join(args))

    sink = Sections(nonce2, on_max)
    mysql.session("\n".join(script) + "\n", sink, logdir / "plan.log")
    sink.flush()
    if not widest.get("eos"):
        raise SnapshotError("plan session ended without its end marker")
    if widest["bytes"] > MAX_ROW_BYTES:
        raise SnapshotError(f"row of {widest['table']} too long for the codec ({mib(widest['bytes'])})")
    return {"server": server, "catalogues": catalogues, "widest_row_bytes": widest["bytes"]}


# --- database capture ------------------------------------------------------------------------

def capture_script(nonce, catalogues, nontx):
    s = ["SET SESSION TRANSACTION READ ONLY;",
         "SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ;",
         "SET SESSION time_zone='+00:00';",
         "SET SESSION net_write_timeout=600;",
         "START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY;",
         f"SELECT '{_marker(nonce, 'begin')}',DATE_FORMAT(UTC_TIMESTAMP(6),'%Y-%m-%dT%H:%i:%s.%fZ'),"
         "UNIX_TIMESTAMP(NOW(6)),@@session.transaction_read_only,@@session.transaction_isolation;"]
    for schema in catalogues:
        s.append(codec.catalogue_sql(schema, _marker(nonce, "catalogue", "begin", schema)))
    for schema, table in nontx:
        cols = catalogues[schema]["columns"][table]
        s.append(codec.stat_sql(schema, table, cols, _marker(nonce, "nontx", "begin", schema, table)))
    for schema, cat in catalogues.items():
        for table in sorted(cat["tables"]):
            cols = cat["columns"][table]
            s.append(f"SELECT '{_marker(nonce, 'ddl', schema, table)}';")
            s.append(f"SHOW CREATE TABLE {codec.ident(schema)}.{codec.ident(table)};")
            s.append(f"SELECT '{_marker(nonce, 'rows', schema, table)}';")
            s.append(codec.rows_sql(schema, table, cols))
            s.append(codec.stat_sql(schema, table, cols, _marker(nonce, "stat", schema, table)))
    for schema, table in nontx:
        cols = catalogues[schema]["columns"][table]
        s.append(codec.stat_sql(schema, table, cols, _marker(nonce, "nontx", "end", schema, table)))
    for schema in catalogues:
        s.append(codec.catalogue_sql(schema, _marker(nonce, "catalogue", "end", schema)))
    s.append(f"SELECT '{_marker(nonce, 'end')}',DATE_FORMAT(UTC_TIMESTAMP(6),'%Y-%m-%dT%H:%i:%s.%fZ'),"
             "UNIX_TIMESTAMP(NOW(6));")
    s.append("COMMIT;")
    s.append(f"SELECT '{_marker(nonce, 'eos')}';")
    script = "\n".join(s) + "\n"
    lint(script)
    return script


def write_rows(path, lines):
    """Canonical rows file: lines sorted bytewise, each ended by LF, gzip without name/mtime."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
        for line in lines:
            gz.write(line + b"\n")


def capture_db(mysql, planned, staging):
    """One session, one InnoDB read view for every schema. Writes db/<schema>/{ddl,rows}/ and
    db/<schema>/tables.json; returns the boundary description."""
    catalogues = planned["catalogues"]
    nontx = [(s, t) for s, cat in catalogues.items() for t, info in sorted(cat["tables"].items())
             if info["engine"] != "InnoDB"]
    nonce = secrets.token_hex(8)
    script = capture_script(nonce, catalogues, nontx)
    state = {"begin": None, "end": None, "eos": False, "catalogue": {}, "nontx": {}, "tables": {}}
    pending = {}

    def on_section(kind, args, values, body):
        if kind in ("begin", "end"):
            state[kind] = values
        elif kind == "eos":
            state["eos"] = True
        elif kind == "catalogue":
            state["catalogue"][(args[0], args[1])] = codec.fingerprint(body)
        elif kind == "nontx":
            state["nontx"][(args[0], args[1], args[2])] = values
        elif kind == "ddl":
            if len(body) != 1:
                raise SnapshotError(f"{args[0]}.{args[1]}: unexpected DDL output")
            ddl = codec.fields(body[0])[1]
            if not codec.single_create_table(ddl, args[1]):
                raise SnapshotError(f"{args[0]}.{args[1]}: DDL is not a single CREATE TABLE statement")
            write_private(staging / "db" / args[0] / "ddl" / f"{args[1]}.sql", ddl + "\n")
        elif kind == "rows":
            schema, table = args
            ncols = len(catalogues[schema]["columns"][table])
            for n, line in enumerate(body, 1):
                if not codec.check_line(line, ncols):
                    raise SnapshotError(f"{schema}.{table}: invalid row line {n} (value too long or bad output)")
            body.sort()
            path = staging / "db" / schema / "rows" / f"{table}.hex.gz"
            write_rows(path, body)
            pending[(schema, table)] = {"rows": len(body), "lanes": codec.lanes_of(body)}
        elif kind == "stat":
            schema, table = args
            got = pending.pop((schema, table), None)
            if got is None or got["rows"] != int(values[0]) or got["lanes"] != values[1:5]:
                raise SnapshotError(f"{schema}.{table}: rows received differ from the server count/digest")
            state["tables"][(schema, table)] = {"rows": got["rows"], "lanes": got["lanes"], "column_counts": values[5]}
        else:
            raise SnapshotError(f"unexpected section {kind}")

    log(f"capture: one READ ONLY transaction over {', '.join(catalogues)} "
        f"({sum(len(c['tables']) for c in catalogues.values())} tables)")
    sink = Sections(nonce, on_section)
    started = time.monotonic()
    mysql.session(script, sink, staging / "logs" / "capture.log")
    sink.flush()
    duration = time.monotonic() - started

    if not state["eos"] or not state["begin"] or not state["end"]:
        raise SnapshotError("capture session ended without its markers")
    if state["begin"][2] != "1":
        raise SnapshotError("capture transaction was not read-only")
    for schema, cat in catalogues.items():
        fps = {cat["fingerprint"], state["catalogue"].get(("begin", schema)), state["catalogue"].get(("end", schema))}
        if len(fps) != 1:
            raise SnapshotError(f"schema {schema} changed during the export (DDL); run again")
        missing = [t for t in cat["tables"] if (schema, t) not in state["tables"]]
        if missing:
            raise SnapshotError(f"schema {schema}: {len(missing)} tables without data/digest")
    for schema, table in nontx:
        b, e = state["nontx"].get(("begin", schema, table)), state["nontx"].get(("end", schema, table))
        mid = state["tables"][(schema, table)]
        if not b or not e or b[:5] != e[:5] or b[0] != str(mid["rows"]) or b[1:5] != mid["lanes"]:
            raise SnapshotError(f"non-transactional table {schema}.{table} changed during the export; run again")

    for schema, cat in catalogues.items():
        tables = {}
        for table, info in sorted(cat["tables"].items()):
            got = state["tables"][(schema, table)]
            rows_file = staging / "db" / schema / "rows" / f"{table}.hex.gz"
            ddl_file = staging / "db" / schema / "ddl" / f"{table}.sql"
            tables[table] = {
                "engine": info["engine"],
                "consistency": "read-view" if info["engine"] == "InnoDB" else "stable-window",
                "columns": [{k: c[k] for k in ("name", "data_type", "column_type", "charset", "class")}
                            for c in cat["columns"][table]],
                "rows": got["rows"], "lanes": got["lanes"], "column_counts": got["column_counts"],
                "rows_file": f"rows/{table}.hex.gz", "rows_bytes": rows_file.stat().st_size,
                "ddl_file": f"ddl/{table}.sql", "ddl_sha256": sha256_file(ddl_file),
            }
        write_json(staging / "db" / schema / "tables.json", tables)
        write_private(staging / "db" / schema / "catalogue.fingerprint", cat["fingerprint"] + "\n")

    begin_epoch, end_epoch = Decimal(state["begin"][1]), Decimal(state["end"][1])
    return {
        "kind": "innodb-read-view",
        "schemas": list(catalogues),
        "begin_utc": state["begin"][0], "end_utc": state["end"][0],
        "begin_epoch": str(begin_epoch), "end_epoch": str(end_epoch),
        "duration_s": round(duration, 1),
        "read_only": True, "isolation": state["begin"][3],
        "catalogue_fingerprints": {s: c["fingerprint"] for s, c in catalogues.items()},
        "non_transactional": [f"{s}.{t}" for s, t in nontx],
        "tables": sum(len(c["tables"]) for c in catalogues.values()),
        "rows": sum(v["rows"] for v in state["tables"].values()),
    }


# --- files -----------------------------------------------------------------------------------

def parse_file_list(data):
    """Records of remote/file_list.py: sha256|unstable, size, mtime_ns, relpath (bytes)."""
    files, meta = {}, {"symlinks": 0, "special": 0, "missing_paths": 0}
    for rec in data.split(b"\0"):
        if not rec:
            continue
        if rec.startswith(b"#summary\t"):
            _, sl, sp = rec.split(b"\t")
            meta.update(symlinks=int(sl), special=int(sp))
        elif rec.startswith(b"#missing\t"):
            meta["missing_paths"] += 1
        else:
            digest, size, mtime, rel = rec.split(b"\t", 3)
            files[rel] = (digest.decode("ascii"), int(size), int(mtime))
    return files, meta


def remote_file_list(root, paths, errlog):
    b64 = base64.b64encode(FILE_LIST.read_bytes()).decode("ascii")
    code = f"import base64;exec(compile(base64.b64decode('{b64}'),'file_list.py','exec'))"
    cmd = "sudo -n nice -n 19 ionice -c3 python3 -c " + " ".join(shlex.quote(a) for a in [code, root, *paths])
    with open(errlog, "ab") as err:
        r = subprocess.run(ssh_argv(cmd), stdout=subprocess.PIPE, stderr=err)
    if r.returncode != 0:
        raise SnapshotError(f"file listing on the source failed (exit {r.returncode})")
    return r.stdout


def local_file_list(root, paths, errlog):
    with open(errlog, "ab") as err:
        r = subprocess.run(["python3", "-I", str(FILE_LIST), str(root), *paths], stdout=subprocess.PIPE, stderr=err)
    if r.returncode != 0:
        raise SnapshotError("local file listing failed")
    return r.stdout


def capture_part(part, boundary_ns, staging, attempts=3):
    dest = staging / "files" / part["name"]
    logs = staging / "logs"
    for attempt in range(1, attempts + 1):
        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir(parents=True)
        listed_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        host, meta = parse_file_list(remote_file_list(part["root"], part["paths"], logs / f"files-{part['name']}.log"))
        if meta["missing_paths"]:
            raise SnapshotError(f"files {part['name']}: {meta['missing_paths']} configured paths absent on the source")
        inside = {rel: v for rel, v in host.items() if not part["boundary"] or v[2] <= boundary_ns}
        unstable = [rel for rel, v in inside.items() if v[0] == "unstable"]
        if unstable:
            log(f"files {part['name']}: {len(unstable)} files changing while listed; attempt {attempt}")
            time.sleep(10)
            continue
        if inside:
            listfile = staging / "work" / f"{part['name']}.files"
            write_private(listfile, b"\0".join(sorted(inside)) + b"\0")
            rsync = ["rsync", "--from0", f"--files-from={listfile}", "-t", "-p", "--chmod=D700,F600",
                     "--rsync-path=sudo -n nice -n 19 ionice -c3 rsync", "-e", "ssh " + " ".join(SSH_OPTS),
                     f"{SOURCE_HOST}:{part['root']}/", f"{dest}/"]
            with open(logs / f"files-{part['name']}.log", "ab") as err:
                r = subprocess.run(rsync, stdout=err, stderr=err)
            if r.returncode in (23, 24):
                log(f"files {part['name']}: rsync reported vanished/partial files; attempt {attempt}")
                continue
            if r.returncode != 0:
                raise SnapshotError(f"files {part['name']}: rsync failed (exit {r.returncode})")
        local, _ = parse_file_list(local_file_list(dest, part["paths"], logs / f"files-{part['name']}.log"))
        want = {rel: (v[0], v[1]) for rel, v in inside.items()}
        have = {rel: (v[0], v[1]) for rel, v in local.items()}
        if want != have:
            diff = len(set(want.items()) ^ set(have.items()))
            log(f"files {part['name']}: {diff} copies differ from the source listing; attempt {attempt}")
            continue
        inventory = "".join(f"{rel.hex()}\t{v[1]}\t{v[2]}\t{v[0]}\n" for rel, v in sorted(inside.items()))
        write_private(staging / "inventory" / f"{part['name']}.tsv", inventory)
        summary = {
            "root": part["root"], "paths": part["paths"], "listed_utc": listed_utc,
            "policy": "mtime<=db.end" if part["boundary"] else "whole files at listing time",
            "host_files": len(host), "host_bytes": sum(v[1] for v in host.values()),
            "files": len(inside), "bytes": sum(v[1] for v in inside.values()),
            "after_boundary": len(host) - len(inside), "attempts": attempt, **meta,
        }
        log(f"files {part['name']}: {summary['files']} files, {mib(summary['bytes'])}; "
            f"after the boundary {summary['after_boundary']}")
        return summary
    raise SnapshotError(f"files {part['name']}: no stable copy after {attempts} attempts")


def capture_files(boundary_ns, staging, parts=FILE_PARTS):
    return {p["name"]: capture_part(p, boundary_ns, staging) for p in parts}


def boundary_ns(db):
    return int(Decimal(db["end_epoch"]) * 1_000_000_000)
