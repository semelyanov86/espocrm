"""Shared helpers of the protected source snapshot (stage 06.1, docs/migration/snapshot.md).

Privacy rule for every module of this package: the console, logs written next to the code and the
protocol carry only step names, schema identifiers, counts, sizes and digests of whole artifacts —
never row values, file names of attachments or values of the contact access fields.
"""
import contextlib
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
from pathlib import Path

# Every artifact of this package is private: directories 700, files 600 from the first byte, whoever
# imports it (the CLI, tests, later importers).
os.umask(0o077)

REPO = Path(__file__).resolve().parents[2]
SNAPSHOT_ROOT = Path(os.environ.get("SNAPSHOT_ROOT", "/data/itvolga/espo-private/snapshots"))
SOURCE_HOST = os.environ.get("AUDIT_HOST", "sergey@serv.sergeyem.ru")
SSH_OPTS = ["-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "-o", "ServerAliveInterval=15",
            "-o", "ServerAliveCountMax=8"]
STAND_LIB = REPO / "scripts" / "stand" / "lib.sh"

FORMAT = "itvolga-vtiger-snapshot"
FORMAT_VERSION = 1
SOURCE_SCHEMAS = ("vtiger7", "asteriskcdrdb")

ID_RE = re.compile(r"^\d{8}T\d{6}$")
NAME_RE = re.compile(r"^[A-Za-z0-9_]+$")          # schema, table and column names we accept
TEMP_DB_RE = re.compile(r"^vtsnap_[0-9]{8}t[0-9]{6}_[0-9a-f]{6}_[a-z0-9_]+$")


class SnapshotError(Exception):
    """A failure whose message is written by this code and never contains source values."""


def log(msg):
    print(f"[snapshot] {msg}", file=sys.stderr, flush=True)


def mib(n):
    return f"{n / 1048576:.1f} MiB"


# --- private files ------------------------------------------------------------------------------

def _git_tree(path):
    """True if `path` (or its nearest existing ancestor) is inside a Git work tree."""
    p = path
    while not p.exists():
        p = p.parent
    r = subprocess.run(["git", "-C", str(p), "rev-parse", "--is-inside-work-tree"],
                       capture_output=True, text=True)
    return r.returncode == 0 and r.stdout.strip() == "true"


def ensure_root(root=SNAPSHOT_ROOT):
    """Snapshot root: outside any Git work tree, owned by us, mode 700, not a symlink."""
    root = Path(os.path.abspath(root))
    real = Path(os.path.realpath(root))
    if real == REPO or REPO in real.parents or _git_tree(real):
        raise SnapshotError(f"snapshot root {root} is inside a Git work tree")
    if not root.exists():
        os.makedirs(root, mode=0o700)
    st = os.lstat(root)
    if os.path.islink(root) or not os.path.isdir(root):
        raise SnapshotError(f"snapshot root {root} is not a plain directory")
    if st.st_uid != os.getuid() or (st.st_mode & 0o777) != 0o700:
        raise SnapshotError(f"snapshot root {root} must be owned by the current user with mode 700")
    return root


@contextlib.contextmanager
def root_lock(root, exclusive=True):
    fd = os.open(root / ".lock", os.O_RDWR | os.O_CREAT, 0o600)
    try:
        try:
            fcntl.flock(fd, (fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH) | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SnapshotError("another snapshot command holds the lock of the snapshot root") from None
        yield
    finally:
        os.close(fd)


def write_private(path, data):
    """Write a private file with mode 600 (directories are created 700 by the umask). A new inode
    replaces the old one atomically: never a half-written file, never a write through a hard link."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, str):
        data = data.encode("utf-8")
    tmp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def write_json(path, obj):
    write_private(path, json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True) + "\n")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_head():
    head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", str(REPO), "status", "--porcelain", "--", "scripts/snapshot", "scripts/audit"],
                           capture_output=True, text=True).stdout.splitlines()
    return head, len(dirty)


# --- MySQL clients ------------------------------------------------------------------------------

class Mysql:
    """A mysql command-line client: production over ssh (sudo, auth_socket) or the stand instance
    as MySQL root (scripts/stand/lib.sh mysql_root). Batch mode; values are never printed by us."""

    def __init__(self, argv, label):
        self.argv, self.label = argv, label

    @classmethod
    def production(cls, host=SOURCE_HOST):
        client = ("sudo -n mysql --batch --skip-column-names --quick --default-character-set=utf8mb4 "
                  "--max-allowed-packet=1G")
        return cls(["ssh", *SSH_OPTS, "-o", "Compression=yes", host, client], "production")

    @classmethod
    def stand(cls, database=None, headers=False, raw=False):
        args = ["--batch", "--quick", "--default-character-set=utf8mb4", "--max-allowed-packet=1G"]
        if not headers:
            args.append("--skip-column-names")
        if raw:
            args.append("--raw")
        if database:
            if not NAME_RE.match(database):
                raise SnapshotError("bad database name")
            args.append(database)
        return cls(["bash", "-c", 'source "$0"; mysql_root "$@"', str(STAND_LIB), *args], "stand")

    def session(self, script, consume, errlog):
        """Feed `script` to one client session; call consume(line_bytes) for every output line.
        stderr (it may quote values) goes to the private `errlog` only."""
        errlog.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(errlog, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, "ab") as err:
            proc = subprocess.Popen(self.argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=err)
            failed = []
            writer = threading.Thread(target=_feed, args=(proc.stdin, script, failed), daemon=True)
            writer.start()
            try:
                with proc.stdout:
                    for raw in proc.stdout:
                        if not raw.endswith(b"\n"):
                            raise SnapshotError(f"{self.label}: truncated client output")
                        consume(raw[:-1])
            except BaseException:
                proc.kill()
                proc.wait()
                raise
            rc = proc.wait()
            writer.join()
        if failed:  # the script generator failed: the client saw a partial script
            raise failed[0] if isinstance(failed[0], SnapshotError) else SnapshotError(
                f"{self.label}: preparing the SQL failed ({type(failed[0]).__name__})")
        if rc != 0:
            raise SnapshotError(f"{self.label}: mysql session failed (exit {rc}); details in {errlog}")

    def lines(self, script, errlog):
        out = []
        self.session(script, out.append, errlog)
        return out


def _feed(pipe, script, failed):
    """Write a str, bytes or an iterable of bytes chunks (streamed restore SQL) to the client;
    an exception of the generator is handed to the session through `failed`."""
    if isinstance(script, str):
        script = script.encode("utf-8")
    chunks = (script[i:i + (1 << 20)] for i in range(0, len(script), 1 << 20)) \
        if isinstance(script, bytes) else script
    try:
        for chunk in chunks:
            pipe.write(chunk)
    except (BrokenPipeError, OSError):
        pass  # the client exited early; its exit code reports the failure
    except BaseException as e:  # noqa: BLE001 — reported by the session
        failed.append(e)
    finally:
        try:
            pipe.close()
        except OSError:
            pass


def ssh_argv(remote_command):
    return ["ssh", *SSH_OPTS, SOURCE_HOST, remote_command]
