#!/usr/bin/env python3
"""Repeatable import of the base entities of Vtiger into the EspoCRM stand (stage 06.2, docs/migration/import.md).

  importer.py run --snapshot ID [--only Accounts,Contacts,…] [--check-only]
      verify the snapshot (V0–V4) and restore it into a temporary stand database, read, drop it; build the plan;
      apply it through `task espo -- itvolga-import` (stdin), then a check pass in a new process; reconcile every
      non-empty source column and relation; private report in IMPORT_ROOT/<run>/.
  importer.py summary RUN [--out docs/migration/import-summary.md]
      the anonymised summary of a run (counts only, checked by the secret scanner before it is written).

Exit codes: 0 pass; 2 findings (pending later stages, conflicts kept in vtigerData, stale map rows…); 1 fail.
The console shows step names and counts only; values never leave the pipe between the two processes.
"""
import argparse
import json
import os
import secrets
import signal
import sys
import time
import traceback
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import source  # noqa: E402  (puts scripts/snapshot and scripts/audit on sys.path)
import spec  # noqa: E402
import transforms as T  # noqa: E402
import verify  # noqa: E402
from common import (SNAPSHOT_ROOT, ID_RE, Mysql, SnapshotError, ensure_root, root_lock, sha256_file,  # noqa: E402
                    write_json, write_private)

IMPORT_ROOT = Path(os.environ.get("IMPORT_ROOT", "/data/itvolga/espo-private/import"))
ESPO = REPO / "scripts" / "stand" / "espo.sh"
REAL_KEYS = (1, spec.SYNTHETIC_KEY_MIN - 1)
TOOL_SOURCES = ("scripts/import", "scripts/snapshot", "custom/Espo/Modules/Itvolga/Tools/Import",
                "custom/Espo/Modules/Itvolga/Classes/ConsoleCommands/Import.php")
VERIFIED = ("carried", "normalized", "mapped", "archived", "linked", "protected", "derived_equal", "duplicate",
            "type_conflict", "no_target")
SILENCE = {  # stand tables an import must not write to (counts before / after)
    "notification": "SELECT COUNT(*) FROM notification",
    "reminder": "SELECT COUNT(*) FROM reminder",
    "stream_subscription": "SELECT COUNT(*) FROM stream_subscription",
    "note_not_imported": "SELECT COUNT(*) FROM note WHERE vtiger_id IS NULL",
    "email": "SELECT COUNT(*) FROM email",
    "webhook_queue_item": "SELECT COUNT(*) FROM webhook_queue_item",
    "action_history_record": "SELECT COUNT(*) FROM action_history_record",
}


def log(msg):
    print(f"[import] {msg}", file=sys.stderr, flush=True)


# --- writer bridge ----------------------------------------------------------------------------------

def bridge(ops, mode, adopt, logdir, inventory=()):
    """One `itvolga-import` process: operations on stdin, `#itv#<nonce>#<json>` results on stdout. Lines without the
    nonce (PHP notices) are counted only; stderr goes to a private log."""
    nonce = secrets.token_hex(16)
    prefix = f"#itv#{nonce}#".encode()
    results, stray, done = {}, [0], []

    def stream():
        yield (json.dumps({"protocol": 1, "mode": mode, "nonce": nonce, "adoptUserName": adopt}) + "\n").encode()
        for op in ops:
            yield (json.dumps(op.payload(), ensure_ascii=False) + "\n").encode()
        for entity in inventory:
            yield (json.dumps({"op": "inventory", "key": f"inventory:{entity}", "entityType": entity}) + "\n").encode()

    def consume(line):
        if not line.startswith(prefix):
            stray[0] += 1
            return
        data = json.loads(line[len(prefix):])
        if "done" in data:
            done.append(data["done"])
        else:
            results[data.get("key")] = data

    Mysql([str(ESPO), "itvolga-import"], "itvolga-import").session(stream(), consume, logdir / f"writer-{mode}.log")
    expected = len(ops) + len(inventory)
    if done != [expected] or len(results) != expected:
        raise SnapshotError(f"writer ({mode}) answered {len(results)} of {expected} operations")
    return results, stray[0]


# --- stand state ------------------------------------------------------------------------------------

