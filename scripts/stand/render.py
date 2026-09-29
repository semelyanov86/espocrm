#!/usr/bin/env python3
"""Render a stand template: replace @@NAME@@ with the environment variable NAME.

Fails on any placeholder whose variable is unset, so a typo never produces a half-rendered
config. Other `$`/`${...}` syntax (Apache, systemd, shell) is left untouched.
"""
import os
import re
import sys

PLACEHOLDER = re.compile(r"@@([A-Z][A-Z0-9_]*)@@")


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: render.py TEMPLATE", file=sys.stderr)
        return 2
    with open(sys.argv[1], encoding="utf-8") as fh:
        text = fh.read()
    missing = sorted({name for name in PLACEHOLDER.findall(text) if name not in os.environ})
    if missing:
        print(f"render.py: unset variables in {sys.argv[1]}: {', '.join(missing)}", file=sys.stderr)
        return 1
    sys.stdout.write(PLACEHOLDER.sub(lambda m: os.environ[m.group(1)], text))
    return 0


if __name__ == "__main__":
    sys.exit(main())
