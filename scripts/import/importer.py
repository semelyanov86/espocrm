#!/usr/bin/env python3
"""Repeatable import of the base entities of Vtiger into the EspoCRM stand (stage 06.2, docs/migration/import.md).

  importer.py run --snapshot ID [--only Accounts,Contacts,…] [--check-only] [--allow-mass-removal]
      verify the snapshot (V0–V4) and restore it into a temporary stand database, read, drop it; build the plan;
      take the target inventory and plan the removals of records gone from the source (stage 06.4, the mass-removal
      rail refuses the run before any write); apply upserts, then removals through `task espo -- itvolga-import`
      (stdin), then a check pass in a new process; reconcile every non-empty source column and relation, and the whole
      snapshot's columns (ledger); private report in IMPORT_ROOT/<run>/.
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
import aggregates  # noqa: E402
import files as F  # noqa: E402
import ledger  # noqa: E402
import removals as R  # noqa: E402
from common import (SNAPSHOT_ROOT, ID_RE, Mysql, SnapshotError, ensure_root, root_lock, sha256_file,  # noqa: E402
                    write_json, write_private)

IMPORT_ROOT = Path(os.environ.get("IMPORT_ROOT", "/data/itvolga/espo-private/import"))
ESPO = REPO / "scripts" / "stand" / "espo.sh"
REAL_KEYS = (1, spec.SYNTHETIC_KEY_MIN - 1)
TOOL_SOURCES = ("scripts/import", "scripts/snapshot", "custom/Espo/Modules/Itvolga/Tools/Import",
                "custom/Espo/Modules/Itvolga/Classes/ConsoleCommands/Import.php",
                "custom/Espo/Modules/Itvolga/Classes/ConsoleCommands/FinanceVerify.php",
                "custom/Espo/Modules/Itvolga/Tools/FinanceDocument/SourceMarks.php")
VERIFIED = ("carried", "normalized", "mapped", "archived", "linked", "protected", "derived_equal", "duplicate",
            "type_conflict", "no_target")
SILENCE = {  # stand tables an import must not write to (counts before / after)
    "notification": "SELECT COUNT(*) FROM notification",
    "reminder": "SELECT COUNT(*) FROM reminder",
    "stream_subscription": "SELECT COUNT(*) FROM stream_subscription",
    "note_not_imported": "SELECT COUNT(*) FROM note WHERE vtiger_id IS NULL",
    "email_not_imported": "SELECT COUNT(*) FROM email WHERE vtiger_id IS NULL",
    "webhook_queue_item": "SELECT COUNT(*) FROM webhook_queue_item",
    "action_history_record": "SELECT COUNT(*) FROM action_history_record",
}


def log(msg):
    print(f"[import] {msg}", file=sys.stderr, flush=True)


# --- writer bridge ----------------------------------------------------------------------------------

def bridge(ops, mode, adopt, logdir, inventory=(), journal=None, files=None, run=None, meta=None):
    """One `itvolga-import` process: operations on stdin, `#itv#<nonce>#<json>` results on stdout. Lines without the
    nonce (PHP notices) are counted only; stderr goes to a private log. In apply mode the bytes of a file follow its
    Attachment operation (`file.chunks` lines), read from the snapshot as they are sent. `run` ({keyRange, ownedTypes},
    stage 06.4) makes it a protocol-3 session: removals and owned links; `meta` receives the writer's `swept` count."""
    nonce = secrets.token_hex(16)
    prefix = f"#itv#{nonce}#".encode()
    results, stray, done = {}, [0], []
    header = {"protocol": 3 if run else 2, "mode": mode, "nonce": nonce, "adoptUserName": adopt, **(run or {})}

    def stream():
        yield (json.dumps(header) + "\n").encode()
        for op in ops:
            payload = op.payload()
            if op.file is not None and mode == "apply":
                payload["file"]["chunks"] = F.chunk_count(op.file["size"])
            yield (json.dumps(payload, ensure_ascii=False) + "\n").encode()
            if op.file is not None and mode == "apply":
                yield from F.chunk_lines(files, op.file_ref, op.file["size"])
        for entity in inventory:
            yield (json.dumps({"op": "inventory", "key": f"inventory:{entity}", "entityType": entity}) + "\n").encode()

    def consume(line):
        if not line.startswith(prefix):
            stray[0] += 1
            return
        data = json.loads(line[len(prefix):])
        if "done" in data:
            done.append(data["done"])
            if meta is not None:
                meta["swept"] = meta.get("swept", 0) + int(data.get("swept") or 0)
        else:
            results[data.get("key")] = data
            if journal is not None and data.get("id"):  # written at once: a run that fails later is still known
                journal.write(json.dumps({"key": data.get("key"), "id": data["id"], "status": data.get("status")}) + "\n")
                journal.flush()

    Mysql([str(ESPO), "itvolga-import"], "itvolga-import").session(stream(), consume, logdir / f"writer-{mode}.log")
    expected = len(ops) + len(inventory)
    if done != [expected] or len(results) != expected:
        raise SnapshotError(f"writer ({mode}) answered {len(results)} of {expected} operations")
    return results, stray[0]


