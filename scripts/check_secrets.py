#!/usr/bin/env python3
"""Scan files that would be committed (and optionally Git history) for secrets and personal data.

Usage:
  scripts/check_secrets.py                 # tracked + untracked-not-ignored files
  scripts/check_secrets.py --history       # also every blob in `git log -p --all`
  PII_HASHES=/path/pii-hashes.txt scripts/check_secrets.py
  scripts/check_secrets.py --self-test     # verify the rules on synthetic samples

Two layers:
1. Regex rules for secrets and PII shapes (keys, tokens, passwords, e-mails, phones, IPv4,
   long digit runs typical for INN/bank accounts).
2. If a private hash list exists (default /data/itvolga/espo-private/pii-hashes.txt, produced on
   the source host by scripts/audit/remote/pii_hashes.py), every word n-gram and digit run of
   every line is hashed and compared — this proves that no real CRM value (names, phones,
   e-mails, INN, accounts, access fields) is in the files.
Findings print file:line and the rule name only, never the matched text.
Allowed exceptions: scripts/check-secrets.allow (lines `path-glob<TAB>rule`).
"""
import fnmatch
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HASHES = Path(os.environ.get("PII_HASHES", "/data/itvolga/espo-private/pii-hashes.txt"))
ALLOW = REPO / "scripts" / "check-secrets.allow"

