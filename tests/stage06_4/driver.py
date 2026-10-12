"""A run of the importer in a process of its own, for the interruption tests of stage 06.4 (test_stage06_4.py): the
parameters of the synthetic run come on stdin as JSON (never in argv), SIGTERM ends the run as the importer CLI does
(KeyboardInterrupt → exit 130). Prints nothing; the run directory gets the usual journal and report.
"""
import json
import signal
import sys
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "import"))
import importer  # noqa: E402
import spec  # noqa: E402


def _terminate(signum, frame):
    raise KeyboardInterrupt


def main():
    signal.signal(signal.SIGTERM, _terminate)
    p = json.loads(sys.stdin.read())
    with mock.patch.dict(spec.C.KB_CATEGORY, {"General": p["category"]}):
        try:
            importer.execute(Path(p["rundir"]), source_db=p["source"], only=p["only"], adopt=p["adopt"],
                             key_range=tuple(p["keys"]), effective_admin=p["admin"], files_root=p["files"],
                             allow_mass_removal=True)
        except KeyboardInterrupt:
            return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