def espo_command(args, logdir, name):
    """A console command of the stand (`task espo -- …`): ids and entity names only in argv; output to a private log,
    the lines are returned for counting."""
    out = []
    Mysql([str(ESPO), *args], name).session(iter(()), out.append, logdir / f"{name}.log")
    lines = [line.decode("utf-8", "replace").rstrip("\n") for line in out]
    with open(logdir / f"{name}.out", "a", encoding="utf-8") as fh:
        fh.write("".join(f"{line}\n" for line in lines))
    return lines


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
            key_range=REAL_KEYS, effective_admin=spec.EFFECTIVE_ADMIN, files_root=None, download=None,
            allow_mass_removal=False, rail=None):
    """The whole run; returns the report (also written to `rundir`). `source_db` (an already restored or synthetic
    source database) and `files_root` (a directory as the file part) are for the stage tests; real runs always come
    from a verified snapshot, whose shared lock is held for the whole run (its files are read while writing).
    `allow_mass_removal` lets removals beyond the rail through (`rail`: removals.RAIL, tests may lower it)."""
    options = {"allow_mass_removal": allow_mass_removal, "rail": rail}
    logdir = rundir / "logs"
    logdir.mkdir(parents=True, exist_ok=True)
    fields, relations = spec.load_maps(REPO)
    problems = spec.check_coverage(fields, relations)
    if problems:
        write_json(rundir / "coverage-problems.json", problems)
        raise SnapshotError(f"the specification does not cover the maps ({len(problems)} problems, see the run directory)")
    uitypes = uitypes_by_module(fields)
    if snapshot_dir is not None:
        with root_lock(SNAPSHOT_ROOT, exclusive=False):
            return _execute(rundir, logdir, fields, uitypes, snapshot_dir, None, F.SnapshotFiles(snapshot_dir), only,
                            check_only, adopt, key_range, effective_admin, download, options)
    return _execute(rundir, logdir, fields, uitypes, None, source_db,
                    F.DirectoryFiles(files_root) if files_root else None, only, check_only, adopt, key_range,
                    effective_admin, download, options)


def _execute(rundir, logdir, fields, uitypes, snapshot_dir, source_db, files, only, check_only, adopt, key_range,
             effective_admin, download, options):
    started = time.time()
    selected = only.split(",") if only else None
    if snapshot_dir is not None:
        with verify.restored_databases(snapshot_dir, SNAPSHOT_ROOT, logdir) as names:
            log("reading the restored source")
            db = source.SourceDb(names["vtiger7"], logdir)
            data, census = source.load(db, uitypes)
            source_totals = aggregates.run(db.lines, aggregates.source_sql())
        log("temporary source database dropped")
        counts = ledger.snapshot_counts(snapshot_dir)
    else:
        db = source.SourceDb(source_db, logdir)
        data, census = source.load(db, uitypes)
        source_totals = aggregates.run(db.lines, aggregates.source_sql())
        counts = {"vtiger7": source.column_counts(db)}
    transport = transport_check(data, census)
    if transport:
        raise SnapshotError(f"reader and census disagree on {len(transport)} columns: nothing written")
    resolved = F.resolve(data["vtiger_attachments"], data["crm"], files) if files else {}
    plan = spec.build(data, selected=selected, key_range=key_range, effective_admin=effective_admin,
                      files={**resolved, "inventory": files.inventory if files else {}})
    log(f"plan: {len(plan.ops)} operations, {len(plan.held)} records held")
    if plan.problems:
        raise SnapshotError(f"plan problems: {', '.join(plan.problems)}: nothing written")
    types = spec.owned_types(selected)
    run = {"keyRange": list(key_range), "ownedTypes": types}
    before, _ = bridge([], "check", adopt, logdir, inventory=types, run=run)  # the target's source keys, no values
    blocked = R.blocked_types(data["orphans"], selected)
    removal = R.plan_removals(plan, {r["inventory"]: r for r in before.values()}, types, key_range, options["rail"],
                              blocked)
    write_json(rundir / "removal-plan.json", {**removal.report(), "keys": {
        t: [o.vtigerId for o in removal.ops if o.entityType == t] for t in removal.by_type}})
    log(f"removals: {len(removal.ops)} planned, retyped {sum(removal.retyped.values())}"
        + (f", beyond the rail: {', '.join(removal.refused)}" if removal.refused else ""))
    if removal.refused and not options["allow_mass_removal"] and not check_only:
        raise SnapshotError(f"mass removal refused ({', '.join(removal.refused)}; --allow-mass-removal): nothing written")
    silence_before = silence_counts(logdir)
    meta = {}
    if check_only:
        applied, stray_apply, targets_before = {}, 0, set()
    else:
        targets_before = allocation_targets(plan, logdir, removal.ops)
        fd = os.open(rundir / "applied.jsonl", os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, "a") as journal:  # keys and EspoCRM ids of written records, as the writer answers
            applied, stray_apply = bridge(plan.ops + removal.ops, "apply", adopt, logdir, journal=journal, files=files,
                                          run=run, meta=meta)
            # a lower source amount of a payment fits only once its allocation is lowered or removed (the payment hook
            # keeps the stored allocations and refuses an amount below them): failed payments are written once more
            retry = [op for op in plan.ops if op.entityType == "Payment" and applied[op.key].get("status") == "error"]
            if retry:
                again, stray_again = bridge(retry, "apply", adopt, logdir, journal=journal, files=files, run=run,
                                            meta=meta)
                applied.update(again)
                stray_apply += stray_again
        log("apply: " + fmt(Counter(r.get("status") for r in applied.values())))
    finance = finance_steps(plan, check_only, logdir, targets_before)
    checked, stray_check = bridge(plan.ops + removal.ops, "check", adopt, logdir, inventory=types, run=run)
    silence_after = silence_counts(logdir)
    log("check: " + fmt(Counter(r.get("status") for k, r in checked.items() if not k.startswith("inventory:"))))
    downloads = file_downloads(plan, checked, download)
    target_totals, excluded = target_aggregates(plan, checked, logdir)
    report = reconcile(plan, applied, checked, census, fields, key_range, check_only, data["link_census"],
                       selected=selected, orphans=data["orphans"])
    extend_report(report, plan, applied, checked, downloads, finance, source_totals, target_totals, excluded, data,
                  resolved, rundir, check_only, selected)
    expected = removal_report(report, plan, removal, applied, checked, types, key_range, check_only, blocked)
    ledger_report(report, rundir, counts, fields, census, data, ledger.maps_check(snapshot_dir) if snapshot_dir else None)
    report.update(started_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
                  finished_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), tool=tool_identity(),
                  snapshot=snapshot_dir.name if snapshot_dir else None, only=only, check_only=check_only,
                  stray_writer_lines={"apply": stray_apply, "check": stray_check}, swept=meta.get("swept", 0),
                  silence={k: silence_after[k] - silence_before[k] - expected.get(k, 0) for k in SILENCE},
                  silence_expected=expected)
    if any(report["silence"].values()) or stray_apply or stray_check or report["problems"]:
        report["status"] = "fail"
    write_json(rundir / "report.json", report)
    write_private(rundir / "records.jsonl", "".join(
        json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n"
        for r in list(records(plan, applied, checked)) + removal_records(removal, applied, checked)))
    return report


