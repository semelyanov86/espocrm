"""Verification of a snapshot (docs/migration/snapshot.md, «Проверка»).

V1 seal and permissions; V2 every copied file against its inventory; V3 every rows file against the
count and digest the server computed inside the export transaction; V4 restore into a temporary
database of the stand MySQL (exact name, sql_log_bin=0, dropped at the end) and the same SQL there;
C* completeness: the audit SQL, consolidate.py and build_maps.py on the restored copy compared with
field-map.csv / relations.csv, attachments, the legal-entity logo and telephony.

Statuses: `fail` — the snapshot does not reproduce the source (create deletes it); `finding` — the
copy is faithful but differs from the maps or misses source files (kept, reported); `info`.
"""
import csv
import gzip
import html
import json
import os
import re
import secrets
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import codec
from common import (FILE_PART_NAMES, FORMAT, FORMAT_VERSION, REPO, SOURCE_SCHEMAS, TEMP_DB_RE, Mysql, SnapshotError, log, read_json,
                    sha256_file, tool_identity, write_json, write_private)

AUDIT = REPO / "scripts" / "audit"
MAPS = REPO / "docs" / "migration"
UNSEALED = ("files/", "reports/")
SEAL_PATH_RE = re.compile(r"^[A-Za-z0-9_.\-/]+$")
MONITOR = b"/var/spool/asterisk/monitor/"
INSERT_BATCH = 4 * 1048576


class Checks:
    def __init__(self):
        self.items = []

    def add(self, cid, title, ok, counts=None, level="fail"):
        """ok=True → pass; otherwise `level` (fail | finding). level=info records numbers only."""
        status = "info" if level == "info" else ("pass" if ok else level)
        self.items.append({"id": cid, "title": title, "status": status, "counts": counts or {}})
        log(f"{cid} {status}: {title}" + (f" — {fmt(counts)}" if counts else ""))
        return ok

    def status(self):
        st = {i["status"] for i in self.items}
        return "fail" if "fail" in st else ("findings" if "finding" in st else "pass")


def fmt(counts):
    return ", ".join(f"{k}={v}" for k, v in counts.items() if not isinstance(v, (list, dict)))


# --- seal ----------------------------------------------------------------------------------------

def sealed_files(snapdir):
    out = []
    for dirpath, dirnames, filenames in os.walk(snapdir):
        rel_dir = os.path.relpath(dirpath, snapdir)
        rel_dir = "" if rel_dir == "." else rel_dir + "/"
        dirnames[:] = [d for d in dirnames if not (rel_dir + d + "/").startswith(UNSEALED)]
        out += [rel_dir + f for f in filenames if rel_dir + f != "SHA256SUMS"]
    return sorted(out)


def write_seal(snapdir):
    lines = []
    for rel in sealed_files(snapdir):
        if not SEAL_PATH_RE.match(rel):
            raise SnapshotError("non-ASCII path among sealed files")
        lines.append(f"{sha256_file(snapdir / rel)}  {rel}\n")
    write_private(snapdir / "SHA256SUMS", "".join(lines))
    return sha256_file(snapdir / "SHA256SUMS")


def check_seal(snapdir, checks):
    listed = {}
    for line in (snapdir / "SHA256SUMS").read_text(encoding="ascii").splitlines():
        digest, rel = line.split("  ", 1)
        listed[rel] = digest
    present = set(sealed_files(snapdir))
    bad = sum(1 for rel in present & set(listed) if sha256_file(snapdir / rel) != listed[rel])
    perms = 0
    for dirpath, dirnames, filenames in os.walk(snapdir):
        for name in dirnames + filenames:
            st = os.lstat(os.path.join(dirpath, name))
            want = 0o700 if name in dirnames else 0o600
            if os.path.islink(os.path.join(dirpath, name)) or (st.st_mode & 0o777) != want or st.st_uid != os.getuid():
                perms += 1
    counts = {"sealed": len(listed), "missing": len(set(listed) - present), "extra": len(present - set(listed)),
              "mismatch": bad, "bad_permissions": perms}
    checks.add("V1", "печать SHA256SUMS и права 700/600", not any(counts[k] for k in list(counts)[1:]), counts)
    return sha256_file(snapdir / "SHA256SUMS")


# --- files ---------------------------------------------------------------------------------------

