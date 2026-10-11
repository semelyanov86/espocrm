"""Files of the import (stage 06.3, docs/migration/import.md «Файлы»): the snapshot's file part as the source, the
attachment → file resolution of the snapshot verification (verify.resolve_attachments: never the unsealed report of a
past verification), the bytes for the writer's stdin, and the check of every imported file through the stand: a
download as the administrator (?entryPoint=download) must answer 200 with the source sha256.

Nothing here prints a file name, a path or bytes; reports carry ids, statuses, sizes and digests only.
"""
import base64
import hashlib
import ipaddress
import os
import socket
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlencode, urlsplit

import verify  # scripts/snapshot (on sys.path through source)

CHUNK = 3 * 1024 * 1024  # raw bytes per stdin line: base64 stays under the writer's 8 MiB line limit
PRIVATE_ENV = Path(os.environ.get("STAND_PRIVATE_ENV", "/data/itvolga/espo-private/stand/local.env"))
BASE = os.environ.get("ESPO_SITE_URL", "http://crm.itvolga.test").rstrip("/")


class SnapshotFiles:
    """The `vtiger` file part of a verified snapshot: inventory/vtiger.tsv (sealed by SHA256SUMS, checked by V1 of
    verify.restored_databases) and files/vtiger/<relpath>."""

    def __init__(self, snapdir):
        self.root = Path(snapdir) / "files" / "vtiger"
        self.inventory = verify.read_inventory(Path(snapdir), "vtiger")  # relpath (bytes) → (size, mtime_ns, sha256)

    def open(self, rel):
        path = self.root / os.fsdecode(rel)
        if not path.resolve().is_relative_to(self.root.resolve()) or path.is_symlink():
            raise OSError("file outside the snapshot part")
        return open(path, "rb")


class DirectoryFiles(SnapshotFiles):
    """A directory as the file part (synthetic tests): the inventory is computed."""

    def __init__(self, root):
        self.root = Path(root)
        self.inventory = {}
        for path in sorted(self.root.rglob("*")):
            if path.is_file():
                data = path.read_bytes()
                rel = os.fsencode(path.relative_to(self.root))
                self.inventory[rel] = (len(data), 0, hashlib.sha256(data).hexdigest())


def resolve(attachment_rows, crm, files):
    """attachment id → {status, rel, size, sha256} by the rules of the snapshot verification (4 name variants, then a
    unique `<id>_` prefix; ambiguous is not found). The planner uses `found` ones only."""
    rows = []
    for r in attachment_rows:
        att = r["vtiger_attachments.attachmentsid"]
        setype, deleted = crm.get(int(att), ("", False))
        rows.append((att, setype, "1" if deleted else "0", (r.get("vtiger_attachments.path") or "").encode().hex(),
                     (r.get("vtiger_attachments.name") or "").encode().hex()))
    out = {}
    for att, _setype, _deleted, status, rel in verify.resolve_attachments(rows, files.inventory):
        size, _mtime, sha = files.inventory.get(rel, (0, 0, "")) if rel else (0, 0, "")
        out[int(att)] = {"status": status, "rel": rel, "size": size, "sha256": sha}
    return out


def chunk_lines(files, rel, size):
    """The stdin lines carrying a file: {"seq": n, "data": base64}, exactly chunk_count(size) of them whatever the file
    holds now, so the next operation is never read as a frame. The writer checks size and sha256 against the sealed
    inventory: a shorter file is refused there; a longer one stops the run after its frames."""
    import json
    with files.open(rel) as fh:
        left = size
        for seq in range(chunk_count(size)):
            block = fh.read(min(CHUNK, left)) if left > 0 else b""
            left -= len(block)
            yield (json.dumps({"seq": seq, "data": base64.b64encode(block).decode("ascii")}) + "\n").encode()
        if fh.read(1):
            raise verify.SnapshotError("a file of the snapshot is longer than its sealed inventory")


def chunk_count(size):
    return max(1, -(-size // CHUNK))


# --- the check through the stand -------------------------------------------------------------------------------

def _admin():
    values = {}
    for line in PRIVATE_ENV.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            values[k.strip()] = v.strip().strip("'\"")
    return values["ESPO_ADMIN_USERNAME"], values["ESPO_ADMIN_PASSWORD"]


def _assert_loopback():
    host = urlsplit(BASE).hostname
    addrs = {info[4][0] for info in socket.getaddrinfo(host, 80, proto=socket.IPPROTO_TCP)}
    if not addrs or not all(ipaddress.ip_address(a).is_loopback for a in addrs):
        raise OSError("the stand does not resolve to loopback only: credentials are not sent")


def download_check(items, credentials=None):
    """items: [(key, attachment id, size, sha256)] → {key: {"http": status, "size": ok, "sha256": ok, "reason": …}}.
    Every file is downloaded as the administrator (the owner's answer 2026-10-11: «access» = 200 and the source
    sha256); bytes are hashed on the way and dropped."""
    _assert_loopback()
    auth = base64.b64encode(":".join(credentials or _admin()).encode()).decode()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
    out = {}
    for key, attachment_id, size, sha256 in items:
        url = f"{BASE}/?" + urlencode({"entryPoint": "download", "id": attachment_id})
        request = urllib.request.Request(url, headers={"Espo-Authorization": auth})
        digest, received, status = hashlib.sha256(), 0, None
        try:
            with opener.open(request, timeout=60) as response:
                status = response.status
                while True:
                    block = response.read(1 << 20)
                    if not block:
                        break
                    digest.update(block)
                    received += len(block)
        except urllib.error.HTTPError as err:
            status = err.code
        except (urllib.error.URLError, OSError):
            status = "unreachable"
        ok = status == 200 and received == size and digest.hexdigest() == sha256
        out[key] = {"http": status, "size": received == size, "sha256": digest.hexdigest() == sha256,
                    "reason": None if ok else ("http_status" if status != 200 else
                                               "size" if received != size else "sha256")}
    return out


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None