DOCUMENT_TABLES = {"Quote": "quote", "SalesOrder": "sales_order", "Act": "act", "Invoice": "invoice"}
FINDING_FLAGS = ("external_url_invalid", "file_name_differs")  # D-153; photo/avatar name ≠ its attachment's
FINANCE_TYPES = ("Quote", "QuoteItem", "SalesOrder", "SalesOrderItem", "Act", "ActItem", "Invoice", "InvoiceItem",
                 "Payment", "PaymentAllocation")


def _command_counts(lines):
    """`Entity: key — n, key — n` (itvolga-finance-verify) and `Entity key: n` (itvolga-finance-settle) → Counter."""
    out = Counter()
    for line in lines:
        line = line.replace("[dry-run] ", "")
        if " — " in line and ": " in line:
            entity, rest = line.split(": ", 1)
            for part in rest.split(", "):
                if " — " in part:
                    key, n = part.rsplit(" — ", 1)
                    out[f"{entity}: {key}"] += int(n) if n.strip().isdigit() else 0
        elif line.rsplit(":", 1)[-1].strip().isdigit():
            out[line.rsplit(":", 1)[0]] += int(line.rsplit(":", 1)[1])
    return out


def finance_steps(plan, check_only, logdir, targets_before):
    """After the records (stage 06.3), only on the documents of this run: source marks of the imported documents
    (`itvolga-finance-verify`, saves only what differs), settlement of the run's invoices and orders and of the documents
    its allocations point to — before and after the write (`itvolga-finance-settle --silent`, writes only changes; then
    a dry run must find nothing to change), the numbering counters raised to the source's cur_id (never lowered; also
    in a run without documents). Check-only runs count without writing. Output lines go to private logs; the counts
    come back."""
    out = {"verify": Counter(), "settle": Counter(), "settle_drift": 0, "counters": {}}
    dry = ["--dry-run"] if check_only else []
    ids = {e: stand_ids(e, [op.vtigerId for op in plan.ops if op.entityType == e], logdir) for e in DOCUMENT_TABLES}
    for entity, found in ids.items():
        if found:  # an empty --id would select every document
            out["verify"] += _command_counts(espo_command(
                ["itvolga-finance-verify", f"--entity={entity}", "--id=" + ",".join(found), *dry], logdir, "finance-verify"))
    settle = sorted({*ids["Invoice"], *ids["SalesOrder"], *targets_before, *allocation_targets(plan, logdir)})
    if settle:
        selection = "--id=" + ",".join(settle)
        if not check_only:
            out["settle"] = _command_counts(espo_command(["itvolga-finance-settle", "--silent", selection], logdir,
                                                         "finance-settle"))
        drift = _command_counts(espo_command(["itvolga-finance-settle", "--dry-run", selection], logdir,
                                             "finance-settle-check"))
        out["settle_drift"] = sum(n for k, n in drift.items() if "would change" in k)
    if plan.counters:
        pairs = ",".join(f"{e}:{n}" for e, n in sorted(plan.counters.items()))
        lines = espo_command(["itvolga-setup-finance", f"--next={pairs}", *dry], logdir, "setup-finance")
        out["counters"]["changes"] = sum(1 for line in lines if "counter" in line)
        out["counters"]["below"] = counters_below(plan.counters, logdir)
    return out


def stand_ids(entity, keys, logdir):
    """EspoCRM ids of the live records of a finance document type with the given source keys."""
    if not keys:
        return []
    sql = (f"SET SESSION TRANSACTION READ ONLY;\nSELECT id FROM `{DOCUMENT_TABLES[entity]}` WHERE deleted = 0 "
           f"AND vtiger_id IN ({', '.join(str(int(k)) for k in sorted(set(keys)))}) ORDER BY id;\n")
    return [v.decode("ascii") for v in Mysql.stand(database="espocrm").lines(sql, logdir / "stand.log")]


def allocation_targets(plan, logdir, extra=()):
    """EspoCRM ids of the documents the run's allocations point to on the stand: read before the write too, so a
    document an allocation leaves (or a removed one left, `extra`: the run's removals) is settled as well."""
    keys = sorted({op.vtigerId for op in list(plan.ops) + list(extra) if op.entityType == "PaymentAllocation"})
    if not keys:
        return set()
    sql = ("SET SESSION TRANSACTION READ ONLY;\nSELECT IFNULL(invoice_id, sales_order_id) FROM payment_allocation "
           f"WHERE deleted = 0 AND vtiger_id IN ({', '.join(str(int(k)) for k in keys)});\n")
    return {v.decode("ascii") for v in Mysql.stand(database="espocrm").lines(sql, logdir / "stand.log")} - {"NULL"}


def counters_below(counters, logdir):
    """Entity types whose stand counter is lower than the source's next number (must be none after a run)."""
    sql = "SET SESSION TRANSACTION READ ONLY;\n" + "".join(
        f"SELECT IFNULL(MAX(value), 0) FROM next_number WHERE deleted = 0 AND entity_type = '{e}' "
        f"AND field_name = 'number';\n" for e in sorted(counters))
    values = Mysql.stand(database="espocrm").lines(sql, logdir / "stand.log")
    return sorted(e for e, v in zip(sorted(counters), values) if int(v) < counters[e])


def file_downloads(plan, checked, download):
    """Every imported file downloaded through the stand as the administrator (owner's answer 2026-10-11)."""
    items = []
    for op in plan.ops:
        if op.entityType != "Attachment" or op.file is None:
            continue
        result = checked.get(op.key, {})
        if result.get("id"):
            items.append((op.key, result["id"], op.file["size"], op.file["sha256"]))
    if not items:
        return {}
    log(f"downloading {len(items)} files through the stand")
    return (download or F.download_check)(items)