def read_inventory(snapdir, part):
    inv = {}
    for line in (snapdir / "inventory" / f"{part}.tsv").read_text(encoding="ascii").splitlines():
        rel, size, mtime, digest = line.split("\t")
        inv[bytes.fromhex(rel)] = (int(size), int(mtime), digest)
    return inv


def check_files(snapdir, manifest, checks):
    inventories = {}
    for part in manifest.get("files", {}):
        inv = read_inventory(snapdir, part)
        base = os.fsencode(snapdir / "files" / part)
        present = set()
        for dirpath, _dirs, filenames in os.walk(base):
            present |= {os.path.relpath(os.path.join(dirpath, f), base) for f in filenames}
        bad = 0
        for rel, (size, _mtime, digest) in inv.items():
            path = os.path.join(base, rel)
            if rel in present and (os.path.getsize(path) != size or sha256_file(path) != digest):
                bad += 1
        counts = {"files": len(inv), "missing": len(set(inv) - present), "extra": len(present - set(inv)),
                  "mismatch": bad}
        checks.add(f"V2.{part}", f"файлы части {part} = опись (размер, sha256)",
                   not (counts["missing"] or counts["extra"] or bad), counts)
        inventories[part] = inv
    return inventories


# --- contract ------------------------------------------------------------------------------------

def check_contract(snapdir, manifest, tables, checks, full):
    """Everything from the snapshot that later becomes SQL text or a path: schema names, sql_mode,
    charsets, engines, column classes, file names; for a full verification also the composition
    (both source databases, all file parts, every table with its DDL and rows). A resealed but altered
    snapshot must not reach the root client, nor pass as complete."""
    db = manifest["db"]
    bad = []
    if not codec.safe_sql_mode(manifest.get("source", {}).get("sql_mode")):
        bad.append("sql_mode")
    if full and (sorted(db["schemas"]) != sorted(SOURCE_SCHEMAS)
                 or sorted(manifest.get("files", {})) != sorted(FILE_PART_NAMES)):
        bad.append("composition")
    if db.get("tables") != sum(len(t) for t in tables.values()):
        bad.append("table count")
    for s in db["schemas"]:
        cs = db.get("schema_charsets", {}).get(s, ["", ""])
        if not (codec.NAME_RE.match(s) and len(cs) == 2 and all(codec.NAME_RE.match(x or "") for x in cs)):
            bad.append(f"schema {s}")
            continue
        ddl = {p.name[:-4] for p in (snapdir / "db" / s / "ddl").glob("*.sql")}
        rows = {p.name[:-7] for p in (snapdir / "db" / s / "rows").glob("*.hex.gz")}
        if not tables[s] or not (set(tables[s]) == ddl == rows):
            bad.append(f"schema {s} files")
        for t, meta in tables[s].items():
            if not (codec.NAME_RE.match(t) and meta.get("engine") in codec.ENGINES
                    and meta.get("ddl_file") == f"ddl/{t}.sql" and meta.get("rows_file") == f"rows/{t}.hex.gz"
                    and codec.valid_columns(meta.get("columns"))):
                bad.append(f"{s}.{t}")
    checks.add("V0", "контракт: состав, sql_mode, имена, движки, классы и кодировки колонок, пути", not bad,
               {"problems": len(bad), "bad": bad[:20]})
    return not bad


# --- rows ----------------------------------------------------------------------------------------

def read_lines(path):
    data = gzip.decompress(path.read_bytes())
    if data and not data.endswith(b"\n"):
        raise SnapshotError(f"{path.name}: last line not terminated")
    return data.split(b"\n")[:-1] if data else []


def check_rows(snapdir, schema, tables, checks):
    bad = []
    for table, meta in tables.items():
        lines = read_lines(snapdir / "db" / schema / meta["rows_file"])
        ncols = len(meta["columns"])
        ok = (len(lines) == meta["rows"] and lines == sorted(lines)
              and all(codec.check_line(line, ncols) for line in lines) and codec.lanes_of(lines) == meta["lanes"])
        if not ok:
            bad.append(table)
    checks.add(f"V3.{schema}", f"строки {schema}: формат, порядок, число и дайджест = данные сервера",
               not bad, {"tables": len(tables), "rows": sum(m["rows"] for m in tables.values()), "bad_tables": len(bad),
                         "bad": bad[:20]})
    return not bad


# --- temporary databases -------------------------------------------------------------------------