def silence_counts(logdir):
    sql = "SET SESSION TRANSACTION READ ONLY;\n" + "".join(f"{q};\n" for q in SILENCE.values())
    out = Mysql.stand(database="espocrm").lines(sql, logdir / "stand.log")
    if len(out) != len(SILENCE):
        raise SnapshotError("stand counts failed")
    return {k: int(v) for k, v in zip(SILENCE, out)}


# --- run ------------------------------------------------------------------------------------------------

def uitypes_by_module(fields):
    out = defaultdict(dict)
    for r in fields:
        module = r["source_module"] or spec.module_of_physical(r["source_table"])
        if module:
            out[module][(r["source_table"], r["source_column"])] = r["uitype"]
    return out


def execute(rundir, snapshot_dir=None, source_db=None, only=None, check_only=False, adopt="admin",
            key_range=REAL_KEYS, effective_admin=spec.EFFECTIVE_ADMIN):
    """The whole run; returns the report (also written to `rundir`). `source_db` (an already restored or synthetic
    source database) is for the stage tests; real runs always come from a verified snapshot."""
    logdir = rundir / "logs"
    logdir.mkdir(parents=True, exist_ok=True)
    fields, relations = spec.load_maps(REPO)
    problems = spec.check_coverage(fields, relations)
    if problems:
        write_json(rundir / "coverage-problems.json", problems)
        raise SnapshotError(f"the specification does not cover the maps ({len(problems)} problems, see the run directory)")
    uitypes = uitypes_by_module(fields)
    started = time.time()
    if snapshot_dir is not None:
        with root_lock(SNAPSHOT_ROOT, exclusive=False):
            with verify.restored_databases(snapshot_dir, SNAPSHOT_ROOT, logdir) as names:
                log("reading the restored source")
                data, census = source.load(source.SourceDb(names["vtiger7"], logdir), uitypes)
        log("temporary source database dropped")
    else:
        data, census = source.load(source.SourceDb(source_db, logdir), uitypes)
    transport = transport_check(data, census)
    if transport:
        raise SnapshotError(f"reader and census disagree on {len(transport)} columns: nothing written")
    plan = spec.build(data, selected=only.split(",") if only else None, key_range=key_range,
                      effective_admin=effective_admin)
    log(f"plan: {len(plan.ops)} operations, {len(plan.held)} records held")
    silence_before = silence_counts(logdir)
    applied, stray_apply = ({}, 0) if check_only else bridge(plan.ops, "apply", adopt, logdir)
    if not check_only:
        log("apply: " + fmt(Counter(r.get("status") for r in applied.values())))
    checked, stray_check = bridge(plan.ops, "check", adopt, logdir, inventory=inventory_types(only))
    silence_after = silence_counts(logdir)
    log("check: " + fmt(Counter(r.get("status") for k, r in checked.items() if not k.startswith("inventory:"))))
    report = reconcile(plan, applied, checked, census, fields, key_range, check_only, data["link_census"],
                       selected=only.split(",") if only else None, orphans=data["orphans"])
    report.update(started_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
                  finished_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), tool=tool_identity(),
                  snapshot=snapshot_dir.name if snapshot_dir else None, only=only, check_only=check_only,
                  stray_writer_lines={"apply": stray_apply, "check": stray_check},
                  silence={k: silence_after[k] - silence_before[k] for k in SILENCE})
    if any(report["silence"].values()) or stray_apply or stray_check:
        report["status"] = "fail"
    write_json(rundir / "report.json", report)
    write_private(rundir / "records.jsonl", "".join(
        json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in records(plan, applied, checked)))
    return report


def inventory_types(only):
    """Target entity types whose every source module is selected: their records with a vtigerId not in the source
    are reported (also when the source has none of them any more)."""
    selected = set(only.split(",")) if only else set(spec.SCOPE)
    types = {e for m in selected for e in spec.MODULE_ENTITIES.get(m, ())}
    return sorted(t for t in types if all(m in selected for m, es in spec.MODULE_ENTITIES.items() if t in es))


LINK_PREFIXES = {  # link table → keys of its outcomes and planner counters (spec.attach_relations, build_user)
    "vtiger_user2role": ("user2role",), "vtiger_users2group": ("users2group",),
    "vtiger_seactivityrel": ("seactivityrel:",), "vtiger_cntactivityrel": ("cntactivityrel:",),
    "vtiger_salesmanactivityrel": ("salesmanactivityrel:",), "vtiger_contpotentialrel": ("contpotentialrel:",),
    "vtiger_crmentityrel": ("crmentityrel:",), "vtiger_freetagged_objects": ("tags:",),
    "vtiger_senotesrel": ("vtiger_senotesrel:",), "vtiger_seattachmentsrel": ("vtiger_seattachmentsrel:",),
}