def target_aggregates(plan, checked, logdir):
    """Stand SQL of the finance measures over the records imported as planned (equal in the check pass); records the
    owner's answers keep out of the import (deleted, recalculated in EspoCRM) are excluded and listed."""
    keys, excluded = defaultdict(list), defaultdict(list)
    for op in plan.ops:
        status = checked.get(op.key, {}).get("status")
        if op.entityType not in FINANCE_TYPES:
            continue
        if status in ("deleted_in_target", "protected") or checked.get(op.key, {}).get("protected"):
            excluded[op.entityType].append(op.vtigerId)
        else:
            keys[op.entityType].append(op.vtigerId)
    if not keys:
        return {}, {}
    sql = "SET SESSION TRANSACTION READ ONLY;\n"
    queries = aggregates.target_sql(keys)
    totals = aggregates.run(lambda q: Mysql.stand(database="espocrm").lines(sql + q, logdir / "stand.log"), queries)
    return totals, {k: sorted(v) for k, v in excluded.items()}


LINK_PREFIXES = {  # link table → keys of its outcomes and planner counters (spec.attach_relations, build_user)
    "vtiger_user2role": ("user2role",), "vtiger_users2group": ("users2group",),
    "vtiger_seactivityrel": ("seactivityrel:",), "vtiger_cntactivityrel": ("cntactivityrel:",),
    "vtiger_salesmanactivityrel": ("salesmanactivityrel:",), "vtiger_contpotentialrel": ("contpotentialrel:",),
    "vtiger_crmentityrel": ("crmentityrel:",), "vtiger_freetagged_objects": ("tags:",),
    "vtiger_senotesrel": ("senotesrel:",), "vtiger_seattachmentsrel": ("seattachmentsrel:",),
    "vtiger_salesmanattachmentsrel": ("salesmanattachmentsrel:",), "vtiger_email_track": ("email_track:",),
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
        if flag.startswith(("pending_rel:", "unhandled_rel:", "mismatch_rel:", "deferred_rel:")):
            name = flag.split(":", 1)[1]
            for table, prefixes in LINK_PREFIXES.items():
                if name.startswith(prefixes):
                    out[table] += n
    return out


def transport_check(data, census):
    """Columns where the Python reader and the SQL census count different non-empty values."""
    bad = []
    for module, counts in data["reader"].items():
        bad += [f"{module}:{k}" for k, v in counts.items() if census[module].get(k, (None,))[0] != v]
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
               "deletedTargets": c.get("deletedTargets") or None, "protected": c.get("protected") or None,
               "file": c.get("file"), "legalEntity": c.get("legalEntity"),
               "verification": {k: v for k, v in (c.get("verification") or {}).items() if k != "expected"} or None,
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
    key_columns = {k for k, rs in rows.items() if any(spec.is_key_row(r) for r in rs)}
    consumed = spec.consumed_columns()

    columns = defaultdict(lambda: {"outcomes": Counter(), "verified": 0, "mismatch": 0, "exempt": 0})
    relations = defaultdict(lambda: {"outcomes": Counter(), "verified": 0, "mismatch": 0, "exempt": 0})
    for op in plan.ops + plan.held:
        c = checked.get(op.key, {})
        differs = set(c.get("differs") or [])
        protected = set(c.get("protected") or [])
        sent = not (op.skip or op.pending)
        for kind, key, outcome, attrs in op.outcomes:
            entry = (columns[(op.module, key)] if kind == "f" else relations[key])
            entry["outcomes"][outcome] += 1
            if outcome.split(":")[0] not in VERIFIED or not sent:
                continue
            if check_only and c.get("status") in ("missing", "absent"):
                continue  # a dry run before the first import: nothing to compare yet
            if c.get("status") in ("deleted_in_target", "protected") or protected & set(attrs):
                entry["exempt"] += 1  # owner's answers 2026-10-11: findings, not compared
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
                                                           if key in spec.MAP_GAPS else spec.EXTRA_FATES.get(key, ""))
            entry = columns.get(key)
            accounted = sum(entry["outcomes"].values()) if entry else 0
            item = {"module": module, "column": name, "fate": fate, "category": fate_category(fate) if fate else "unmapped",
                    "nonempty": nonempty, "meaningful": meaningful}
            if key in key_columns:
                item["category"] = "key"
            elif key in consumed:
                item.update(category="rule", outcomes=dict(entry["outcomes"]) if entry else {},
                            verified=entry["verified"] if entry else 0, mismatch=entry["mismatch"] if entry else 0,
                            exempt=entry["exempt"] if entry else 0, unaccounted=nonempty - accounted)
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

    rel_report = [{"relation": k, "outcomes": dict(v["outcomes"]), "verified": v["verified"], "mismatch": v["mismatch"],
                   "exempt": v["exempt"]} for k, v in sorted(relations.items())]
    accounted_rows = link_rows_accounted(plan)
    link_tables = {t: {"source_rows": n, "accounted": accounted_rows.get(t, 0)} for t, n in sorted((link_census or {}).items())}
    full_run = selected >= set(spec.SCOPE)
    for t, v in link_tables.items():
        if full_run and v["source_rows"] != v["accounted"]:  # a partial run plans only the selected modules
            problems["link_rows_unaccounted"] += 1
            problem_columns["link_rows_unaccounted"].append(t)
    def in_run(rel):  # crmentityrel:A->B of a module of this run (Calendar rows belong to Calendar and Events)
        ends = rel.split(":", 1)[1].split("->")
        return any(m in selected or (m == "Calendar" and selected & {"Calendar", "Events"}) for m in ends)

    unhandled = {k.split(":", 1)[1]: n for k, n in plan.flags.items() if k.startswith("unhandled_rel:") and in_run(k.split(":", 1)[1])}
    if unhandled:  # a pair of modules the specification does not know: never accounted silently
        problems["unhandled_relations"] = sum(unhandled.values())
        problem_columns["unhandled_relations"] = sorted(unhandled)
    lost = {k: n for k, n in (orphans or {}).items()
            if n and (k in selected or (k == "Calendar" and selected & {"Calendar", "Events"}))}
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
        not_equal = ("error", "deleted", "differs") + (() if check_only else ("missing",))
        if a.get("status") == "error" or c.get("status") in not_equal:  # a dry run only expects missing records
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
        inactive = set(r.get("inactive", []))  # a user gone from the source is deactivated (stage 06.4)
        live = [v for v in r.get("live", []) if (entity, v) not in keys and v not in inactive]
        inventory[entity] = {
            "missing_in_source": sum(1 for v in live if key_range[0] <= v <= key_range[1]),
            "missing_keys": sorted(v for v in live if key_range[0] <= v <= key_range[1]),  # private report only
            "other_range_live": sum(1 for v in live if not key_range[0] <= v <= key_range[1]),
            "deleted_in_target": sum(1 for v in r.get("deleted", []) if key_range[0] <= v <= key_range[1]),
            "other_range_deleted": sum(1 for v in r.get("deleted", []) if not key_range[0] <= v <= key_range[1]),
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
    findings["relation_module_mismatch"] = sum(n for k, n in plan.flags.items() if k.startswith("mismatch_rel:"))
    for flag in FINDING_FLAGS:  # values kept in vtigerData that the planner could not carry as they are
        findings[flag] = plan.flags.get(flag, 0)
    findings["missing_in_source"] = sum(i["missing_in_source"] for i in inventory.values())

    status = "fail" if problems else ("findings" if any(findings.values()) else "pass")
    return {"status": status, "problems": dict(problems), "problem_columns": dict(problem_columns),
            "findings": dict(findings),
            "entities": {k: dict(v) for k, v in sorted(entities.items())}, "columns": col_report,
            "relations": rel_report, "link_tables": link_tables, "orphans": orphans or {}, "inventory": inventory,
            "flags": {k: v for k, v in sorted(plan.flags.items()) if not k.startswith("pending_rel:")}}


# --- stage 06.4: removals, retyped activities, owned links, the whole-snapshot column ledger -----------------------

def removal_report(report, plan, removal, applied, checked, types, key_range, check_only, blocked=()):
    """Removals of the run (planned, applied, checked), activities retyped by their upserts, link items the source
    owns that were removed, and the proof: after the run no live target record outside the source but the kept ones
    (problem `live_outside_source`). Returns the silence effects the removals are expected to have."""
    problems, findings = Counter(report["problems"]), Counter(report["findings"])
    problem_columns = defaultdict(list, report["problem_columns"])
    by_type, expected = defaultdict(Counter), Counter()
    kept = set()
    for op in removal.ops:
        a, c = applied.get(op.key, {}), checked.get(op.key, {})
        by_type[op.entityType]["planned"] += 1
        by_type[op.entityType][f"apply:{a.get('status', 'none')}"] += 1
        by_type[op.entityType][f"check:{c.get('status')}"] += 1
        if "error" in (a.get("status"), c.get("status")):
            problems["removal_errors"] += 1
        if c.get("status") == "kept":
            kept.add((op.entityType, op.vtigerId))
            findings[f"kept_in_target:{c.get('reason')}"] += 1
        elif c.get("status") == "live":
            if check_only:
                findings["would_remove"] += 1
            else:
                problems["removal_not_applied"] += 1
                problem_columns["removal_not_applied"].append(op.entityType)
        for name, n in (a.get("effects") or {}).items():
            expected[name] += n
    if removal.refused:
        findings["mass_removal_refused" if check_only else "mass_removal_allowed"] += len(removal.refused)
    retyped, links = Counter(), Counter()
    for op in plan.ops:
        a = applied.get(op.key, {})
        if a.get("retyped"):
            retyped[f"{a['retyped']['from']}->{op.entityType}"] += 1
            findings["retyped_notes_left"] += a["retyped"].get("notesLeft", 0)
        for link, n in (a.get("removedLinks") or {}).items():
            links[f"{op.entityType}.{link}"] += n
    after = {r["inventory"]: r for k, r in checked.items() if k.startswith("inventory:")}
    left = R.plan_removals(plan, after, types, key_range, blocked=blocked)
    outside = sorted({o.entityType for o in left.ops if (o.entityType, o.vtigerId) not in kept})
    if not check_only:
        n = sum(1 for o in left.ops if (o.entityType, o.vtigerId) not in kept)
        if n:
            problems["live_outside_source"] = n
            problem_columns["live_outside_source"] = outside
        if left.retyped:
            problems["retype_incomplete"] = sum(left.retyped.values())
    elif left.retyped:
        findings["would_retype"] += sum(left.retyped.values())
    report.update(problems=dict(problems), problem_columns=dict(problem_columns),
                  findings={k: v for k, v in findings.items() if v},
                  removals={"by_type": {k: dict(v) for k, v in sorted(by_type.items())}, "plan": removal.report(),
                            "retyped": dict(retyped), "removed_links": dict(links), "blocked": sorted(blocked)})
    if problems:
        report["status"] = "fail"
    elif report["status"] == "pass" and report["findings"]:
        report["status"] = "findings"
    return dict(expected)


def removal_records(removal, applied, checked):
    """Per removal (private): the record's key (as the other records of the run), id, statuses, reason."""
    out = []
    for op in removal.ops:
        a, c = applied.get(op.key, {}), checked.get(op.key, {})
        out.append({"key": f"{op.entityType}:{op.vtigerId}", "removal": True, "module": op.module,
                    "id": c.get("id") or a.get("id"), "apply": a.get("status"), "check": c.get("status"),
                    "reason": c.get("reason") or a.get("reason"), "error": a.get("error") or c.get("error"),
                    "state": c.get("state") or a.get("state")})
    return out


def ledger_report(report, rundir, counts, fields, census, data, maps):
    """The whole-snapshot column ledger: every non-empty column of every table of both schemas gets a class (the
    reader takes the census of every module whatever the run selects; columns of modules a partial run leaves out are
    `not_selected` in the reconciliation); a column without a fate, a transfer fate nobody reads, counts that do not
    add up or stale map fates are problems. Rows (identifiers and counts) go to the private ledger.jsonl."""
    result = ledger.build(counts, fields, census, data.get("census_deleted", {}), report["columns"], maps)
    write_private(rundir / "ledger.jsonl", "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n"
                                                   for r in result["rows"]))
    report["ledger"] = {k: v for k, v in result.items() if k != "rows"}
    if result["problems"]:
        problems = Counter(report["problems"])
        problem_columns = defaultdict(list, report["problem_columns"])
        for name, cols in result["problems"].items():
            problems[f"ledger_{name}"] = len(cols)
            problem_columns[f"ledger_{name}"] = cols[:50]
        report.update(problems=dict(problems), problem_columns=dict(problem_columns), status="fail")


