#!/bin/bash
# Usage (from anywhere):
#   scripts/misc/run_resources.sh              # every directory in output/, plus the overview
#   scripts/misc/run_resources.sh DIR [DIR...] # only these output directories (no overview)

set -euo pipefail

RICA_S_HOME="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$RICA_S_HOME"

python3 -m scripts.evaluate_resources "$@"