class TempDatabases:
    """Temporary databases on the stand MySQL: names are journalled before CREATE and dropped one by
    one by exact name (never by pattern); sql_log_bin=0 keeps production rows out of the binlog."""

    def __init__(self, root, logdir):
        self.journal = root / "tempdbs.journal"
        self.logdir = logdir
        self.label = time.strftime("%Y%m%dt%H%M%S")
        self.created = []

    def _journal(self, state, name):
        fd = os.open(self.journal, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, "a") as fh:
            fh.write(f"{state}\t{name}\n")

    def create(self, schema, charset, collation):
        name = f"vtsnap_{self.label}_{secrets.token_hex(3)}_{schema}".lower()
        if not (TEMP_DB_RE.match(name) and codec.NAME_RE.match(charset) and codec.NAME_RE.match(collation)):
            raise SnapshotError("bad temporary database name or charset")
        self._journal("created", name)
        Mysql.stand().lines(f"SET SESSION sql_log_bin=0;\nCREATE DATABASE `{name}` CHARACTER SET {charset} "
                            f"COLLATE {collation};\n", self.logdir / "restore.log")
        self.created.append(name)
        return name

    def drop_all(self):
        """Every name is dropped independently: a failed drop or a failed journal write (full disk)
        never stops the cleanup of the next database."""
        left = []
        for name in self.created:
            try:
                drop(name, self.logdir / "restore.log")
            except Exception:  # noqa: BLE001 — keep dropping the others; reported by name below
                left.append(name)
                continue
            try:
                self._journal("dropped", name)
            except OSError:
                log(f"journal not updated for the dropped {name}")
        self.created = []
        return left

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        left = self.drop_all()
        if left and exc[0] is None:
            raise SnapshotError(f"temporary databases not dropped: {', '.join(left)}")


def drop(name, errlog):
    if not TEMP_DB_RE.match(name):
        raise SnapshotError("refusing to drop a database that is not a snapshot temporary database")
    Mysql.stand().lines(f"SET SESSION sql_log_bin=0;\nDROP DATABASE `{name}`;\n", errlog)
    if existing([name], errlog):
        raise SnapshotError(f"temporary database {name} still exists")


def existing(names, errlog):
    names = [n for n in names if TEMP_DB_RE.match(n)]
    if not names:
        return []
    quoted = ",".join(f"'{n}'" for n in names)
    return [line.decode() for line in Mysql.stand().lines(
        f"SELECT schema_name FROM information_schema.schemata WHERE schema_name IN ({quoted});\n", errlog)]


def journal_leftovers(root, errlog):
    journal = root / "tempdbs.journal"
    if not journal.exists():
        return []
    state = {}
    for line in journal.read_text(encoding="ascii").splitlines():
        st, name = line.split("\t")
        state[name] = st
    return existing([n for n, st in state.items() if st == "created"], errlog)


def restore_sql(snapdir, schema, tables, sql_mode):
    if not codec.safe_sql_mode(sql_mode) or not all(codec.valid_columns(m["columns"]) for m in tables.values()):
        raise SnapshotError(f"{schema}: snapshot contract check failed; not restored")
    mode = ",".join(m for m in (sql_mode, "NO_AUTO_VALUE_ON_ZERO") if m)
    yield (f"SET SESSION sql_log_bin=0;\nSET SESSION sql_mode='{mode}';\n"
           "SET SESSION time_zone='+00:00';\nSET SESSION foreign_key_checks=0;\nSET SESSION unique_checks=0;\n"
           "SET SESSION sql_generate_invisible_primary_key=0;\nSET NAMES utf8mb4;\nSET autocommit=0;\n").encode()
    for table, meta in tables.items():
        ddl = (snapdir / "db" / schema / meta["ddl_file"]).read_text(encoding="utf-8").rstrip("\n")
        if not codec.single_create_table(ddl, table, meta["engine"]):
            raise SnapshotError(f"{schema}.{table}: DDL is not a single CREATE TABLE statement; not restored")
        yield (ddl + ";\n").encode("utf-8")
    for table, meta in tables.items():
        cols = meta["columns"]
        head = f"INSERT INTO {codec.ident(table)} ({','.join(codec.ident(c['name']) for c in cols)}) VALUES ".encode()
        batch, size = [], 0
        for line in read_lines(snapdir / "db" / schema / meta["rows_file"]):
            values = ("(" + ",".join(codec.literal(tok, col) for tok, col in zip(line.split(b"\t"), cols)) + ")").encode()
            batch.append(values)
            size += len(values) + 1
            if size >= INSERT_BATCH:
                yield head + b",".join(batch) + b";\n"
                batch, size = [], 0
        if batch:
            yield head + b",".join(batch) + b";\n"
        yield b"COMMIT;\n"