# --- stage 06.3: finance discrepancies, files, aggregates ------------------------------------------------------

TOTALS = ("subtotal", "preTaxTotal", "grandTotal")


def extend_report(report, plan, applied, checked, downloads, finance, source_totals, target_totals, excluded, data,
                  resolved, rundir, check_only, selected):
    """Stage 06.3 sections of the report: the owner's-answer findings, every rounding discrepancy and every file
    (private machine reports with reasons), exact aggregates; problems and findings are added to the run's."""
    problems, findings = Counter(report["problems"]), Counter(report["findings"])
    problem_columns = defaultdict(list, report["problem_columns"])
    results = {op.key: checked.get(op.key, {}) for op in plan.ops}
    findings["deleted_in_target"] = sum(1 for c in results.values() if c.get("status") == "deleted_in_target")
    findings["recalculated_in_target"] = sum(1 for c in results.values()
                                             if c.get("status") == "protected" or c.get("protected"))
    findings["deleted_targets"] = sum(len(c.get("deletedTargets") or []) for c in results.values())
    for name, keys in (("legal_entity_differs", [k for k, c in results.items() if c.get("legalEntity") == "differs"]),
                       ("source_marks_differ", [] if check_only else [
                           k for k, c in results.items() if (c.get("verification") or {}).get("marks") == "differs"])):
        if keys:
            problems[name] = len(keys)
            problem_columns[name] = sorted(keys)[:50]

    discrepancies, finance_counts = finance_discrepancies(plan, results)
    for d in discrepancies:
        findings[f"discrepancy:{d['kind']}"] += 1
    file_rows, file_counts = file_report(plan, results, downloads, check_only)
    for row in file_rows:
        if row["class"] == "problem":
            problems["file_" + row["reason"]] += 1
        elif row["class"] == "finding":
            findings["file_" + row["reason"]] += 1
    if finance.get("settle_drift"):
        problems["settlement_drift"] = finance["settle_drift"]
    if (finance.get("counters") or {}).get("below") and not check_only:
        problems["counter_below"] = len(finance["counters"]["below"])

    measures = selected_measures(source_totals, selected)
    reader = aggregates.compare(source_totals, aggregates.planned(plan.ops + plan.held, lambda op: True), measures)
    imported = {op.key for op in plan.ops if results.get(op.key, {}).get("status") in ("equal", "differs")
                and not results[op.key].get("protected")}
    writer = aggregates.compare(aggregates.planned(plan.ops, lambda op: op.key in imported), target_totals,
                                [m for m in measures if target_totals]) if target_totals else []
    if any(not r["equal"] for r in reader):
        problems["aggregate_reader_mismatch"] = sum(1 for r in reader if not r["equal"])
    if any(not r["equal"] for r in writer) and not check_only:
        problems["aggregate_writer_mismatch"] = sum(1 for r in writer if not r["equal"])

    write_private(rundir / "discrepancies.jsonl", "".join(
        json.dumps(d, ensure_ascii=False, sort_keys=True) + "\n" for d in discrepancies + [
            {"kind": "file", **r} for r in file_rows if r["class"] != "ok"]))
    write_private(rundir / "files.jsonl", "".join(json.dumps(r, sort_keys=True) + "\n" for r in file_rows))
    write_json(rundir / "aggregates.json", {"reader": reader, "writer": writer, "excluded": excluded})
    report.update(
        problems=dict(problems), problem_columns=dict(problem_columns), findings={k: v for k, v in findings.items() if v},
        finance={**finance_counts, "verify": dict(finance.get("verify") or {}), "settle": dict(finance.get("settle") or {}),
                 "settle_drift": finance.get("settle_drift", 0), "counters": finance.get("counters") or {},
                 "allocations": {k.split(":", 1)[1]: v for k, v in plan.flags.items() if k.startswith("allocation:")}},
        files=file_counts | {"excluded": data.get("excluded_files", {}),
                             "unresolved_in_snapshot": sum(1 for r in resolved.values() if r["status"] != "found")},
        aggregates={"reader": {"measures": len(reader), "unequal": sum(1 for r in reader if not r["equal"])},
                    "writer": {"measures": len(writer), "unequal": sum(1 for r in writer if not r["equal"])},
                    "excluded": {k: len(v) for k, v in excluded.items()}})
    if problems:
        report["status"] = "fail"
    elif report["status"] == "pass" and any(report["findings"].values()):
        report["status"] = "findings"


