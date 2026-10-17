#!/usr/bin/env python3
"""Places call recordings of a verified snapshot into the stand's recordings root (stage 07.2, D-177). Run only as
root by `scripts/stand/telephony.sh place-recordings <source dir>` (the importer, `--recordings place`); never on
production, where the files already are in the Asterisk directory and EspoCRM only reads them.

  stdin:  one JSON line per file {"i": n, "rel": "<hex of YYYY/MM/DD/<name>.wav>", "size": n, "sha256": "<hex>"}
  stdout: one JSON line per file {"i": n, "status": placed | present | conflict | source_missing | source_mismatch |
          unsafe | error} — no paths, no names (a recording name carries phone numbers)

- the root must be a real directory owned by the PBX uid, inside a state directory with the stand's ownership marker;
- the relative path must be the dialplan's layout (port of Core/RecordingPath::SAFE); every operation goes through
  directory descriptors opened with O_NOFOLLOW|O_DIRECTORY from the root's and the source's descriptors (a component
  replaced by a link meanwhile is refused, not followed — the PBX user owns the day directories); day directories are
  created 0750 for uid:gid (the root's default ACL lets EspoCRM read);
- the bytes are copied into a part file while hashing; size and sha256 must equal the sealed inventory, and the part
  file read back must equal them too (a short write is never published); the file is published with link(2): an
  existing file is never replaced — the same bytes are `present`, others a `conflict`;
- part files of an interrupted run are removed first.
"""
import argparse
import hashlib
import json
import os
import re
import secrets
import stat
import sys

SAFE = re.compile(r"^[0-9]{4}/[0-9]{2}/[0-9]{2}/[^/.\\\x00][^/\\\x00]{0,200}\.wav$")
PART = re.compile(r"^\.itvolga-place-[0-9a-f]{16}\.part$")
CHUNK = 1 << 20


def safe(rel):
    return bool(SAFE.match(rel)) and ".." not in rel.split("/")


DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW


def open_dirs(root_fd, parts, uid, gid):
    """The day directory as a descriptor, walked from the root's descriptor component by component: every step is
    opened with O_NOFOLLOW|O_DIRECTORY relative to the previous one, so a component replaced by a symbolic link
    meanwhile is refused instead of followed (the PBX user owns these directories). Created ones are 0750 uid:gid."""
    fd = os.dup(root_fd)
    try:
        for part in parts:
            try:
                os.mkdir(part, 0o750, dir_fd=fd)
                created = True
            except FileExistsError:
                created = False
            nxt = os.open(part, DIR_FLAGS, dir_fd=fd)
            if created:
                os.fchown(nxt, uid, gid)
            os.close(fd)
            fd = nxt
        return fd
    except OSError:
        os.close(fd)
        return None


def digest(fd):
    h, size = hashlib.sha256(), 0
    while True:
        chunk = os.read(fd, CHUNK)
        if not chunk:
            return size, h.hexdigest()
        h.update(chunk)
        size += len(chunk)


def open_source(source_fd, rel):
    """The snapshot file, walked from the source part's descriptor without following links."""
    parts = rel.split("/")
    fd = os.dup(source_fd)
    try:
        for part in parts[:-1]:
            nxt = os.open(part, DIR_FLAGS, dir_fd=fd)
            os.close(fd)
            fd = nxt
        return os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
    finally:
        os.close(fd)


def place(item, source_fd, root_fd, uid, gid):
    rel = bytes.fromhex(item["rel"]).decode("utf-8", "surrogateescape")
    if not safe(rel):
        return "unsafe"
    try:
        sfd = open_source(source_fd, rel)
    except FileNotFoundError:
        return "source_missing"
    except OSError:
        return "unsafe"  # a symbolic link or a non-directory below the snapshot's part
    parts = rel.split("/")
    try:
        if not stat.S_ISREG(os.fstat(sfd).st_mode):
            return "unsafe"
        dfd = open_dirs(root_fd, parts[:3], uid, gid)
        if dfd is None:
            return "unsafe"
        try:
            return publish(sfd, dfd, parts[3], item, uid, gid)
        finally:
            os.close(dfd)
    finally:
        os.close(sfd)


