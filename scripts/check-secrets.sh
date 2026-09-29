#!/usr/bin/env bash
# Pre-commit check for secrets and personal data (see scripts/check_secrets.py).
#   scripts/check-secrets.sh            # files that would be committed
#   scripts/check-secrets.sh --history  # plus the whole Git history
set -euo pipefail
exec python3 "$(dirname "${BASH_SOURCE[0]}")/check_secrets.py" "$@"