def selected_measures(source_totals, selected):
    modules = set(selected or spec.SCOPE)
    prefix = {"Payment": "SPPayments", "PaymentAllocation": "SPPayments"}
    return sorted(m for m in source_totals if prefix.get(m.split(".")[0], m.split(".")[0]) in modules)


def finance_discrepancies(plan, results):
    """Every document whose stored totals are not exactly the core recomputation, every line margin that disagrees,
    every invoice and act of one pair with different totals — with a closed reason (private report)."""
    out, counts = [], defaultdict(Counter)
    acts = {op.vtigerId: op for op in plan.ops if op.entityType == "Act"}
    for op in plan.ops:
        c = results.get(op.key, {})
        v = c.get("verification")
        if v is None:
            continue
        if v.get("recalculated"):
            counts["formula"]["recalculated"] += 1
            continue
        counts["formula"][v.get("formula") or "not_classified"] += 1
        counts["totalsCheck"][v.get("worst") or "not_classified"] += 1
        for kind, n in (v.get("margins") or {}).items():
            counts["margins"][kind] += n
        reasons = {"rounded": ["rounded_to_kopecks"], "mismatch": ["stored_total_differs_from_source_formula"],
                   "unverified": ["unsupported_source_formula"]}.get(v.get("worst"), [])
        if v.get("formula") is None:
            reasons = ["not_classified"]
        reasons += [r for r in v.get("reasons") or [] if reasons]
        margin = (v.get("margins") or {})
        if margin.get("mismatch") or margin.get("absent"):
            reasons.append("margin_differs_from_net_less_purchase_cost")
        if reasons:
            out.append({"kind": "rounding" if v.get("worst") in ("rounded", "mismatch") else "verification",
                        "key": op.key, "id": c.get("id"), "number_present": bool(op.attributes.get("number")),
                        "formula": v.get("formula"), "checks": v.get("checks"), "reasons": reasons,
                        "marginLines": v.get("marginLines"), "expected": v.get("expected"),
                        "stored": {t: op.attributes.get(t) for t in TOTALS}})
        if op.entityType == "Invoice" and op.links.get("act"):
            act = acts.get(op.links["act"][1])
            if act and any(T.decimal(op.attributes.get(t) or "0", 8) != T.decimal(act.attributes.get(t) or "0", 8)
                           for t in TOTALS):
                out.append({"kind": "invoice_act_total", "key": op.key, "act": act.key, "id": c.get("id"),
                            "reasons": ["linked_invoice_act_totals_differ"],
                            "invoice": {t: op.attributes.get(t) for t in TOTALS},
                            "actTotals": {t: act.attributes.get(t) for t in TOTALS}})
    reasons = Counter(r for d in out for r in d["reasons"])
    return out, {k: dict(v) for k, v in counts.items()} | {"discrepancy_reasons": dict(reasons)}


