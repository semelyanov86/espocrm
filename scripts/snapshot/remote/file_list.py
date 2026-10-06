"""List regular files under ROOT/PATH... with sha256, size and mtime; symlinks are never followed.

Runs on the source host (inline through `python3 -c`, as root; nothing is written there) and
locally on the copy. stdout: NUL-terminated records `<sha256|unstable>\\t<size>\\t<mtime_ns>\\t<relpath>`
(relpath relative to ROOT, raw bytes), then `#missing\\t<path>` for absent PATHs and
`#summary\\t<symlinks>\\t<special files>`. A file whose size, mtime or inode changes while it is read,
or that vanishes or cannot be read, is reported as `unstable` (the caller retries, then fails). A
directory that cannot be listed aborts the run (exit 3): a partial inventory is never printed. Errors
name the failing operation and errno only — never a path (file names may contain personal data).

    python3 file_list.py ROOT PATH...
"""
import hashlib
import os
import stat
import sys


class WalkError(Exception):
    pass


def walk_error(err):
    raise WalkError(err.errno)


def digest(path, before):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError:
        return "unstable"
    try:
        h = hashlib.sha256()
        while True:
            chunk = os.read(fd, 1 << 20)
            if not chunk:
                break
            h.update(chunk)
        after = os.fstat(fd)
    finally:
        os.close(fd)
    try:
        again = os.lstat(path)
    except OSError:
        return "unstable"
    same = all((a.st_size, a.st_mtime_ns, a.st_ino) == (before.st_size, before.st_mtime_ns, before.st_ino)
               for a in (after, again))
    return h.hexdigest() if same else "unstable"


def main():
    root = os.fsencode(sys.argv[1])
    out = []
    symlinks = special = 0
    for rel in (os.fsencode(a) for a in sys.argv[2:]):
        base = os.path.normpath(os.path.join(root, rel))
        if os.path.islink(base) or not os.path.isdir(base):
            out.append(b"#missing\t" + rel)
            continue
        for dirpath, dirnames, filenames in os.walk(base, onerror=walk_error):
            for d in list(dirnames):
                if os.path.islink(os.path.join(dirpath, d)):
                    symlinks += 1
                    dirnames.remove(d)
            for name in filenames:
                path = os.path.join(dirpath, name)
                try:
                    st = os.lstat(path)
                except OSError:  # vanished between listing and stat
                    out.append(b"\t".join([b"unstable", b"0", b"0", os.path.relpath(path, root)]))
                    continue
                if stat.S_ISLNK(st.st_mode):
                    symlinks += 1
                elif not stat.S_ISREG(st.st_mode):
                    special += 1
                else:
                    relpath = os.path.relpath(path, root)
                    out.append(b"\t".join([digest(path, st).encode(), str(st.st_size).encode(),
                                           str(st.st_mtime_ns).encode(), relpath]))
    records = sorted(r for r in out if not r.startswith(b"#")) + [r for r in out if r.startswith(b"#")]
    records.append(b"#summary\t%d\t%d" % (symlinks, special))
    sys.stdout.buffer.write(b"\0".join(records) + b"\0")


try:
    main()
except WalkError as e:
    sys.stderr.write(f"file_list: a directory could not be listed (errno {e.args[0]})\n")
    sys.exit(3)
except OSError as e:
    sys.stderr.write(f"file_list: {type(e).__name__} (errno {e.errno})\n")
    sys.exit(3)
