#!/usr/bin/env python3
"""Interruption and idempotency drill of the import on the stand (stage 06.4, docs/migration/import.md «Прерывание и
повтор», owner's answer 2026-10-12: «stand + backup»). The source is a verified snapshot; the stand is backed up first
(the protected copy to return to) and may be restored from an earlier backup, so that the run has something to write:

  1. backup of the stand (`--label pre-drill`); with `--restore NAME`: restore that backup (code kept, --skip-custom);
  2. run A — SIGTERM to the importer after `--term-after` written records: exit 130, no writer process left;
  3. run B — SIGKILL of the importer and of the writer (as the stand user) while a file is being sent: no process left;
  4. run C — converges: no problems; part files of the killed writer swept;
  5. fingerprint F1, run D, fingerprint F2: run D writes nothing (every answer unchanged/kept) and F1 = F2.

Every run is the real importer CLI (`importer.py run --snapshot`), each in a session of its own. The protocol (statuses,
counts, run ids — no values) goes to IMPORT_ROOT/drills/<time>/protocol.json; the console shows the same counts.

  drill.py --snapshot ID [--restore BACKUP] [--term-after N] [--allow-mass-removal]
"""
import argparse
import json
import os
import signal
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "stand"))
sys.path.insert(0, str(REPO / "scripts" / "snapshot"))
import fingerprint  # noqa: E402
from common import SnapshotError, write_private  # noqa: E402

IMPORT_ROOT = Path(os.environ.get("IMPORT_ROOT", "/data/itvolga/espo-private/import"))
WRITER = "command.php itvolga-import"
WRITES = ("created", "updated", "restored", "adopted", "removed", "deactivated")
QUIET = ("unchanged", "skipped", "kept", "absent", "protected", "deleted_in_target")  # answers that write nothing


def log(msg):
    print(f"[drill] {msg}", file=sys.stderr, flush=True)


def stand(*args):
    res = subprocess.run([str(REPO / "scripts" / "stand" / args[0]), *args[1:]], cwd=REPO, check=False)
    if res.returncode != 0:
        raise SnapshotError(f"{args[0]} failed (exit {res.returncode})")


def writers_alive():
    res = subprocess.run(["pgrep", "-f", WRITER], capture_output=True, text=True, check=False)
    return [int(p) for p in res.stdout.split()]


def part_files():
    res = subprocess.run(["sudo", "-n", "find", str(fingerprint.UPLOAD), "-maxdepth", "1", "-name",
                          ".itvolga-import-*.part"], capture_output=True, text=True, check=False)
    return len(res.stdout.split())


