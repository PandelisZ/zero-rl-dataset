#!/usr/bin/env bash
# Schema + oracle validation. Exits non-zero on any oracle failure.
set -euo pipefail
export PATH="$HOME/.zero/bin:$PATH"
cd "$(dirname "$0")/.."
python3 tools/validators/validate_cir.py
python3 tools/validators/oracle_validate.py
