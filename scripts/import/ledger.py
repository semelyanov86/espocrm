"""The whole-snapshot column ledger (stage 06.4, docs/migration/import.md «Полная сверка колонок»): every non-empty column
of every table of both source schemas gets a class, from three independent inputs — the snapshot's own per-column
counters (`tables.json`, computed by the production server inside the snapshot transaction), the committed fates of
`field-map.csv`, and the import's census and value reconciliation. Pure: counts and identifiers only.

Classes of a column (its non-empty values):
- `import` — a table the import reads: the values of live records in scope are accounted value by value by the run
  (outcomes and the check pass, `importer.reconcile`), the values of records deleted in Vtiger are counted apart
  (`deleted`), the rest (`outside_scope`: rows of modules the migration does not import, attachment records, rows
  without a record) carries the fates of the map rows of those modules;
- `configuration` / `module_code` / `excluded` / `key` / `empty` — a table the import does not read, by the fate of
  its map rows (configuration and options are checked by `task model:check`, print forms and reports are the module's
  code, excluded values carry the map's reason);
- the telephony schema (`asteriskcdrdb`, stage 07.2): its `cdr` table is read by the call history — the fates of its
  columns are the specification's (cdr.COLUMN_FATES: the maps describe Vtiger), every other table of the schema has
  none (`no_fate`).

Problems: a non-empty column without a fate (`no_fate`: a field or table Vtiger got after the audit), a transfer or
archive fate on a table nobody reads (`transfer_unread`), the import's census of a column above the server's count
(`counts_disagree`), and stale map decisions (`maps_outdated`: the maps regenerated from this snapshot by its verify —
checks C4/C5 — differ from Git, or that verify is missing).
"""
import json
from collections import Counter, defaultdict

import cdr
import spec

TELEPHONY_SCHEMA = "asteriskcdrdb"
TELEPHONY_FATES = {"cdr": cdr.COLUMN_FATES}  # table of the telephony schema → column fates (stage 07.2)
# fate prefix → class (longest prefix first)
FATE_CLASSES = (
    ("переносится как опции enum", "configuration"), ("переносится как значения multiEnum", "transfer"),
    ("переносится как конфигурация", "configuration"), ("переносится настройкой", "configuration"),
    ("переносится собственным кодом", "module_code"), ("заменено модулем отчётов", "module_code"),
    ("перенос в защищённое хранилище", "transfer"), ("переносится как связь", "transfer"),
    ("не переносится", "excluded"), ("исключено", "excluded"), ("только ключ записи", "key"), ("пусто", "empty"),
    ("переносится", "transfer"), ("перенос", "transfer"), ("архив", "archive"), ("слияние", "transfer"),
)


def snapshot_counts(snapdir):
    """{schema: {table: {column: [nonempty, nonzero]}}} from the sealed `tables.json` of every schema."""
    out = {}
    for path in sorted((snapdir / "db").glob("*/tables.json")):
        tables = json.loads(path.read_text(encoding="utf-8"))
        out[path.parent.name] = {t: (json.loads(m["column_counts"]) if isinstance(m["column_counts"], str)
                                     else m["column_counts"]) for t, m in tables.items()}
    return out


def maps_check(snapdir, repo):
    """The maps regenerated from this snapshot by its latest full verify (`reports/verify-*/audit/maps/`, the verify
    tied to this snapshot by its seal digest) compared now with the maps in Git (`repo`): decisions and fates equal —
    the C4/C5 rule of the verify, checked against the current maps, not the ones of the verify's day."""
    import verify  # scripts/snapshot (source.py puts it on sys.path)
    from common import sha256_file
    reports = sorted((snapdir / "reports").glob("verify-*/report.json"), key=lambda p: p.stat().st_mtime)
    fresh = [p.parent / "audit" / "maps" for p in reports if (p.parent / "audit" / "maps" / "field-map.csv").is_file()]
    if not fresh:
        return {"status": "missing"}
    report = json.loads((fresh[-1].parent.parent / "report.json").read_text(encoding="utf-8"))
    sealed = report.get("seal_digest") == sha256_file(snapdir / "SHA256SUMS")
    out = {"sealed": sealed, "verified_utc": report.get("finished_utc")}
    for name, path, key, counts in (("field_map", "field-map.csv", verify.FIELD_KEY, verify.FIELD_COUNTS),
                                    ("relations", "relations.csv", ("relation_id",), verify.REL_COUNTS)):
        d = verify.diff_rows(verify.read_csv(repo / "docs" / "migration" / path), verify.read_csv(fresh[-1] / path),
                             key, counts)
        out[name] = {k: d[k] for k in ("only_committed", "only_fresh", "decision_changed")}
    ok = sealed and not any(v for m in ("field_map", "relations") for v in out[m].values())
    return {"status": "pass" if ok else "fail", **out}


