"""Count-only difference of two verified snapshots (stage 06.4, docs/migration/snapshot.md «Разница снимков»): what
changed in Vtiger between the snapshot of the trial import and a later one — per table rows new / changed / deleted by
the primary key (tables without one: rows added / removed as a multiset, an update shows as one of each), CRM records
per module (new, changed, deleted in Vtiger, restored, purged), files per part. Both seals are checked first; rows are
compared as the codec wrote them (NULL, bytes, decimals exactly). Nothing but identifiers and counts leaves this
module: no values, no keys.
"""
import json
import re
from collections import Counter

import verify
from common import SnapshotError, read_json

PK_RE = re.compile(r"PRIMARY KEY \(([^)]*)\)")
COLUMN_RE = re.compile(r"`([^`]+)`")


def primary_key(ddl):
    """Column names of the primary key of a `SHOW CREATE TABLE` text (prefix lengths ignored), or None."""
    m = PK_RE.search(ddl)
    return COLUMN_RE.findall(m.group(1)) if m else None


def _value(token):
    """A codec token (hex of the value, `N` = NULL) → bytes or None."""
    return None if token == b"N" else bytes.fromhex(token.decode("ascii"))


def _schema_tables(snapdir, schema):
    return read_json(snapdir / "db" / schema / "tables.json")


def _table_diff(a_dir, b_dir, schema, table, ma, mb):
    la = verify.read_lines(a_dir / "db" / schema / ma["rows_file"])
    lb = verify.read_lines(b_dir / "db" / schema / mb["rows_file"])
    names = [c["name"] for c in mb["columns"]]
    ddl = (b_dir / "db" / schema / mb["ddl_file"]).read_text(encoding="utf-8", errors="replace")
    pk = primary_key(ddl)
    same_columns = [c["name"] for c in ma["columns"]] == names
    if same_columns and pk and all(c in names for c in pk):
        idx = [names.index(c) for c in pk]

        def keyed(lines):
            out = {}
            for line in lines:
                tokens = line.split(b"\t")
                out[tuple(tokens[i] for i in idx)] = line
            return out
        ka, kb = keyed(la), keyed(lb)
        if len(ka) == len(la) and len(kb) == len(lb):
            shared = ka.keys() & kb.keys()
            return {"identity": "primary_key", "rows_a": len(la), "rows_b": len(lb), "new": len(kb.keys() - ka.keys()),
                    "deleted": len(ka.keys() - kb.keys()), "changed": sum(1 for k in shared if ka[k] != kb[k])}, \
                (ka, kb, names)
    ca, cb = Counter(la), Counter(lb)
    return {"identity": "row_multiset", "rows_a": len(la), "rows_b": len(lb), "added": sum((cb - ca).values()),
            "removed": sum((ca - cb).values()), "changed": None,
            "schema_changed": not same_columns}, None


def _records(keyed):
    """vtiger_crmentity by its key: per module (setype) new, purged, deleted in Vtiger, restored, changed."""
    ka, kb, names = keyed
    setype, deleted = names.index("setype"), names.index("deleted")
    out = {}

    def bump(line, what):
        module = (_value(line.split(b"\t")[setype]) or b"").decode("utf-8", "replace")
        out.setdefault(module, Counter())[what] += 1
    for k in kb.keys() - ka.keys():
        bump(kb[k], "new")
    for k in ka.keys() - kb.keys():
        bump(ka[k], "purged")
    for k in ka.keys() & kb.keys():
        if ka[k] == kb[k]:
            continue
        da, db = (_value(line.split(b"\t")[deleted]) for line in (ka[k], kb[k]))
        bump(kb[k], "deleted" if (da, db) == (b"0", b"1") else "restored" if (da, db) == (b"1", b"0") else "changed")
    return {m: dict(c) for m, c in sorted(out.items())}