def link_rows_accounted(plan):
    """Rows of each link table that got an outcome or a counter from the planner."""
    out = Counter()
    for op in plan.ops + plan.held:
        for kind, key, outcome, _ in op.outcomes:
            if kind == "r":
                for table, prefixes in LINK_PREFIXES.items():
                    if key.startswith(prefixes):
                        out[table] += 1
    for flag, n in plan.flags.items():
        if flag.startswith(("pending_rel:", "unhandled_rel:")):
            name = flag.split(":", 1)[1]
            for table, prefixes in LINK_PREFIXES.items():
                if name.startswith(prefixes):
                    out[table] += n
    return out


def transport_check(data, census):
    """Columns where the Python reader and the SQL census count different non-empty values."""
    bad = []
    for module in spec.SOURCES:
        counts = source.reader_counts(data[module])
        bad += [f"{module}:{k}" for k, v in counts.items() if census[module].get(k, (None,))[0] != v]
    counts = source.reader_counts(data["vtiger_users"])
    bad += [f"Users:{k}" for k, v in counts.items() if census["Users"].get(k, (None,))[0] != v]
    for table in spec.LINK_COLUMNS:
        counts = source.reader_counts(data[table])
        bad += [f"links:{k}" for k, v in counts.items() if census["links"].get(k, (None,))[0] != v]
    return bad


def records(plan, applied, checked):
    """Per record (private): keys, ids, statuses and attribute names — never values."""
    for op in plan.ops + plan.held:
        a, c = applied.get(op.key, {}), checked.get(op.key, {})
        yield {"key": op.key, "module": op.module, "held": op.skip or op.pending, "id": c.get("id") or a.get("id"),
               "apply": a.get("status"), "check": c.get("status"), "error": a.get("error") or c.get("error"),
               "invalid": a.get("attributes") or c.get("attributes"), "changed": a.get("changed"),
               "forced": a.get("forced"), "differs": c.get("differs"),
               "unresolved": sorted(set(a.get("unresolved") or []) | set(c.get("unresolved") or [])),
               "outcomes": [[k, key, outcome] for k, key, outcome, _ in op.outcomes]}


# --- reconciliation ----------------------------------------------------------------------------------

def fate_category(fate):
    if fate.startswith(spec.TRANSFER_FATES) or fate.startswith("слияние"):
        return "transfer"
    if fate.startswith("пусто"):
        return "empty"
    return "excluded"