RULES = [
    ("private-key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("aws-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("openai-anthropic-key", re.compile(r"\bsk-(?:ant-)?[A-Za-z0-9_\-]{20,}\b")),
    ("slack-token", re.compile(r"\bxox[abprs]-[A-Za-z0-9\-]{10,}\b")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}")),
    # Also matches prefixed names such as DB_PASSWORD= or MY_API_KEY: (no word boundary before the keyword).
    ("password-assignment", re.compile(r"(?i)[A-Za-z0-9_\-]*(?:pass(?:word)?|passwd|secret|token|api[_-]?key)[A-Za-z0-9_\-]*"
                                       r"\s*[:=]\s*['\"]?(?P<value>[^\s'\"<>{}$]{6,})")),
    ("email", re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")),
    ("phone", re.compile(r"(?<![\w.])(?:\+7|\+49|8)[\s\-(]*\d{3}[\s\-)]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}(?![\w.])")),
    ("ipv4", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
    ("long-digits", re.compile(r"(?<![\w.:/-])\d{10,20}(?![\w.:/-])")),
]
# Commit attribution address and the documented SSH target of the source server (given in the task).
ALLOWED_EMAILS = {"noreply@anthropic.com", "sergey@serv.sergeyem.ru"}
# Placeholder values that are not secrets (checked against the assigned value only, not the whole line).
PLACEHOLDER = re.compile(r"(?i)^(\*+|x{3,}|changeme|redacted|example\w*|dummy|placeholder|%env\(.*|vault_\w+|"
                         r"none|null|true|false|required|\*\*\*redacted\*\*\*)[,;)\]]*$")
ALLOWED_EMAIL_DOMAINS = ("example.com", "example.org", "example.net")
ALLOWED_IPS = {"127.0.0.1", "0.0.0.0", "255.255.255.255"}
BINARY_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".phar", ".zip", ".gz", ".wav", ".mp3",
                   ".docx", ".xlsx", ".odt", ".sqlite", ".db")


def load_allow():
    """Returns (path_glob, rule) pairs; `pii-word<TAB>word` lines become ("pii-word", word)."""
    items = []
    if ALLOW.exists():
        for line in ALLOW.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                glob, _, rule = line.partition("\t")
                items.append((glob.strip(), rule.strip()))
    return items


def allowed(path, rule, allow):
    path = path.removeprefix("history:")
    return any(fnmatch.fnmatch(path, g) and (r == rule or r == "*") for g, r in allow)


def load_hashes():
    if not HASHES.exists():
        return None
    return {line.strip() for line in HASHES.read_text(encoding="utf-8").splitlines() if line.strip()}


def sha(v):
    return hashlib.sha256(v.encode("utf-8")).hexdigest()


def hash_candidates(line):
    low = re.sub(r"\s+", " ", line.lower())
    words = re.findall(r"[\w@.\-]+", low)
    for n in range(1, 5):
        for i in range(len(words) - n + 1):
            chunk = " ".join(words[i:i + n])
            if len(chunk) >= 5 and not chunk.isdigit():
                yield "t:" + sha(chunk), chunk
    for m in re.finditer(r"\+?\d[\d\s()\-]{5,}\d", line):
        d = re.sub(r"\D", "", m.group(0))
        if len(d) >= 7:
            yield "d:" + sha(d), d
            if len(d) > 10:
                yield "d:" + sha(d[-10:]), d[-10:]


def scan_text(name, text, hashes, allow, findings):
    for lineno, line in enumerate(text.splitlines(), 1):
        for rule, rx in RULES:
            for m in rx.finditer(line):
                val = m.group(0)
                if rule == "email" and (val.lower() in ALLOWED_EMAILS or val.lower().endswith(ALLOWED_EMAIL_DOMAINS)):
                    continue
                if rule == "ipv4" and (val in ALLOWED_IPS or any(int(o) > 255 for o in val.split("."))):
                    continue
                if rule == "password-assignment" and (PLACEHOLDER.match(m.group("value"))
                                                      or re.match(r"^[A-Za-z_][\w.]*\(", m.group("value"))):
                    continue  # placeholder or code expression such as TOKEN_RE = re.compile(...)
                if not allowed(name, rule, allow):
                    findings.append((name, lineno, rule))
        if hashes:
            generic = {r for g, r in allow if g == "pii-word"}
            for c, chunk in hash_candidates(line):
                if chunk in generic:
                    continue
                if c in hashes and not allowed(name, "pii-hash", allow):
                    # never print the matched text: it may be a real value (e.g. an access field)
                    findings.append((name, lineno, f"pii-hash(len={len(chunk)})"))
                    break


def worktree_files():
    out = subprocess.run(["git", "ls-files", "-co", "--exclude-standard", "-z"], cwd=REPO,
                         capture_output=True, check=True).stdout.decode("utf-8")
    return [p for p in out.split("\0") if p and (REPO / p).is_file()]


SELF_TEST = [
    ("DB_PASSWORD=Sup3rS3cretValue", "password-assignment"),
    ("MY_API_KEY: abcdef123456", "password-assignment"),
    ("$password = 'SecurePass123!';", "password-assignment"),
    ("token = ghp_" + "a" * 36, "github-token"),
    ("mail me: someone.real@company.test", "email"),
    ("call +7 (927) 123-45-67", "phone"),
    ("host 10.20.30.40", "ipv4"),
    ("account 40702810900000000001", "long-digits"),
]
SELF_TEST_CLEAN = ["password: '***REDACTED***'", "api_key = vault_api_key", "127.0.0.1:5000", "sergey@serv.sergeyem.ru"]


def self_test():
    ok = True
    for text, rule in SELF_TEST:
        found = []
        scan_text("selftest", text, None, [], found)
        if not any(r == rule for _, _, r in found):
            print(f"SELF-TEST MISS: rule {rule}")
            ok = False
    for text in SELF_TEST_CLEAN:
        found = []
        scan_text("selftest", text, None, [], found)
        if found:
            print(f"SELF-TEST FALSE POSITIVE: {[r for _, _, r in found]}")
            ok = False
    print("self-test:", "ok" if ok else "FAILED")
    sys.exit(0 if ok else 1)


def main():
    if "--self-test" in sys.argv:
        self_test()
    allow = load_allow()
    hashes = load_hashes()
    findings = []
    files = worktree_files()
    for p in files:
        # Binary files cannot be scanned; they are reported so a human decides (allow rule "binary-file").
        if p.lower().endswith(BINARY_SUFFIXES):
            if not allowed(p, "binary-file", allow):
                findings.append((p, 0, "binary-file"))
            continue
        try:
            text = (REPO / p).read_text(encoding="utf-8")
        except UnicodeDecodeError:
            if not allowed(p, "binary-file", allow):
                findings.append((p, 0, "binary-file"))
            continue
        scan_text(p, text, hashes, allow, findings)
    if "--history" in sys.argv:
        log = subprocess.run(["git", "log", "-p", "--all", "--no-color", "--format=commit %H"], cwd=REPO,
                             capture_output=True, check=True).stdout.decode("utf-8", "replace")
        current = "history"
        buf = []
        for line in log.splitlines():
            if line.startswith("+++ b/"):
                if buf:
                    scan_text(f"history:{current}", "\n".join(buf), hashes, allow, findings)
                current, buf = line[6:], []
            elif line.startswith("+") and not line.startswith("+++"):
                buf.append(line[1:])
        if buf:
            scan_text(f"history:{current}", "\n".join(buf), hashes, allow, findings)
    print(f"scanned files: {len(files)}; pii hash list: {'yes (' + str(len(hashes)) + ')' if hashes else 'not available'}")
    for name, lineno, rule in findings:
        print(f"FINDING {name}:{lineno} {rule}")
    print(f"findings: {len(findings)}")
    sys.exit(1 if findings else 0)


if __name__ == "__main__":
    main()