def compare(a_dir, b_dir):
    """The difference of snapshot `a_dir` (earlier) and `b_dir` (later) → a count-only report."""
    checks = verify.Checks()
    for snapdir in (a_dir, b_dir):
        verify.check_seal(snapdir, checks)
    if checks.status() != "pass":
        raise SnapshotError("a snapshot seal does not hold: no difference computed")
    report = {"a": a_dir.name, "b": b_dir.name, "schemas": {}, "records": {}, "files": {}}
    schemas = sorted({p.name for d in (a_dir, b_dir) for p in (d / "db").iterdir() if p.is_dir()})
    for schema in schemas:
        ta = _schema_tables(a_dir, schema) if (a_dir / "db" / schema).is_dir() else {}
        tb = _schema_tables(b_dir, schema) if (b_dir / "db" / schema).is_dir() else {}
        entry = {"tables_a": len(ta), "tables_b": len(tb), "unchanged": 0, "changed": {},
                 "added_tables": {t: tb[t]["rows"] for t in sorted(set(tb) - set(ta))},
                 "dropped_tables": {t: ta[t]["rows"] for t in sorted(set(ta) - set(tb))}}
        for table in sorted(set(ta) & set(tb)):
            ma, mb = ta[table], tb[table]
            if ma["rows"] == mb["rows"] and ma["lanes"] == mb["lanes"] and ma["ddl_sha256"] == mb["ddl_sha256"]:
                entry["unchanged"] += 1
                continue
            counts, keyed = _table_diff(a_dir, b_dir, schema, table, ma, mb)
            counts["ddl_changed"] = ma["ddl_sha256"] != mb["ddl_sha256"]
            entry["changed"][table] = counts
            if schema == "vtiger7" and table == "vtiger_crmentity" and keyed:
                report["records"] = _records(keyed)
        report["schemas"][schema] = entry
    manifest_a, manifest_b = read_json(a_dir / "MANIFEST.json"), read_json(b_dir / "MANIFEST.json")
    for part in sorted(set(manifest_a.get("files", {})) | set(manifest_b.get("files", {}))):
        ia = verify.read_inventory(a_dir, part) if part in manifest_a.get("files", {}) else {}
        ib = verify.read_inventory(b_dir, part) if part in manifest_b.get("files", {}) else {}
        report["files"][part] = {"files_a": len(ia), "files_b": len(ib), "added": len(ib.keys() - ia.keys()),
                                 "removed": len(ia.keys() - ib.keys()),
                                 "changed": sum(1 for k in ia.keys() & ib.keys() if ia[k][2] != ib[k][2])}
    return report


def render(report):
    """Markdown for Git: table names and counts only."""
    lines = [f"# Разница снимков `{report['a']}` → `{report['b']}`", "",
             "Генерируется: `task snapshot:diff -- <A> <B> --out docs/migration/snapshot-delta.md` "
             "(`scripts/snapshot/diff.py`). Только имена таблиц и счётчики строк: ни значений, ни ключей. Строки "
             "сравниваются так, как их записал кодек снимка; таблицы с первичным ключом — по ключу (новые, "
             "изменённые, удалённые), без ключа — мультимножеством строк (изменение видно как «добавлена» + "
             "«удалена»).", ""]
    for schema, s in report["schemas"].items():
        lines += [f"## Схема `{schema}`", "",
                  f"Таблиц: {s['tables_a']} → {s['tables_b']}; без изменений: {s['unchanged']}; изменились: "
                  f"{len(s['changed'])}; новые: {len(s['added_tables'])}; исчезли: {len(s['dropped_tables'])}.", ""]
        if s["changed"]:
            lines += ["| Таблица | Строк | Сравнение | Новые / добавлены | Изменены | Удалены | DDL |",
                      "|---|---|---|---|---|---|---|"]
            for table, c in s["changed"].items():
                if c["identity"] == "primary_key":
                    lines.append(f"| `{table}` | {c['rows_a']} → {c['rows_b']} | ключ | {c['new']} | {c['changed']} | "
                                 f"{c['deleted']} | {'да' if c['ddl_changed'] else '—'} |")
                else:
                    lines.append(f"| `{table}` | {c['rows_a']} → {c['rows_b']} | строки | {c['added']} | — | "
                                 f"{c['removed']} | {'да' if c['ddl_changed'] else '—'} |")
            lines.append("")
        for kind, title in (("added_tables", "Новые таблицы"), ("dropped_tables", "Исчезнувшие таблицы")):
            if s[kind]:
                lines += [f"{title}: " + ", ".join(f"`{t}` ({n})" for t, n in s[kind].items()), ""]
    lines += ["## Записи CRM по модулям (`vtiger_crmentity`)", ""]
    if report["records"]:
        lines += ["| Модуль | Новые | Изменены | Удалены в Vtiger | Восстановлены | Стёрты |", "|---|---|---|---|---|---|"]
        for module, c in report["records"].items():
            lines.append(f"| {module} | {c.get('new', 0)} | {c.get('changed', 0)} | {c.get('deleted', 0)} | "
                         f"{c.get('restored', 0)} | {c.get('purged', 0)} |")
    else:
        lines.append("Изменений нет.")
    lines += ["", "## Файлы", "", "| Часть | Файлов | Новые | Изменены | Исчезли |", "|---|---|---|---|---|"]
    for part, c in report["files"].items():
        lines.append(f"| {part} | {c['files_a']} → {c['files_b']} | {c['added']} | {c['changed']} | {c['removed']} |")
    return "\n".join(lines) + "\n"


def to_json(report):
    return json.dumps(report, ensure_ascii=False, indent=1, sort_keys=True)