def reconcile(plan, applied, checked, census, fields, key_range, check_only, link_census=None, selected=None,
              orphans=None):
    """Every non-empty value of every column of every table read, every relation item, every record — accounted."""
    rows, physical = defaultdict(list), defaultdict(list)
    for r in fields:
        column = f"{r['source_table']}.{r['source_column']}"
        if r["source_module"]:
            rows[(r["source_module"], column)].append(r)
        else:
            physical[column].append(r)  # shared tables (vtiger_crmentity, …): one row for every module
    for module in census:
        for column in census[module]:
            if (module, column) not in rows and column in physical:
                rows[(module, column)] = physical[column]
    key_columns = {k for k, rs in rows.items()
                   if any(r["target_field"] in ("(ключ записи)", "vtigerId", "(тип сущности)") for r in rs)}
    consumed = spec.consumed_columns()

    columns = defaultdict(lambda: {"outcomes": Counter(), "verified": 0, "mismatch": 0})
    relations = defaultdict(lambda: {"outcomes": Counter(), "verified": 0, "mismatch": 0})
    for op in plan.ops + plan.held:
        c = checked.get(op.key, {})
        differs = set(c.get("differs") or [])
        sent = not (op.skip or op.pending)
        for kind, key, outcome, attrs in op.outcomes:
            entry = (columns[(op.module, key)] if kind == "f" else relations[key])
            entry["outcomes"][outcome] += 1
            if outcome.split(":")[0] not in VERIFIED or not sent:
                continue
            ok = c.get("status") == "equal" or (c.get("status") == "differs" and not differs & set(attrs))
            entry["verified" if ok else "mismatch"] += 1

    col_report, problems, problem_columns = [], Counter(), defaultdict(list)
    selected = set(selected or spec.SCOPE)
    for module, counts in sorted(census.items()):
        for name, (nonempty, meaningful) in sorted(counts.items()):
            key = (module, name)
            if module == "links":
                table, column = name.split(".", 1)
                fate = spec.LINK_COLUMNS.get(table, {}).get(column)
                item = {"module": module, "column": name, "fate": fate or "", "nonempty": nonempty,
                        "meaningful": meaningful,
                        "category": ("relation" if fate == "pair" else "pending" if fate and fate.startswith("pending")
                                     else "excluded" if fate else "unmapped")}
                if not fate and nonempty:
                    problems["link_column_without_fate"] += 1
                    problem_columns["link_column_without_fate"].append(name)
                col_report.append(item)
                continue
            if module not in selected:
                col_report.append({"module": module, "column": name, "category": "not_selected",
                                   "nonempty": nonempty, "meaningful": meaningful})
                continue
            fate_rows = rows.get(key, [])
            fate = fate_rows[0]["fate"] if fate_rows else ("правило без строки карты: " + spec.MAP_GAPS[key]
                                                           if key in spec.MAP_GAPS else "")
            entry = columns.get(key)
            accounted = sum(entry["outcomes"].values()) if entry else 0
            item = {"module": module, "column": name, "fate": fate, "category": fate_category(fate) if fate else "unmapped",
                    "nonempty": nonempty, "meaningful": meaningful}
            if key in key_columns:
                item["category"] = "key"
            elif key in consumed:
                item.update(category="rule", outcomes=dict(entry["outcomes"]) if entry else {},
                            verified=entry["verified"] if entry else 0, mismatch=entry["mismatch"] if entry else 0,
                            unaccounted=nonempty - accounted)
                if nonempty != accounted:
                    problems["unaccounted_values"] += 1
                    problem_columns["unaccounted_values"].append(f"{module}:{name}")
                if item["mismatch"]:
                    problems["mismatched_values"] += 1
                    problem_columns["mismatched_values"].append(f"{module}:{name}")
            elif item["category"] == "transfer" and nonempty:
                problems["transfer_without_rule"] += 1
                problem_columns["transfer_without_rule"].append(f"{module}:{name}")
            elif item["category"] == "empty" and meaningful:
                problems["map_stale"] += 1
                problem_columns["map_stale"].append(f"{module}:{name}")
            elif item["category"] == "unmapped" and nonempty:
                problems["unmapped_nonempty"] += 1
                problem_columns["unmapped_nonempty"].append(f"{module}:{name}")
            col_report.append(item)

    rel_report = [{"relation": k, "outcomes": dict(v["outcomes"]), "verified": v["verified"], "mismatch": v["mismatch"]}
                  for k, v in sorted(relations.items())]
    accounted_rows = link_rows_accounted(plan)
    link_tables = {t: {"source_rows": n, "accounted": accounted_rows.get(t, 0)} for t, n in sorted((link_census or {}).items())}
    full_run = selected >= set(spec.SCOPE)
    for t, v in link_tables.items():
        if full_run and v["source_rows"] != v["accounted"]:  # a partial run plans only the selected modules
            problems["link_rows_unaccounted"] += 1
            problem_columns["link_rows_unaccounted"].append(t)
    unhandled = {k.split(":", 1)[1]: n for k, n in plan.flags.items() if k.startswith("unhandled_rel:")}
    if unhandled:  # a pair of modules the specification does not know: never accounted silently
        problems["unhandled_relations"] = sum(unhandled.values())
        problem_columns["unhandled_relations"] = sorted(unhandled)
    lost = {k: n for k, n in (orphans or {}).items() if n}
    if lost:
        problems["live_without_base_row"] = sum(lost.values())
        problem_columns["live_without_base_row"] = sorted(lost)
    errors = Counter()
    for entry in list(columns.values()) + list(relations.values()):
        for outcome, n in entry["outcomes"].items():
            if outcome.startswith("error"):
                errors[outcome] += n
    if errors:
        problems["error_outcomes"] = sum(errors.values())
        problem_columns["error_outcomes"] = sorted(errors)
    rel_report += [{"relation": k.split(":", 1)[1].rsplit(":", 1)[0], "outcomes": {"pending:" + k.rsplit(":", 1)[1]: n}}
                   for k, n in sorted(plan.flags.items()) if k.startswith("pending_rel:")]
    if any(r.get("mismatch") for r in rel_report):
        problems["mismatched_relations"] += 1

    entities = defaultdict(Counter)
    for op in plan.ops:
        a, c = applied.get(op.key, {}), checked.get(op.key, {})
        entities[op.entityType]["source"] += 1
        entities[op.entityType][f"apply:{a.get('status', 'none')}"] += 1
        entities[op.entityType][f"check:{c.get('status')}"] += 1
        if a.get("status") == "error" or c.get("status") in ("error", "missing", "deleted", "differs"):
            if not (op.onlyIfExists and c.get("status") == "absent"):
                problems["record_not_equal"] += 1
        for name in a.get("forced") or []:
            entities[op.entityType][f"forced:{name}"] += 1
        if a.get("unresolved") or c.get("unresolved"):
            problems["unresolved_links"] += 1
    for op in plan.held:
        entities[op.entityType]["source"] += 1
        entities[op.entityType][f"held:{op.skip or op.pending}"] += 1
        if op.skip and op.skip.startswith("error"):
            problems["record_errors"] += 1

    keys = {(o.entityType, o.vtigerId) for o in plan.ops + plan.held}
    inventory = {}
    for k, r in checked.items():
        if not k.startswith("inventory:"):
            continue
        entity = r["inventory"]
        live = [v for v in r.get("live", []) if (entity, v) not in keys]
        inventory[entity] = {
            "missing_in_source": sum(1 for v in live if key_range[0] <= v <= key_range[1]),
            "other_range_live": sum(1 for v in live if not key_range[0] <= v <= key_range[1]),
            "deleted_in_target": len(r.get("deleted", [])),
        }

    findings = Counter()
    for c in col_report:
        for outcome, n in (c.get("outcomes") or {}).items():
            if outcome.startswith(("pending", "dangling", "no_target", "type_conflict", "deferred")):
                findings[outcome.split(":")[0]] += n
    for r in rel_report:
        for outcome, n in r["outcomes"].items():
            if outcome.startswith(("pending", "dangling", "conflict", "no_target", "deferred")):
                findings[outcome.split(":")[0]] += n
    findings["records_held"] = len(plan.held)
    findings["missing_in_source"] = sum(i["missing_in_source"] for i in inventory.values())
    if check_only:
        problems.pop("record_not_equal", None)

    status = "fail" if problems else ("findings" if any(findings.values()) else "pass")
    return {"status": status, "problems": dict(problems), "problem_columns": dict(problem_columns),
            "findings": dict(findings),
            "entities": {k: dict(v) for k, v in sorted(entities.items())}, "columns": col_report,
            "relations": rel_report, "link_tables": link_tables, "orphans": orphans or {}, "inventory": inventory,
            "flags": {k: v for k, v in sorted(plan.flags.items()) if not k.startswith("pending_rel:")}}