def fate_class(row, module=None):
    """`module`: the module of a physical row (no source_module) — the only module of its table's other rows."""
    module = row.get("source_module") or module or ""
    if spec.is_key_row(row):
        return "key"
    if module in spec.PENDING:
        return "pending:" + spec.PENDING[module]
    fate = row.get("fate") or ""
    for prefix, cls in FATE_CLASSES:
        if fate.startswith(prefix):
            return cls
    return "unknown"


def build(counts, fields, census, census_deleted, columns, maps=None):
    """`counts`: snapshot counters; `fields`: field-map.csv rows; `census`/`census_deleted`: the run's per-module census
    of live and deleted records ({module: {"table.column": (nonempty, meaningful)}}); `columns`: the reconciliation's
    column rows (report["columns"]); `maps`: maps_check() or None (a synthetic source has no verify)."""
    rows_of, table_modules = defaultdict(list), defaultdict(set)
    for r in fields:
        rows_of[(r["source_table"], r["source_column"])].append(r)
        if r["source_module"]:
            table_modules[r["source_table"]].add(r["source_module"])
    rule_only = {k[1] for k in list(spec.MAP_GAPS) + list(spec.EXTRA_FATES)}  # fates of the specification, no map row

    def has_fate(table, column, schema=None):
        if schema == TELEPHONY_SCHEMA:
            return column in TELEPHONY_FATES.get(table, {})
        if table in spec.LINK_COLUMNS:
            return column in spec.LINK_COLUMNS[table]
        return bool(rows_of.get((table, column))) or f"{table}.{column}" in rule_only

    def classes(table, column, skip=()):
        only = next(iter(table_modules[table])) if len(table_modules[table]) == 1 else None
        return sorted({fate_class(r, only) for r in rows_of.get((table, column), [])
                       if (r["source_module"] or "") not in skip})

    live, deleted, read_modules = Counter(), Counter(), defaultdict(set)
    for module, cols in census.items():
        for key, (n, _) in cols.items():
            table = key.split(".", 1)[0]
            if (table in spec.LINK_COLUMNS) != (module == "links"):  # link tables: the links census only
                continue
            live[key] += n
            read_modules[table].add(module)
    for module, cols in census_deleted.items():
        for key, (n, _) in cols.items():
            deleted[key] += n
    recon = defaultdict(lambda: {"categories": Counter(), "verified": 0, "mismatch": 0, "unaccounted": 0})
    for c in columns:
        entry = recon[c["column"]]
        entry["categories"][c["category"]] += 1
        for k in ("verified", "mismatch", "unaccounted"):
            entry[k] += c.get(k) or 0

    rows, problems = [], defaultdict(list)
    for schema, tables in sorted(counts.items()):
        for table, cols in sorted(tables.items()):
            for column, (nonempty, nonzero) in sorted(cols.items()):
                if not nonempty:
                    continue
                key = f"{table}.{column}"
                row = {"schema": schema, "table": table, "column": column, "nonempty": nonempty, "nonzero": nonzero}
                fates = classes(table, column) if schema != TELEPHONY_SCHEMA else \
                    sorted({fate_class({"fate": TELEPHONY_FATES[table][column], "target_field": ""})}
                           if has_fate(table, column, schema)
                           else set())
                if not has_fate(table, column, schema):  # a read table too: values may sit in deleted rows only
                    row.update(cls="no_fate")
                    problems["no_fate"].append(f"{schema}.{key}")
                elif table in read_modules:
                    other = nonempty - live[key] - deleted[key]
                    entry = recon.get(key)
                    row.update(cls="import", live=live[key], deleted=deleted[key], outside_scope=other,
                               categories=dict(entry["categories"]) if entry else {},
                               verified=entry["verified"] if entry else 0, mismatch=entry["mismatch"] if entry else 0,
                               unaccounted=entry["unaccounted"] if entry else 0,
                               outside_fates=classes(table, column, read_modules[table]))
                    if other < 0:
                        problems["counts_disagree"].append(f"{schema}.{key}")
                else:
                    row.update(cls="/".join(fates), fates=fates)
                    if {"transfer", "archive"} & set(fates):
                        problems["transfer_unread"].append(f"{schema}.{key}")
                    if "unknown" in fates:
                        problems["unknown_fate"].append(f"{schema}.{key}")
                rows.append(row)
    if maps is not None and maps.get("status") != "pass":
        problems["maps_outdated"].append(maps.get("status"))
    by_class = defaultdict(lambda: [0, 0])
    for r in rows:
        by_class[r["cls"]][0] += 1
        by_class[r["cls"]][1] += r["nonempty"]
    imported = [r for r in rows if r["cls"] == "import"]
    return {"status": "fail" if problems else "pass", "columns": len(rows),
            "values": sum(r["nonempty"] for r in rows), "by_class": dict(sorted(by_class.items())),
            "import": {k: sum(r[k] for r in imported) for k in ("live", "deleted", "outside_scope", "verified",
                                                                 "mismatch", "unaccounted")},
            "maps": maps, "problems": {k: sorted(v) for k, v in problems.items()}, "rows": rows}
