#!/usr/bin/env python3
"""Protected snapshot of the source Vtiger (stage 06.1): docs/migration/snapshot.md.

    snapshot.py create                 read-only export → staging → verify → atomic rename
    snapshot.py verify <id> [--no-restore]
    snapshot.py list
    snapshot.py delete <id | .staging-<id> | vtsnap_… temporary database> --yes
    snapshot.py protocol <id> [--out PATH]   anonymised protocol for Git (counts only)

Exit codes: 0 — verified; 2 — verified with findings (the copy is faithful, see the report);
1 — failure (create removes the incomplete snapshot).
"""
import argparse
import datetime
import os
import re
import shutil
import signal
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import capture  # noqa: E402
import verify  # noqa: E402
from common import (FORMAT, FORMAT_VERSION, ID_RE, REPO, SNAPSHOT_ROOT, SOURCE_HOST, SOURCE_SCHEMAS,  # noqa: E402
                    TEMP_DB_RE, Mysql, SnapshotError, ensure_root, git_head, log, mib, read_json, root_lock,
                    write_json, write_private)


def _terminate(signum, _frame):
    raise SystemExit(128 + signum)


def local_iso(epoch):
    return datetime.datetime.fromtimestamp(float(epoch)).astimezone().isoformat(timespec="seconds")


def build_manifest(sid, planned, db, files):
    head, dirty = git_head()
    server = planned["server"]
    db = dict(db, begin_local=local_iso(db["begin_epoch"]),
              schema_charsets={s: [c["objects"]["charset"], c["objects"]["collation"]]
                               for s, c in planned["catalogues"].items()})
    return {
        "format": FORMAT, "format_version": FORMAT_VERSION, "id": sid,
        "created_local": local_iso(time.time()),
        "tool": {"git_head": head, "dirty_tool_files": dirty},
        "source": {"host": SOURCE_HOST, "mysql_version": server["version"], "time_zone": server["time_zone"],
                   "system_time_zone": server["system_time_zone"], "sql_mode": server["sql_mode"],
                   "lower_case_table_names": server["lower_case_table_names"], "log_bin": server["log_bin"],
                   "gtid_mode": server["gtid_mode"], "widest_row_bytes": planned["widest_row_bytes"]},
        "codec": {"name": "hex-tsv", "version": 1, "null": "N", "separator": "TAB", "order": "bytewise",
                  "digest": "sum of 4x64-bit lanes of sha256(line)", "session_time_zone": "+00:00"},
        "db": db,
        "files": files,
        "excluded": ["vtiger7 test/ except logo and upload", "vendor/", "cache/", "logs/", "user_privileges/",
                     "config*.php"],
    }


def report_exit(report):
    log(f"verify: {report['status']} — {sum(c['status'] == 'pass' for c in report['checks'])} passed, "
        f"{sum(c['status'] == 'finding' for c in report['checks'])} findings, "
        f"{sum(c['status'] == 'fail' for c in report['checks'])} failed")
    return {"pass": 0, "findings": 2}.get(report["status"], 1)


def cmd_create(_args):
    root = ensure_root()
    sid = time.strftime("%Y%m%dT%H%M%S")
    staging, final = root / f".staging-{sid}", root / sid
    with root_lock(root):
        if final.exists() or staging.exists():
            raise SnapshotError(f"snapshot {sid} already exists")
        staging.mkdir(mode=0o700)
        try:
            prod = Mysql.production()
            log(f"plan: server settings and catalogue of {', '.join(SOURCE_SCHEMAS)}")
            planned = capture.plan(prod, SOURCE_SCHEMAS, staging / "logs")
            db = capture.capture_db(prod, planned, staging)
            log(f"db: {db['tables']} tables, {db['rows']} rows, transaction {db['duration_s']} s "
                f"({db['begin_utc']} … {db['end_utc']})")
            files = capture.capture_files(capture.boundary_ns(db), staging)
            shutil.rmtree(staging / "work", ignore_errors=True)
            write_json(staging / "MANIFEST.json", build_manifest(sid, planned, db, files))
            seal = verify.write_seal(staging)
            log(f"sealed: {seal}")
            report = verify.verify(staging, root, report_dir=staging / "reports" / f"verify-{sid}")
            code = report_exit(report)
            if code == 1:
                raise SnapshotError("verification failed; see the report of the removed staging in failures/")
            os.rename(staging, final)
            log(f"snapshot {sid} ready: {final} ({du(final)})")
            return code
        except BaseException:
            try:
                keep_failure(root, sid, staging)
            except Exception:  # noqa: BLE001 — e.g. a full disk: removing the copy matters more
                log("diagnostics of the failed run could not be kept")
            finally:
                shutil.rmtree(staging, ignore_errors=True)
                if staging.exists():
                    log(f"ERROR: incomplete {staging.name} was not removed: task snapshot:delete -- {staging.name} --yes")
            raise