def fmt(counter):
    return ", ".join(f"{k}={v}" for k, v in sorted(counter.items(), key=lambda kv: str(kv[0])))


def tool_identity():
    import hashlib
    import subprocess
    head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", str(REPO), "status", "--porcelain", "--", *TOOL_SOURCES],
                           capture_output=True, text=True).stdout.splitlines()
    h = hashlib.sha256()
    for base in TOOL_SOURCES:
        paths = [REPO / base] if (REPO / base).is_file() else sorted((REPO / base).rglob("*"))
        for path in paths:
            if path.is_file() and path.suffix in (".py", ".php") and "__pycache__" not in path.parts:
                h.update(f"{path.relative_to(REPO)}\0{sha256_file(path)}\n".encode())
    return {"git_head": head, "dirty_tool_files": len(dirty), "sources_sha256": h.hexdigest()}


# --- summary (Git) ------------------------------------------------------------------------------------

def render_summary(report, run_id):
    cat = defaultdict(lambda: Counter())
    for c in report["columns"]:
        if c["module"] == "links":
            continue
        cat[c["module"]][c["category"]] += 1
        cat[c["module"]]["values_" + c["category"]] += c["nonempty"]
        if c["category"] == "rule":
            cat[c["module"]]["values_verified"] += c.get("verified", 0)
            cat[c["module"]]["values_mismatch"] += c.get("mismatch", 0)
            cat[c["module"]]["values_unaccounted"] += c.get("unaccounted", 0)
    lines = [
        "# Импорт базовых сущностей — сводка прогона (этап 06.2)", "",
        "Генерируется: `task import:summary -- <прогон>` (`scripts/import/importer.py summary`). Только счётчики: ни "
        "значений, ни идентификаторов записей. Машинный отчёт с причинами по каждой записи и колонке — вне Git "
        "(`/data/itvolga/espo-private/import/<прогон>/`). Контракт импорта — `import.md`.", "",
        f"- Прогон: `{run_id}`; снимок: `{report.get('snapshot')}`; код: `{report['tool']['git_head'][:7]}` "
        f"(незакоммиченных файлов инструмента: {report['tool']['dirty_tool_files']}).",
        f"- Итог: **{report['status']}**; проблемы: {fmt(Counter(report['problems'])) or 'нет'}; "
        f"находки: {fmt(Counter(report['findings'])) or 'нет'}.",
        f"- «Тишина» (изменение числа строк стенда: уведомления, напоминания, подписки, записи ленты без vtigerId, письма, "
        f"вебхуки, журнал действий): {fmt(Counter(report['silence'])) or 'нет изменений'}.", "",
        "## Записи", "", "| Сущность | Источник | Запись | Проверка | Удержаны | Возвращено после хуков |", "|---|---|---|---|---|---|"]
    for entity, c in report["entities"].items():
        apply = fmt(Counter({k[6:]: v for k, v in c.items() if k.startswith("apply:")}))
        check = fmt(Counter({k[6:]: v for k, v in c.items() if k.startswith("check:")}))
        held = fmt(Counter({k[5:]: v for k, v in c.items() if k.startswith("held:")})) or "—"
        forced = fmt(Counter({k[7:]: v for k, v in c.items() if k.startswith("forced:")})) or "—"
        lines.append(f"| {entity} | {c['source']} | {apply} | {check} | {held} | {forced} |")
    lines += ["", "## Колонки источника по модулям", "",
              "Все колонки всех прочитанных таблиц по живым записям модуля. «Правило» — колонка переносится правилом "
              "спецификации; для них значения сверены проверочным проходом (несверенный остаток — нули «0 = пусто», "
              "ожидание следующего этапа, удержанные записи). «Исключено»/«пусто» — судьба из `field-map.csv`, значения "
              "не переносятся. «Значений» — непустых по выражению аудита (`nonempty_expr`: ноль и «нет» — тоже значения); "
              "значимых (ненулевых, «да») в колонках «пусто по карте» нет — иначе прогон дал бы находку «карта устарела».", "",
              "| Модуль | Колонок с правилом | Значений | Сверено | Расхождений | Неучтённых | Ключи | Исключено (колонок/значений) "
              "| Пусто по карте (колонок/значений) | Без строки карты (колонок/значений) |", "|---|---|---|---|---|---|---|---|---|---|"]
    for module, c in sorted(cat.items()):
        lines.append(f"| {module} | {c['rule']} | {c['values_rule']} | {c['values_verified']} | {c['values_mismatch']} | "
                     f"{c['values_unaccounted']} | {c['key']} | {c['excluded']}/{c['values_excluded']} | "
                     f"{c['empty']}/{c['values_empty']} | {c['unmapped']}/{c['values_unmapped']} |")
    outcomes = defaultdict(Counter)
    for c in report["columns"]:
        for k, v in (c.get("outcomes") or {}).items():
            outcomes[c["module"]][k] += v
    lines += ["", "## Исходы значений", "", "| Модуль | Исходы |", "|---|---|"]
    for module, c in sorted(outcomes.items()):
        lines.append(f"| {module} | {fmt(c)} |")
    lines += ["", "## Связи", "", "| Источник связи | Исходы | Сверено | Расхождений |", "|---|---|---|---|"]
    for r in report["relations"]:
        lines.append(f"| `{r['relation']}` | {fmt(Counter(r['outcomes']))} | {r.get('verified', '—')} | "
                     f"{r.get('mismatch', '—')} |")
    lines += ["", "## Колонки таблиц связей", "", "Строки таблиц связей в границах этапа: «пара» — колонки, из которых "
              "строится связь (строки сверены ниже), «ждёт этапа» — связи следующего этапа, «не переносится» — с причиной "
              "(D-144).", "", "| Колонка | Судьба | Значений |", "|---|---|---|"]
    for c in report["columns"]:
        if c["module"] == "links":
            fate = {"relation": "пара", "pending": "ждёт этапа 06.3", "unmapped": "**нет судьбы**"}.get(
                c["category"], c["fate"].replace("excluded: ", "не переносится: "))
            lines.append(f"| `{c['column']}` | {fate} | {c['nonempty']} |")
    lines += ["", "## Таблицы связей источника", "", "Строки таблиц связей по живым записям этапа (SQL) и строки, получившие "
              "исход планировщика — должны совпадать.", "", "| Таблица | Строк в источнике | Учтено |", "|---|---|---|"]
    for table, v in report.get("link_tables", {}).items():
        lines.append(f"| `{table}` | {v['source_rows']} | {v['accounted']} |")
    lines += ["", "## Цель вне источника", "", "| Сущность | Живые с vtigerId вне источника | Вне диапазона ключей | "
              "Удалённые с vtigerId |", "|---|---|---|---|"]
    for entity, i in sorted(report["inventory"].items()):
        lines.append(f"| {entity} | {i['missing_in_source']} | {i['other_range_live']} | {i['deleted_in_target']} |")
    lines += ["", "## Счётчики преобразований", "", ", ".join(f"`{k}` {v}" for k, v in report["flags"].items()) or "—", ""]
    return "\n".join(lines)