ACCEPTED = {"not_applicable:D-23"}


def file_report(plan, results, downloads, check_only=False):
    """Every file of the import (and every file the source names without one) → class ok / finding / problem with a
    reason: stored and downloaded as the administrator with the source sha256 = ok; a file the source names but the
    snapshot has none of = finding (accepted loss D-23 or a new one); anything wrong on the stand = problem."""
    rows = []
    for op in plan.ops + plan.held:
        if op.entityType != "Attachment":
            continue
        c, d = results.get(op.key, {}), downloads.get(op.key)
        row = {"key": op.key, "owner": op.owner, "id": c.get("id"), "size": op.file and op.file["size"],
               "sha256": op.file and op.file["sha256"], "storage": c.get("file"), "check": c.get("status"),
               "http": d and d["http"], "held": op.skip or op.pending}
        if op.skip:
            row.update({"class": "finding", "reason": op.skip if op.skip.startswith("file_") else "held"})
        elif op.pending:
            row.update({"class": "ok", "reason": "deferred"})
        elif check_only and c.get("status") == "missing":
            row.update({"class": "ok", "reason": "not_imported_yet"})  # a dry run before the first import
        elif c.get("status") != "equal":
            row.update({"class": "problem", "reason": f"check_{c.get('status')}"})
        elif not d or d["reason"]:
            row.update({"class": "problem", "reason": "download_" + (d["reason"] if d else "missing")})
        else:
            row.update({"class": "ok", "reason": None})
        rows.append(row)
    for op in plan.ops + plan.held:  # names without a file in the source: accepted losses (D-23)
        for kind, col, outcome, _ in op.outcomes:
            if kind == "f" and outcome in ACCEPTED:
                rows.append({"key": op.key, "column": col, "class": "accepted", "reason": "accepted_loss_D-23"})
    counts = defaultdict(Counter)
    for row in rows:
        owner = (row.get("owner") or {}).get("entityType", "source")
        counts[owner][row["class"] if row["class"] != "ok" else ("ok" if row.get("reason") is None else row["reason"])] += 1
    return rows, {"by_owner": {k: dict(v) for k, v in sorted(counts.items())},
                  "stored_and_downloaded": sum(1 for r in rows if r["class"] == "ok" and r.get("reason") is None),
                  "accepted_losses": sum(1 for r in rows if r["class"] == "accepted")}


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
        "# Импорт Vtiger — сводка прогона (этапы 06.2–06.4)", "",
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
    lines += ["", "## Цель вне источника", "", "Записи EspoCRM с vtigerId: живые вне источника; вне диапазона реальных ключей "
              "(синтетика тестов, ключи ≥ 900 000 000); удалённые в EspoCRM — в диапазоне реальных ключей и вне его.", "",
              "| Сущность | Живые с vtigerId вне источника | Вне диапазона ключей | Удалённые (реальные ключи) | "
              "Удалённые (вне диапазона) |", "|---|---|---|---|---|"]
    for entity, i in sorted(report["inventory"].items()):
        lines.append(f"| {entity} | {i['missing_in_source']} | {i['other_range_live']} | {i['deleted_in_target']} | "
                     f"{i.get('other_range_deleted', 0)} |")
    lines += render_063(report)
    lines += render_064(report)
    lines += ["", "## Счётчики преобразований", "", ", ".join(f"`{k}` {v}" for k, v in report["flags"].items()) or "—", ""]
    return "\n".join(lines)


