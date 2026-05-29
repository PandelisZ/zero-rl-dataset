#!/usr/bin/env bash
# Regenerate every dataset artifact from scratch (verified against `zero`).
set -euo pipefail
export PATH="$HOME/.zero/bin:$PATH"
cd "$(dirname "$0")/.."
python3 tools/generators/gen_zero_native.py
python3 tools/generators/gen_zero_repair.py
python3 tools/generators/gen_zero_package_edit.py
python3 tools/generators/assemble_cir.py
python3 tools/generators/cir_to_zero_cases.py
python3 tools/validators/compute_hashes.py