def compare_restored(snapdir, schema, tables, dbname, fingerprint, logdir, checks):
    nonce = secrets.token_hex(8)
    prefix = f"#vtsnap#{nonce}#"
    script = ["SET SESSION time_zone='+00:00';", "START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY;",
              codec.catalogue_sql(dbname, prefix + "catalogue")]
    for table, meta in tables.items():
        script.append(codec.stat_sql(dbname, table, meta["columns"], prefix + "stat#" + table))
    script += ["COMMIT;", f"SELECT '{prefix}eos';"]
    catalogue, stats, eos = [], {}, []

    def consume(line):
        if line.startswith(prefix.encode()):
            head, *values = line.decode("ascii").split("\t")
            kind = head[len(prefix):]
            if kind.startswith("stat#"):
                stats[kind[5:]] = values
            elif kind == "eos":
                eos.append(True)
            elif kind != "catalogue":
                raise SnapshotError("unexpected marker")
        else:
            catalogue.append(line)

    Mysql.stand(database=dbname).session("\n".join(script) + "\n", consume, logdir / "restore.log")
    differ = []
    for table, meta in tables.items():
        got = stats.get(table)
        if (not got or int(got[0]) != meta["rows"] or got[1:5] != meta["lanes"]
                or json.loads(got[5]) != json.loads(meta["column_counts"])):
            differ.append(table)
    same_schema = codec.fingerprint(catalogue) == fingerprint
    checks.add(f"V4.{schema}", f"восстановленная копия {schema}: схема, число строк, дайджесты и счётчики колонок",
               bool(eos) and same_schema and not differ,
               {"tables": len(tables), "differ": len(differ), "schema_equal": int(same_schema), "tables_differ": differ[:20]})


# --- completeness: audit on the restored copy and the maps ----------------------------------------

AUDIT_SQL = ["01_tabs", "02_fields", "03_columns", "04_tables", "05_primary_keys", "20_relations",
             "25_activity_workflows", "27_payments", "32_cardinality", "33_allocation_check"]
GENERATED = [("table-counts", "10_table_counts.tsv", None), ("column-counts", "11_column_counts.raw", None),
             ("field-live-counts", "12_field_live_counts.raw", None),
             ("reference-targets", "13_reference_targets.tsv", b"module\t"),
             ("picklist-values", "14_picklist_values.tsv", b"module\tfield"),
             ("table-live-counts", "15_table_live_counts.raw", None), ("max-lengths", "42_max_lengths.raw", None)]


def run_audit(dbname, auditdir, started_at, logdir):
    """The steps of scripts/audit/run-audit.sh that the map builders read, on the restored copy."""
    client = Mysql.stand(database=dbname, headers=True, raw=True)

    def run(sql, out, drop_prefix=None):
        lines = client.lines("SET SESSION TRANSACTION READ ONLY;\n" + sql, logdir / "audit.log")
        if drop_prefix:
            lines = [ln for ln in lines if not ln.startswith(drop_prefix)]
        write_private(auditdir / out, b"".join(ln + b"\n" for ln in lines))

    for name in AUDIT_SQL[:5]:
        run((AUDIT / "sql" / f"{name}.sql").read_text(encoding="utf-8"), f"{name}.tsv")
    for mode, out, drop_prefix in GENERATED:
        sql = subprocess.run([sys.executable, "-I", str(AUDIT / "gen_sql.py"), mode, str(auditdir)],
                             capture_output=True, text=True, check=True).stdout
        run(sql, out, drop_prefix)
    for name in AUDIT_SQL[5:]:
        run((AUDIT / "sql" / f"{name}.sql").read_text(encoding="utf-8"), f"{name}.tsv")
    write_private(auditdir / "started_at.txt", started_at + "\n")
    maps = auditdir / "maps"
    maps.mkdir()
    with open(logdir / "audit.log", "ab") as out:
        for cmd in (["consolidate.py", str(auditdir)], ["build_maps.py", str(auditdir), str(maps)]):
            subprocess.run([sys.executable, "-I", str(AUDIT / cmd[0]), *cmd[1:]], stdout=out, stderr=out, check=True)
    return maps