def render_064(report):
    """Stage 06.4 sections of the summary: removals, owned links, retyped activities, the whole-snapshot ledger."""
    rem, led = report.get("removals") or {}, report.get("ledger") or {}
    if not (rem or led):
        return []
    plan = rem.get("plan") or {}
    lines = ["", "## Дельта: удаления, связи, смена типа (этап 06.4)", "",
             "Записи цели с vtigerId, которых нет в источнике, — удаляются (пользователи деактивируются; пересчитанные в "
             "EspoCRM документы и администратор остаются); связи между импортированными записями следуют источнику; "
             "активность, сменившая тип, пересоздаётся в новом типе. Предохранитель — до любой записи.", "",
             f"- Удаления по плану: {plan.get('operations', 0)}; сменили тип: "
             f"{fmt(Counter(plan.get('retyped') or {})) or 'нет'}; за порогом: {', '.join(plan.get('refused') or []) or 'нет'}.",
             f"- Итоги удалений: " + ("; ".join(f"{t}: {fmt(Counter(c))}" for t, c in (rem.get("by_type") or {}).items())
                                     or "нет"),
             f"- Снятые элементы связей (источник владеет): {fmt(Counter(rem.get('removed_links') or {})) or 'нет'}.",
             f"- Сменили тип в прогоне: {fmt(Counter(rem.get('retyped') or {})) or 'нет'}.",
             f"- Ожидаемые эффекты удалений в «тишине»: {fmt(Counter(report.get('silence_expected') or {})) or 'нет'}; "
             f"убрано `.part`-файлов убитого писателя: {report.get('swept', 0)}."]
    if led:
        imp = led.get("import") or {}
        lines += ["", "## Полная сверка колонок снимка (этап 06.4)", "",
                  "Каждая непустая колонка каждой таблицы обеих схем снимка (счётчики сервера в `tables.json`) — класс по "
                  "судьбе карты; колонки таблиц импорта — значения живых записей сверены по одному, значения удалённых в "
                  "Vtiger записей и строк вне границ импорта — отдельными счётчиками. Строки — в приватном `ledger.jsonl`.",
                  "", f"- Итог: **{led.get('status')}**; колонок: {led.get('columns', 0)}; значений: {led.get('values', 0)}; "
                  f"проверка карт снимка (C4/C5): {(led.get('maps') or {}).get('status', '—')}.",
                  f"- Проблемы: {fmt(Counter({k: len(v) for k, v in (led.get('problems') or {}).items()})) or 'нет'}.",
                  f"- Таблицы импорта: значений живых записей {imp.get('live', 0)} (сверено {imp.get('verified', 0)}, "
                  f"расхождений {imp.get('mismatch', 0)}, неучтённых {imp.get('unaccounted', 0)}), удалённых в Vtiger "
                  f"записей {imp.get('deleted', 0)}, вне границ импорта {imp.get('outside_scope', 0)}.", "",
                  "| Класс | Колонок | Значений |", "|---|---|---|"]
        for cls, (n, v) in (led.get("by_class") or {}).items():
            lines.append(f"| {cls} | {n} | {v} |")
    return lines


def render_063(report):
    """Stage 06.3 sections of the summary: counts and classes only (no amounts, names, ids or digests)."""
    fin, files, agg = report.get("finance") or {}, report.get("files") or {}, report.get("aggregates") or {}
    if not (fin or files or agg):
        return []
    lines = ["", "## Финансы: сверка итогов и налогов (этап 06.3)", "",
             "Исходные итоги и строки — эталон (D-05): импорт их не пересчитывает. Каждый документ проверен чистым ядром "
             "(`SourceVerifier`, «Пересчёт ядра»): класс формулы, сравнение каждого итога с точным пересчётом по строкам, "
             "маржа строк. Каждое расхождение (округление, несовпадение, неподтверждённая формула, маржа, разные итоги "
             "связанных счёта и акта) — с причиной в приватном `discrepancies.jsonl`.", "",
             f"- Класс формулы: {fmt(Counter(fin.get('formula') or {})) or '—'}.",
             f"- Сверка итогов: {fmt(Counter(fin.get('totalsCheck') or {})) or '—'}.",
             f"- Маржа строк: {fmt(Counter(fin.get('margins') or {})) or '—'}.",
             f"- Причины расхождений: {fmt(Counter(fin.get('discrepancy_reasons') or {})) or 'нет'}.",
             f"- Распределение платежей (D-11, категория:решение): {fmt(Counter(fin.get('allocations') or {})) or '—'}.",
             f"- Пометки источника (`itvolga-finance-verify`): {fmt(Counter(fin.get('verify') or {})) or '—'}.",
             f"- Оплата документов (`itvolga-finance-settle --silent`): {fmt(Counter(fin.get('settle') or {})) or '—'}; "
             f"расхождение после пересчёта: {fin.get('settle_drift', 0)}.",
             f"- Счётчики номеров (cur_id источника, только вверх): изменений {(fin.get('counters') or {}).get('changes', 0)}, "
             f"ниже источника: {len((fin.get('counters') or {}).get('below') or [])}.",
             "", "## Агрегаты (точные суммы decimal)", "",
             "Одни и те же меры тремя способами: SQL восстановленного источника, значения плана, SQL стенда. "
             "«Чтение» — SQL источника = план по всем записям; «запись» — план = SQL стенда по импортированным записям "
             "(без удалённых и пересчитанных в EspoCRM — ответы владельца). Суммы — только в приватном `aggregates.json`.", "",
             "| Сравнение | Мер | Не равно |", "|---|---|---|",
             f"| чтение | {(agg.get('reader') or {}).get('measures', 0)} | {(agg.get('reader') or {}).get('unequal', 0)} |",
             f"| запись | {(agg.get('writer') or {}).get('measures', 0)} | {(agg.get('writer') or {}).get('unequal', 0)} |",
             f"", f"Исключено из сравнения записи: {fmt(Counter(agg.get('excluded') or {})) or 'нет'}.",
             "", "## Файлы", "",
             "Каждый файл: байты из проверенного снимка (размер и sha256 по запечатанной описи), запись в хранилище "
             "стенда, проверочный проход (файл есть, sha256 совпадает) и скачивание через стенд администратором "
             "(200 и sha256 источника). Внешние ссылки документов не открываются — переносятся дословно. Каждый "
             "недоступный файл — с причиной в приватном `files.jsonl`.", "",
             "| Владелец | Итоги |", "|---|---|"]
    for owner, counts in (files.get("by_owner") or {}).items():
        lines.append(f"| {owner} | {fmt(Counter(counts))} |")
    lines += ["", f"- Сохранено и скачано: {files.get('stored_and_downloaded', 0)}; принятые потери D-23 (имя файла без "
                  f"файла в источнике): {files.get('accepted_losses', 0)}; не найдено в снимке: "
                  f"{files.get('unresolved_in_snapshot', 0)}.",
              f"- Оставлены в снимке по решениям: {fmt(Counter(files.get('excluded') or {})) or 'нет'}."]
    return lines


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
        report = execute(rundir, snapshot_dir=snapdir, only=args.only, check_only=args.check_only,
                         allow_mass_removal=args.allow_mass_removal)
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
    r.add_argument("--allow-mass-removal", action="store_true")
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