class Run:
    """One importer CLI run in a session of its own; its run directory is read from its log line `run <id>`."""

    def __init__(self, snapshot, logdir, name, extra=()):
        self.name, self.err = name, logdir / f"{name}.stderr"
        fd = os.open(self.err, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        self.proc = subprocess.Popen([sys.executable, str(REPO / "scripts" / "import" / "importer.py"), "run",
                                      "--snapshot", snapshot, *extra], cwd=REPO, stdout=fd, stderr=fd,
                                     start_new_session=True)
        os.close(fd)
        self.rundir = None

    def find_rundir(self):
        if self.rundir is None and self.err.exists():
            for line in self.err.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.startswith("[import] run "):
                    self.rundir = IMPORT_ROOT / line.split()[2]
        return self.rundir

    def journal(self):
        rundir = self.find_rundir()
        path = rundir / "applied.jsonl" if rundir else None
        if not path or not path.exists():
            return []
        out = []
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                pass  # a line torn by the kill
        return out

    def wait_for(self, predicate, timeout=3600):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.proc.poll() is not None:
                raise SnapshotError(f"run {self.name} ended (exit {self.proc.returncode}) before the interruption point")
            if predicate(self.journal()):
                return
            time.sleep(0.2)
        raise SnapshotError(f"run {self.name}: interruption point not reached")

    def wait(self, timeout=7200):
        return self.proc.wait(timeout=timeout)

    def report(self):
        rundir = self.find_rundir()
        path = rundir / "report.json" if rundir else None
        return json.loads(path.read_text(encoding="utf-8")) if path and path.exists() else None


def statuses(journal):
    return dict(Counter(e.get("status") for e in journal))


def main():
    os.umask(0o077)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--restore")
    ap.add_argument("--term-after", type=int, default=200)
    ap.add_argument("--allow-mass-removal", action="store_true")
    args = ap.parse_args()
    extra = ["--allow-mass-removal"] if args.allow_mass_removal else []
    drilldir = IMPORT_ROOT / "drills" / time.strftime("%Y%m%dT%H%M%S")
    drilldir.mkdir(parents=True, mode=0o700)
    protocol = {"snapshot": args.snapshot, "restore": args.restore, "steps": []}

    def step(name, **data):
        protocol["steps"].append({"step": name, **data})
        log(f"{name}: " + json.dumps(data, ensure_ascii=False, sort_keys=True))
        write_private(drilldir / "protocol.json", json.dumps(protocol, ensure_ascii=False, indent=1))

    try:
        stand("backup.sh", "--label", "pre-drill")
        step("backup")
        if args.restore:
            stand("restore.sh", args.restore, "--yes", "--skip-custom")
            step("restore", backup=args.restore)
        if writers_alive():
            raise SnapshotError("a writer is already running")

        failures = []
        a = Run(args.snapshot, drilldir, "A-term", extra)
        a.wait_for(lambda j: sum(1 for e in j if e.get("status") in WRITES) >= args.term_after)
        os.kill(a.proc.pid, signal.SIGTERM)
        rc = a.wait(timeout=120)
        time.sleep(1)
        left = len(writers_alive())
        step("A: SIGTERM after writes", exit=rc, run=a.rundir.name if a.rundir else None,
             journal=statuses(a.journal()), writers_left=left, part_files=part_files())
        if rc != 130 or left:
            failures.append("A")

        b = Run(args.snapshot, drilldir, "B-kill", extra)
        # files are the last operations of a run (spec.ORDER): the first answered Attachment means the next file is
        # in flight — its part file, if the kill lands while its frames arrive, is left for run C to sweep
        b.wait_for(lambda j: any(str(e.get("key", "")).startswith("Attachment:") for e in j))
        parts_in_flight = part_files()
        os.killpg(b.proc.pid, signal.SIGKILL)
        subprocess.run(["sudo", "-n", "pkill", "-KILL", "-f", WRITER], check=False)
        b.wait(timeout=60)
        time.sleep(1)
        left = len(writers_alive())
        step("B: SIGKILL of importer and writer", run=b.rundir.name if b.rundir else None,
             journal=statuses(b.journal()), parts_in_flight=parts_in_flight, writers_left=left,
             part_files_left=part_files())
        if left:
            failures.append("B")

        c = Run(args.snapshot, drilldir, "C-converge", extra)
        rc = c.wait()
        rep = c.report() or {}
        step("C: converging run", exit=rc, run=c.rundir.name if c.rundir else None, status=rep.get("status"),
             problems=rep.get("problems"), swept=rep.get("swept"), journal=statuses(c.journal()),
             silence=rep.get("silence"))
        if rc not in (0, 2) or not rep or rep.get("problems"):  # pass or findings, a report without problems
            failures.append("C")

        f1, d1 = fingerprint.take("drill-before-d")
        d = Run(args.snapshot, drilldir, "D-repeat", extra)
        rc = d.wait()
        f2, d2 = fingerprint.take("drill-after-d")
        rep = d.report() or {}
        same = fingerprint.diff(d1, d2)
        journal = statuses(d.journal())
        step("D: repeat writes nothing", exit=rc, run=d.rundir.name if d.rundir else None, status=rep.get("status"),
             problems=rep.get("problems"), journal=journal, writes=sum(n for s, n in journal.items() if s not in QUIET),
             fingerprint_equal=same["equal"], fingerprint_tables=same["tables"], fingerprint_files=same["files"],
             fingerprints=[f1.name, f2.name])
        if (rc not in (0, 2) or not rep or rep.get("problems") or not same["equal"]
                or any(s not in QUIET for s in journal) or writers_alive()):
            failures.append("D")
        ok = not failures
        protocol["result"] = "pass" if ok else "fail"
        step("result", result=protocol["result"], failed_steps=failures)
        return 0 if ok else 1
    except SnapshotError as e:
        protocol["result"] = "error"
        step("error", message=str(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