FIELD_KEY = ("source_module", "source_table", "source_column", "source_field", "uitype")
FIELD_COUNTS = ("nonempty_all_rows", "live_records", "nonempty_live", "max_len_live", "count_status")
REL_COUNTS = ("cardinality_observed", "live_count", "deleted_or_dangling", "distribution")


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def diff_rows(committed, fresh, key, counts):
    """Multiset comparison: identities present on one side only, decision columns that differ
    (target, transform, fate, status...), count columns that differ."""
    def group(rows):
        g = defaultdict(list)
        for r in rows:
            g[tuple(r[k] for k in key)].append(r)
        for v in g.values():
            v.sort(key=lambda r: tuple(r[k] for k in sorted(r) if k not in counts))
        return g
    a, b = group(committed), group(fresh)
    only_committed = sum(max(0, len(a[k]) - len(b.get(k, []))) for k in a)
    only_fresh = sum(max(0, len(b[k]) - len(a.get(k, []))) for k in b)
    decision, count, examples = 0, 0, []
    for k in a.keys() & b.keys():
        for ra, rb in zip(a[k], b[k]):
            dec = [c for c in ra if c not in counts and c not in key and ra[c] != rb.get(c)]
            if dec:
                decision += 1
                examples.append({"key": list(k), "columns": dec})
            elif any(ra[c] != rb.get(c) for c in counts if c != "count_status"):
                count += 1
    missing = [list(k) for k in a if len(b.get(k, [])) < len(a[k])]
    added = [list(k) for k in b if len(a.get(k, [])) < len(b[k])]
    return {"committed": len(committed), "fresh": len(fresh), "only_committed": only_committed,
            "only_fresh": only_fresh, "decision_changed": decision, "count_changed": count,
            "missing": missing, "added": added, "decision_examples": examples}


DERIVED = {"sp_payments.related_to ∪ vtiger_crmentityrel(Invoice,SPPayments)":
           [("sp_payments", "related_to"), ("vtiger_crmentityrel", None)]}


def relation_sources(obj):
    if obj in DERIVED:
        return DERIVED[obj]
    m = re.fullmatch(r"(\w+)(?:\.(\w+))?", obj)
    return [(m.group(1), m.group(2))] if m else None


def check_maps(maps_fresh, vtiger_tables, tabs_rows, checks, report):
    field_committed = read_csv(MAPS / "field-map.csv")
    rel_committed = read_csv(MAPS / "relations.csv")
    columns = {t: {c["name"] for c in m["columns"]} for t, m in vtiger_tables.items()}

    absent = [f"{r['source_table']}.{r['source_column']}" for r in field_committed
              if r["source_column"] not in columns.get(r["source_table"], ())]
    checks.add("C1", "каждая пара «таблица.колонка» field-map.csv есть в снимке", not absent,
               {"map_rows": len(field_committed),
                "pairs": len({(r['source_table'], r['source_column']) for r in field_committed}),
                "tables": len({r['source_table'] for r in field_committed}), "absent": len(absent)}, "finding")

    unresolved = []
    for r in rel_committed:
        src = relation_sources(r["source_object"])
        if src is None or any(t not in columns or (c and c not in columns[t]) for t, c in src):
            unresolved.append(r["relation_id"])
    checks.add("C2", "источник каждой связи relations.csv есть в снимке", not unresolved,
               {"relations": len(rel_committed), "unresolved": len(unresolved)}, "finding")

    with_records = {r["name"]: (int(r["live"]), int(r["deleted"])) for r in tabs_rows
                    if int(r["live"]) + int(r["deleted"]) > 0}
    map_modules = {r["source_module"] for r in field_committed}
    unmapped = sorted(set(with_records) - map_modules)
    checks.add("C3", "каждый модуль с записями есть в field-map.csv", not unmapped,
               {"modules_with_records": len(with_records), "live": sum(v[0] for v in with_records.values()),
                "deleted": sum(v[1] for v in with_records.values()), "unmapped": len(unmapped)}, "finding")
    report["modules"] = [{"module": m, "live": v[0], "deleted": v[1]} for m, v in sorted(with_records.items())]

    fdiff = diff_rows(field_committed, read_csv(maps_fresh / "field-map.csv"), FIELD_KEY, FIELD_COUNTS)
    rdiff = diff_rows(rel_committed, read_csv(maps_fresh / "relations.csv"), ("relation_id",), REL_COUNTS)
    report["maps"] = {"field_map": fdiff, "relations": rdiff}
    for cid, title, d in (("C4", "field-map.csv, пересобранная по снимку = карта в Git (кроме счётчиков)", fdiff),
                          ("C5", "relations.csv, пересобранная по снимку = карта в Git (кроме счётчиков)", rdiff)):
        checks.add(cid, title, not (d["only_committed"] or d["only_fresh"] or d["decision_changed"]),
                   {k: d[k] for k in ("committed", "fresh", "only_committed", "only_fresh", "decision_changed",
                                      "count_changed")}, "finding")
    report["unmapped_modules"] = unmapped
    report["absent_map_columns"] = absent
    report["unresolved_relations"] = unresolved