def keep_failure(root, sid, staging):
    """Logs and reports of a failed run (no data) go to failures/<id>/ for diagnosis."""
    dest = root / "failures" / sid
    dest.mkdir(parents=True, exist_ok=True, mode=0o700)
    for sub in ("logs", "reports"):
        if (staging / sub).exists():
            shutil.copytree(staging / sub, dest / sub, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("audit", "attachments.tsv"))
    write_private(dest / "traceback.txt", traceback.format_exc())


def du(path):
    return mib(sum(f.stat().st_size for f in path.rglob("*") if f.is_file() and not f.is_symlink()))


def snapshot_dir(root, sid):
    if not ID_RE.match(sid) or not (root / sid / "MANIFEST.json").is_file() or (root / sid).is_symlink():
        raise SnapshotError(f"no snapshot {sid}")
    return root / sid


def cmd_verify(args):
    root = ensure_root()
    with root_lock(root, exclusive=False):
        report = verify.verify(snapshot_dir(root, args.id), root, restore=not args.no_restore,
                               completeness=not args.no_restore)
    return report_exit(report)


def latest_report(snapdir):
    reports = sorted((snapdir / "reports").glob("verify-*/report.json"), key=lambda p: p.stat().st_mtime)
    return read_json(reports[-1]) if reports else None


def cmd_list(_args):
    root = ensure_root()
    with root_lock(root, exclusive=False):
        for d in sorted(p for p in root.iterdir() if ID_RE.match(p.name)):
            m = read_json(d / "MANIFEST.json")
            rep = latest_report(d)
            files = sum(f["files"] for f in m["files"].values())
            print(f"{d.name}  {m['db']['begin_utc']}  tables {m['db']['tables']}  rows {m['db']['rows']}  "
                  f"files {files}  {du(d)}  verify: {rep['status'] if rep else '—'}")
        for d in sorted(root.glob(".staging-*")):
            print(f"{d.name}  incomplete (remove: task snapshot:delete -- {d.name} --yes)")
        for name in verify.journal_leftovers(root, root / "failures" / "list.log"):
            print(f"{name}  temporary database left on the stand (task snapshot:delete -- {name} --yes)")


def cmd_delete(args):
    root = ensure_root()
    target = args.target
    if not args.yes:
        raise SnapshotError("deletion needs --yes")
    with root_lock(root):
        if TEMP_DB_RE.match(target):
            if target not in verify.journal_leftovers(root, root / "failures" / "delete.log"):
                raise SnapshotError(f"{target} is not a recorded temporary database of this root")
            verify.drop(target, root / "failures" / "delete.log")
            log(f"dropped temporary database {target}")
            return 0
        if re.fullmatch(r"\.staging-\d{8}T\d{6}", target):
            path = root / target
        else:
            path = snapshot_dir(root, target)
        if path.is_symlink() or path.parent != root or not path.is_dir():
            raise SnapshotError("refusing to delete")
        size = du(path)
        shutil.rmtree(path)
        log(f"deleted {target} ({size})")
    return 0


# --- protocol --------------------------------------------------------------------------------------

STATUS_RU = {"pass": "пройдена", "finding": "находка", "fail": "не пройдена", "info": "сведения",
             "findings": "пройдена, есть находки"}


