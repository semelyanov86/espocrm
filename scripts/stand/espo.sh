#!/usr/bin/env bash
# EspoCRM console (bin/command) as the web user with the pinned PHP version.
#   scripts/stand/espo.sh rebuild | clear-cache | version | app-check | run-job Cleanup | ...
# Do not run bin/command directly: its `#!/usr/bin/env php` may pick another PHP version,
# and files it creates would belong to the wrong user.
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
[[ $# -gt 0 ]] || set -- help
espo_cmd "$@"