# --- CLI -------------------------------------------------------------------------------------------------

def _terminate(signum, frame):
    raise KeyboardInterrupt


def cmd_run(args):
    root = ensure_root(IMPORT_ROOT)
    if not ID_RE.match(args.snapshot):
        raise SnapshotError("bad snapshot id")
    snapdir = ensure_root(SNAPSHOT_ROOT) / args.snapshot
    if not (snapdir / "MANIFEST.json").is_file():
        raise SnapshotError("no such published snapshot")
    with root_lock(root, exclusive=True):
        run_id = time.strftime("%Y%m%dT%H%M%S")
        rundir = root / run_id
        rundir.mkdir()
        log(f"run {run_id} (private directory {rundir})")
        report = execute(rundir, snapshot_dir=snapdir, only=args.only, check_only=args.check_only)
    log(f"status {report['status']}; problems: {fmt(Counter(report['problems'])) or 'none'}; "
        f"findings: {fmt(Counter(report['findings'])) or 'none'}")
    for entity, c in report["entities"].items():
        log(f"  {entity}: " + fmt(Counter({k: v for k, v in c.items() if not k.startswith('forced:')})))
    return {"pass": 0, "findings": 2}.get(report["status"], 1)


def cmd_summary(args):
    root = ensure_root(IMPORT_ROOT)
    if not ID_RE.match(args.run):
        raise SnapshotError("bad run id")
    report = json.loads((root / args.run / "report.json").read_text(encoding="utf-8"))
    text = render_summary(report, args.run)
    sys.path.insert(0, str(REPO / "scripts"))
    import check_secrets  # noqa: E402
    findings = []
    check_secrets.scan_text("import-summary.md", text, check_secrets.load_hashes(), check_secrets.load_allow(), findings)
    if findings:
        raise SnapshotError("summary not written: secret scanner rules " + ", ".join(sorted({f[2] for f in findings})))
    Path(args.out).write_text(text, encoding="utf-8")
    log(f"summary written: {args.out}")
    return 0