def parse_tsv_with_header(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="\t", quoting=csv.QUOTE_NONE))


# --- attachments, logo, telephony ------------------------------------------------------------------

ATTACHMENTS_SQL = ("SELECT a.attachmentsid,IFNULL(c.setype,'(no crmentity)'),IFNULL(c.deleted,''),"
                   "HEX(IFNULL(a.path,'')),HEX(IFNULL(a.name,'')) FROM vtiger_attachments a "
                   "LEFT JOIN vtiger_crmentity c ON c.crmid=a.attachmentsid ORDER BY a.attachmentsid;")
LOSSES_SQL = (
    "SELECT 'contact_images_without_file',COUNT(*) FROM vtiger_contactdetails d JOIN vtiger_crmentity e "
    "ON e.crmid=d.contactid AND e.deleted=0 WHERE IFNULL(d.imagename,'')<>'' AND NOT EXISTS (SELECT 1 FROM "
    "vtiger_seattachmentsrel r JOIN vtiger_crmentity ae ON ae.crmid=r.attachmentsid AND ae.setype='Contacts Image' "
    "WHERE r.crmid=d.contactid);\n"
    "SELECT 'internal_documents_without_attachment',COUNT(*) FROM vtiger_notes n JOIN vtiger_crmentity e "
    "ON e.crmid=n.notesid AND e.deleted=0 WHERE n.filelocationtype='I' AND NOT EXISTS (SELECT 1 FROM "
    "vtiger_seattachmentsrel r WHERE r.crmid=n.notesid);\n")


def _variants(name):
    text = name.decode("utf-8", "surrogateescape")
    out = [text, html.unescape(text), text.replace(" ", "_"), html.unescape(text).replace(" ", "_")]
    return list(dict.fromkeys(v.encode("utf-8", "surrogateescape") for v in out))


def resolve_attachments(rows, inventory):
    """check_attachments.py rules (4 name variants, then `<id>_` prefix), on the copied inventory;
    more than one prefix candidate is `ambiguous` instead of «first in directory order»."""
    by_dir = defaultdict(list)
    for rel in inventory:
        by_dir[os.path.dirname(rel)].append(os.path.basename(rel))
    out = []
    for att_id, setype, deleted, path_hex, name_hex in rows:
        path, name = bytes.fromhex(path_hex), bytes.fromhex(name_hex)
        folder = os.path.normpath(path) if path else b""
        status, rel = "missing", None
        if not folder.startswith(b"storage/") or b".." in folder.split(b"/"):
            status = "outside"
        else:
            for v in _variants(name):
                cand = os.path.join(folder, att_id.encode() + b"_" + v)
                if cand in inventory:
                    status, rel = "found", cand
                    break
            if rel is None:
                hits = sorted(b for b in by_dir.get(folder, []) if b == att_id.encode() or b.startswith(att_id.encode() + b"_"))
                if len(hits) == 1:
                    status, rel = "found", os.path.join(folder, hits[0])
                elif hits:
                    status = "ambiguous"
        out.append((att_id, setype, deleted, status, rel))
    return out