def render_protocol(snapdir, m, rep):
    db, files = m["db"], m["files"]
    tables = {s: read_json(snapdir / "db" / s / "tables.json") for s in db["schemas"]}
    lines = [
        "# Протокол защищённого снимка",
        "",
        f"Сгенерирован `task snapshot:protocol -- {m['id']}` (`scripts/snapshot/snapshot.py`). Только счётчики, "
        "размеры и идентификаторы схемы; значений строк, имён файлов и реквизитов нет. Формат, границы, права "
        "и очистка — `docs/migration/snapshot.md`.",
        "",
        f"- Снимок: `{m['id']}`, формат `{m['format']}` v{m['format_version']}; печать (sha256 файла SHA256SUMS): "
        f"`{rep['seal_digest']}`.",
        f"- Код: `{m['tool']['git_head'][:12]}`; источник: MySQL {m['source']['mysql_version']}, "
        f"`time_zone={m['source']['time_zone']}` (`{m['source']['system_time_zone']}`), `sql_mode={m['source']['sql_mode']}`.",
        f"- Проверка: `{rep['started_utc']}` … `{rep['finished_utc']}` — **{STATUS_RU[rep['status']]}**.",
        "",
        "## Границы согласованности",
        "",
        "| Часть | Граница | Время (UTC) |",
        "|---|---|---|",
        f"| БД {', '.join(db['schemas'])} | одна транзакция `READ ONLY` с `CONSISTENT SNAPSHOT` (InnoDB); "
        f"{len(db['non_transactional'])} таблицы MyISAM — неизменны от начала до конца транзакции | "
        f"{db['begin_utc']} … {db['end_utc']} ({db['duration_s']} с) |",
    ]
    for name, f in files.items():
        lines.append(f"| файлы `{name}` | {'время изменения ≤ конца транзакции' if f['policy'].startswith('mtime') else 'файлы целиком на момент описи'}"
                     f" | опись {f['listed_utc']} |")
    lines += ["", "## Состав", "", "| Часть | Таблиц | Строк | Размер |", "|---|---:|---:|---:|"]
    for s in db["schemas"]:
        t = tables[s]
        lines.append(f"| БД `{s}` | {len(t)} | {sum(v['rows'] for v in t.values())} | "
                     f"{mib(sum(v['rows_bytes'] for v in t.values()))} (сжато) |")
    lines += ["", "| Файлы | Корень источника | Файлов | Размер | Новее границы (не взяты) | Ссылок/спецфайлов |",
              "|---|---|---:|---:|---:|---:|"]
    for name, f in files.items():
        lines.append(f"| `{name}` | `{f['root']}` ({', '.join(f['paths'])}) | {f['files']} | {mib(f['bytes'])} | "
                     f"{f['after_boundary']} | {f['symlinks']}/{f['special']} |")
    lines += ["", "## Проверки", "", "| Код | Проверка | Итог | Счётчики |", "|---|---|---|---|"]
    for c in rep["checks"]:
        counts = ", ".join(f"{k} {v}" for k, v in c["counts"].items() if isinstance(v, int))
        lines.append(f"| {c['id']} | {c['title']} | {STATUS_RU[c['status']]} | {counts} |")
    if rep.get("modules"):
        lines += ["", "## Модули с записями", "", "| Модуль | Живых | Удалённых |", "|---|---:|---:|"]
        lines += [f"| {r['module']} | {r['live']} | {r['deleted']} |" for r in rep["modules"]]
    if rep.get("attachments"):
        lines += ["", "## Вложения (`vtiger_attachments`)", "", "| setype | deleted | Итог | Строк |", "|---|---|---|---:|"]
        lines += [f"| {a['setype']} | {a['deleted']} | {a['status']} | {a['rows']} |" for a in rep["attachments"]]
    lines += ["", "## Права и очистка", "",
              "Каталог снимка — `700`, файлы — `600`, владелец — разработчик; временные базы стенда удалены по точному "
              f"имени (создано {rep['tempdbs']['created']}, удалено {rep['tempdbs']['dropped']}). Удаление снимка — "
              f"`task snapshot:delete -- {m['id']} --yes`.", ""]
    return "\n".join(lines)


def cmd_protocol(args):
    root = ensure_root()
    snapdir = snapshot_dir(root, args.id)
    rep = latest_report(snapdir)
    if not rep or rep["status"] == "fail" or not rep.get("completeness"):
        raise SnapshotError("no full verification report for this snapshot: run task snapshot:verify first")
    text = render_protocol(snapdir, read_json(snapdir / "MANIFEST.json"), rep)
    sys.path.insert(0, str(REPO / "scripts"))
    import check_secrets  # noqa: E402
    findings = []
    check_secrets.scan_text("snapshot-protocol.md", text, check_secrets.load_hashes(), check_secrets.load_allow(),
                            findings)
    if findings:
        raise SnapshotError("protocol not written: secret scanner rules " + ", ".join(sorted({f[2] for f in findings})))
    out = Path(args.out)
    out.write_text(text, encoding="utf-8")
    log(f"protocol written: {out}")
    return 0


def main():
    os.umask(0o077)
    signal.signal(signal.SIGTERM, _terminate)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("create")
    v = sub.add_parser("verify")
    v.add_argument("id")
    v.add_argument("--no-restore", action="store_true")
    sub.add_parser("list")
    d = sub.add_parser("delete")
    d.add_argument("target")
    d.add_argument("--yes", action="store_true")
    p = sub.add_parser("protocol")
    p.add_argument("id")
    p.add_argument("--out", default=str(REPO / "docs" / "migration" / "snapshot-protocol.md"))
    args = ap.parse_args()
    if os.geteuid() == 0:
        log("run as the developer user, not root")
        return 1
    try:
        return {"create": cmd_create, "verify": cmd_verify, "list": cmd_list, "delete": cmd_delete,
                "protocol": cmd_protocol}[args.cmd](args) or 0
    except SnapshotError as e:
        log(f"ERROR: {e}")
        return 1
    except KeyboardInterrupt:
        log("interrupted")
        return 130
    except Exception as e:  # noqa: BLE001 — messages of foreign exceptions may quote source values
        dest = SNAPSHOT_ROOT / "failures" / f"{args.cmd}-{time.strftime('%Y%m%dT%H%M%S')}.txt"
        dest.parent.mkdir(parents=True, exist_ok=True)
        write_private(dest, traceback.format_exc())
        log(f"ERROR: unexpected {type(e).__name__}; traceback (private): {dest}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