def main():
    os.umask(0o077)
    signal.signal(signal.SIGTERM, _terminate)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--snapshot", required=True)
    r.add_argument("--only")
    r.add_argument("--check-only", action="store_true")
    s = sub.add_parser("summary")
    s.add_argument("run")
    s.add_argument("--out", default=str(REPO / "docs" / "migration" / "import-summary.md"))
    args = ap.parse_args()
    if os.geteuid() == 0:
        log("run as the developer user, not root")
        return 1
    try:
        return {"run": cmd_run, "summary": cmd_summary}[args.cmd](args)
    except (SnapshotError, T.TransformError) as e:
        log(f"ERROR: {e}")
        return 1
    except KeyboardInterrupt:
        log("interrupted")
        return 130
    except Exception as e:  # noqa: BLE001 — messages of foreign exceptions may quote source values
        where = ""
        try:
            dest = IMPORT_ROOT / "failures" / f"{args.cmd}-{time.strftime('%Y%m%dT%H%M%S')}.txt"
            dest.parent.mkdir(parents=True, exist_ok=True)
            write_private(dest, traceback.format_exc())
            where = f"; traceback (private): {dest}"
        except Exception:  # noqa: BLE001
            pass
        log(f"ERROR: unexpected {type(e).__name__}{where}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