def check_attachments(dbname, inventory, begin_ns, report_dir, logdir, checks, report):
    client = Mysql.stand(database=dbname)
    rows = [codec.fields(line) for line in client.lines(ATTACHMENTS_SQL + "\n", logdir / "audit.log")]
    resolved = resolve_attachments([r[:5] for r in rows], inventory)
    tsv = []
    summary = Counter()
    referenced = set()
    for att_id, setype, deleted, status, rel in resolved:
        summary[(setype, deleted or "-", status)] += 1
        size, _m, digest = inventory.get(rel, (0, 0, "")) if rel else (0, 0, "")
        if rel:
            referenced.add(rel)
        tsv.append(f"{att_id}\t{setype}\t{deleted}\t{status}\t{(rel or b'').hex()}\t{size}\t{digest}\n")
    write_private(report_dir / "attachments.tsv", "attachmentsid\tsetype\tdeleted\tstatus\trelpath_hex\tsize\tsha256\n"
                  + "".join(tsv))
    live_missing = sum(n for (st, d, s), n in summary.items() if d == "0" and s != "found")
    orphans = [rel for rel in inventory if rel.startswith(b"storage/") and rel not in referenced
               and os.path.basename(rel) not in (b".htaccess", b"index.html")]
    orphan_after = sum(1 for rel in orphans if inventory[rel][1] > begin_ns)
    report["attachments"] = [{"setype": st, "deleted": d, "status": s, "rows": n}
                             for (st, d, s), n in sorted(summary.items())]
    counts = {"rows": len(rows), "live": sum(n for (_, d, _s), n in summary.items() if d == "0"),
              "live_found": sum(n for (_, d, s), n in summary.items() if d == "0" and s == "found"),
              "live_missing": live_missing,
              "deleted_found": sum(n for (_, d, s), n in summary.items() if d == "1" and s == "found"),
              "deleted_missing": sum(n for (_, d, s), n in summary.items() if d == "1" and s != "found"),
              "orphan_files": len(orphans), "orphan_files_after_t0": orphan_after}
    checks.add("C6", "файл каждого живого вложения есть в снимке", not live_missing, counts, "finding")
    losses = {r[0]: int(r[1]) for r in (codec.fields(x) for x in client.lines(LOSSES_SQL, logdir / "audit.log"))}
    checks.add("C7", "принятые потери источника (D-23): фото контактов и документы без вложения", True, losses, "info")
    logos = [bytes.fromhex(codec.fields(x)[0]) for x in client.lines(
        "SELECT HEX(IFNULL(logoname,'')) FROM vtiger_organizationdetails;\n", logdir / "audit.log")]
    logos = [n for n in logos if n]
    found = sum(1 for n in logos if b"test/logo/" + n in inventory and b"/" not in n)
    checks.add("C8", "логотип юрлица (logoname) есть в снимке", bool(logos) and found == len(logos),
               {"logos": len(logos), "found": found}, "finding")


def check_telephony(dbname, monitor, csv_path, begin_utc, logdir, checks, report):
    rows = [codec.fields(x) for x in Mysql.stand(database=dbname).lines(
        "SELECT HEX(IFNULL(recordingpath,'')),HEX(IFNULL(uniqueid,'')) FROM cdr;\n", logdir / "audit.log")]
    paths = {bytes.fromhex(p) for p, _u in rows if p}
    outside = sum(1 for p in paths if not p.startswith(MONITOR))
    found = {p[len(MONITOR):] for p in paths if p.startswith(MONITOR) and p[len(MONITOR):] in monitor}
    counts = {"cdr_rows": len(rows), "recording_paths": len(paths), "found": len(found),
              "missing": len(paths) - len(found) - outside, "outside_monitor": outside,
              "wav_files": len(monitor), "wav_without_cdr": len(set(monitor) - found)}
    checks.add("C9", "запись каждого CDR (recordingpath) есть в снимке", counts["missing"] == 0 and not outside,
               counts, "finding")
    uniqueids = {bytes.fromhex(u).decode("ascii", "replace") for _p, u in rows if u}
    csv_rows = csv_after = csv_18 = overlap = 0
    t0 = begin_utc[:19].replace("T", " ")
    checks.add("C11", "CDR CSV (Master.csv) есть в снимке", csv_path.exists(), {"present": int(csv_path.exists())},
               "finding")
    if csv_path.exists():
        with open(csv_path, newline="", encoding="utf-8", errors="replace") as fh:
            for rec in csv.reader(fh):
                csv_rows += 1
                csv_18 += len(rec) == 18
                if len(rec) >= 17:
                    csv_after += rec[9] > t0
                    overlap += rec[16] in uniqueids
    checks.add("C10", "CDR CSV: строки, после T0, общие uniqueid с MySQL", True,
               {"csv_rows": csv_rows, "csv_rows_18_fields": csv_18, "csv_rows_after_t0": csv_after,
                "csv_rows_with_mysql_uniqueid": overlap}, "info")
    report["telephony"] = counts