def write_all(fd, data):
    """os.write may write part of the buffer (a full disk, a signal): the rest is written until done or an error."""
    view = memoryview(data)
    while view:
        view = view[os.write(fd, view):]


def publish(sfd, dfd, name, item, uid, gid):
    """Part file in the day directory (by its descriptor), size and sha256 of the source checked, the part file read
    back and checked again, then link(2) under the final name: an existing file is never replaced."""
    tmp = f".itvolga-place-{secrets.token_hex(8)}.part"
    tfd = os.open(tmp, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=dfd)
    try:
        h, size = hashlib.sha256(), 0
        while True:
            chunk = os.read(sfd, CHUNK)
            if not chunk:
                break
            h.update(chunk)
            size += len(chunk)
            write_all(tfd, chunk)
        if size != item["size"] or h.hexdigest() != item["sha256"]:
            return "source_mismatch"
        os.fsync(tfd)
        os.lseek(tfd, 0, os.SEEK_SET)
        if digest(tfd) != (item["size"], item["sha256"]):
            return "error"  # the copy is not the bytes read: never published (external review 2026-10-17)
        os.fchown(tfd, uid, gid)
        os.fchmod(tfd, 0o644)
        try:
            os.link(tmp, name, src_dir_fd=dfd, dst_dir_fd=dfd, follow_symlinks=False)
            return "placed"
        except FileExistsError:
            try:
                efd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=dfd)
            except OSError:
                return "conflict"
            try:
                if not stat.S_ISREG(os.fstat(efd).st_mode):
                    return "conflict"
                return "present" if digest(efd) == (item["size"], item["sha256"]) else "conflict"
            finally:
                os.close(efd)
    finally:
        os.close(tfd)
        os.unlink(tmp, dir_fd=dfd)


def sweep(root_fd):
    """Part files of an interrupted run, found and removed through directory descriptors (no link followed)."""
    removed = 0
    for _dirpath, _dirs, files, dirfd in os.fwalk(dir_fd=root_fd, follow_symlinks=False):
        for name in files:
            if PART.match(name):
                os.unlink(name, dir_fd=dirfd)
                removed += 1
    return removed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--root", required=True)
    ap.add_argument("--uid", type=int, required=True)
    ap.add_argument("--gid", type=int, required=True)
    ap.add_argument("--marker", required=True)
    args = ap.parse_args()
    root, source = args.root.rstrip("/"), os.path.realpath(args.source)
    st = os.lstat(root) if os.path.lexists(root) else None
    if (st is None or not stat.S_ISDIR(st.st_mode) or st.st_uid != args.uid or os.path.realpath(root) != root
            or not os.path.isfile(args.marker) or os.path.dirname(args.marker) != os.path.dirname(root)
            or not os.path.isdir(source)):  # the root's parents belong to root: only the root is checked here
        print(json.dumps({"error": "root"}), flush=True)
        return 2
    root_fd = os.open(root, DIR_FLAGS)
    source_fd = os.open(source, DIR_FLAGS)
    try:
        if os.fstat(root_fd).st_uid != args.uid:
            print(json.dumps({"error": "root"}), flush=True)
            return 2
        sweep(root_fd)
        for line in sys.stdin:
            if not line.strip():
                continue
            item = json.loads(line)
            try:
                status = place(item, source_fd, root_fd, args.uid, args.gid)
            except (OSError, ValueError, KeyError):
                status = "error"
            print(json.dumps({"i": item.get("i"), "status": status}), flush=True)
    finally:
        os.close(root_fd)
        os.close(source_fd)
    return 0


if __name__ == "__main__":
    sys.exit(main())