# --- entry point -----------------------------------------------------------------------------------

def verify(snapdir, root, restore=True, completeness=True, report_dir=None):
    snapdir = Path(snapdir)
    manifest = read_json(snapdir / "MANIFEST.json")
    if manifest.get("format") != FORMAT or manifest.get("format_version") != FORMAT_VERSION:
        raise SnapshotError("unknown snapshot format/version")
    report_dir = report_dir or snapdir / "reports" / f"verify-{time.strftime('%Y%m%dT%H%M%S')}"
    report_dir.mkdir(parents=True)
    logdir = report_dir / "logs"
    logdir.mkdir()
    checks = Checks()
    report = {"snapshot": manifest["id"], "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "restore": restore, "completeness": False}
    report["seal_digest"] = check_seal(snapdir, checks)
    inventories = check_files(snapdir, manifest, checks)
    db = manifest["db"]
    if not all(isinstance(s, str) and codec.NAME_RE.match(s) for s in db["schemas"]):
        raise SnapshotError("bad schema name in MANIFEST.json")
    tables = {s: read_json(snapdir / "db" / s / "tables.json") for s in db["schemas"]}
    if check_contract(snapdir, manifest, tables, checks, full=completeness and restore):
        for s in db["schemas"]:
            check_rows(snapdir, s, tables[s], checks)
    tempdbs = {"created": 0, "dropped": 0}
    if restore and checks.status() == "fail":
        # Never execute the SQL of a snapshot that failed its contract, seal, files or rows: it runs as MySQL root.
        checks.add("V4", "восстановление не выполнялось: контракт, печать, файлы или строки не сошлись", False,
                   {"skipped": 1})
    elif restore:
        with TempDatabases(root, logdir) as temp:
            names = {}
            for s in db["schemas"]:
                charset, collation = db["schema_charsets"][s]
                name = temp.create(s, charset, collation)
                log(f"restore {s}: loading into a temporary database")
                try:
                    Mysql.stand(database=name).session(
                        restore_sql(snapdir, s, tables[s], manifest["source"]["sql_mode"]),
                        lambda line: None, logdir / "restore.log")
                except SnapshotError as e:  # our own message: no values
                    checks.add(f"V4.{s}", f"восстановление {s} прервано: {e}", False, {"restored": 0})
                    continue
                compare_restored(snapdir, s, tables[s], name, db["catalogue_fingerprints"][s], logdir, checks)
                names[s] = name
            tempdbs["created"] = len(temp.created)
            completeness = completeness and checks.status() != "fail"
            report["completeness"] = completeness and sorted(names) == sorted(SOURCE_SCHEMAS)
            if completeness and "vtiger7" in names:
                log("completeness: audit SQL and map builders on the restored copy")
                auditdir = report_dir / "audit"
                maps = run_audit(names["vtiger7"], auditdir, db["begin_local"], logdir)
                check_maps(maps, tables["vtiger7"], parse_tsv_with_header(auditdir / "01_tabs.tsv"), checks, report)
                begin_ns = int(float(db["begin_epoch"]) * 1e9)
                check_attachments(names["vtiger7"], inventories.get("vtiger", {}), begin_ns, report_dir, logdir,
                                  checks, report)
            if completeness and "asteriskcdrdb" in names:
                monitor = {rel: v for rel, v in inventories.get("monitor", {}).items()}
                check_telephony(names["asteriskcdrdb"], monitor, snapdir / "files" / "cdr-csv" / "Master.csv",
                                db["begin_utc"], logdir, checks, report)
            left = temp.drop_all()
            tempdbs["dropped"] = tempdbs["created"] - len(left)
            checks.add("V5", "временные базы стенда удалены (по точному имени)", not left,
                       {"created": tempdbs["created"], "dropped": tempdbs["dropped"]})
    report["tool"] = tool_identity()
    report.update(status=checks.status(), checks=checks.items, tempdbs=tempdbs,
                  finished_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    write_json(report_dir / "report.json", report)
    return report
