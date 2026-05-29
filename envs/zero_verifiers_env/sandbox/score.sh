#!/usr/bin/env bash
# In-sandbox verifier: after the Roder agent edits the zerolang project, run the
# native `zero` toolchain and emit a Harbor-style reward.
#
# Emits BOTH /logs/verifier/reward.json and reward.txt (Harbor reads JSON first,
# falls back to text). Mirrors the reward shaping in tools/graders/zero_reward.py.
#
# Config via env vars:
#   ZERO_TASK_FAMILY   zero_native | zero_repair | zero_package_edit (default package)
#   ZERO_WORKDIR       project / file dir (default /app)
#   ZERO_ENTRY         entry file for single-file tasks (default main.0)
#   ZERO_EXPECTED_STDOUT_FILE  optional file with expected stdout (native/repair)
set -uo pipefail
export PATH="$HOME/.zero/bin:$PATH"

FAMILY="${ZERO_TASK_FAMILY:-zero_package_edit}"
WORKDIR="${ZERO_WORKDIR:-/app}"
ENTRY="${ZERO_ENTRY:-main.0}"
OUT_DIR="${VERIFIER_LOG_DIR:-/logs/verifier}"
mkdir -p "$OUT_DIR"
cd "$WORKDIR" 2>/dev/null || true

reward="0.0"

emit() {
    printf '%s' "$1" > "$OUT_DIR/reward.txt"
    printf '{"reward": %s, "metrics": %s}\n' "$1" "${2:-{}}" > "$OUT_DIR/reward.json"
    echo "reward=$1"
}

if [ "$FAMILY" = "zero_package_edit" ]; then
    check=0; tests=0; run=0
    zero check . >/dev/null 2>&1 && check=1
    if [ "$check" = 1 ]; then
        if zero test . 2>&1 | grep -q "test(s) ok"; then tests=1; fi
        zero run . >/dev/null 2>&1 && run=1
    fi
    reward=$(awk -v c="$check" -v t="$tests" -v r="$run" 'BEGIN{printf "%.4f", 0.05 + 0.25*c + 0.50*t + 0.20*r}')
    emit "$reward" "{\"zero_check\": $check, \"tests_pass\": $tests, \"zero_run\": $run}"
else
    check=0; run=0; stdout_match=0
    zero check "$ENTRY" >/dev/null 2>&1 && check=1
    actual="$(zero run "$ENTRY" 2>/dev/null)"; [ $? -eq 0 ] && run=1
    if [ -n "${ZERO_EXPECTED_STDOUT_FILE:-}" ] && [ -f "$ZERO_EXPECTED_STDOUT_FILE" ]; then
        expected="$(cat "$ZERO_EXPECTED_STDOUT_FILE")"
        [ "$actual" = "$expected" ] && stdout_match=1
    else
        stdout_match=$run
    fi
    reward=$(awk -v c="$check" -v r="$run" -v s="$stdout_match" 'BEGIN{printf "%.4f", 0.05 + 0.30*c + 0.25*r + 0.40*s}')
    emit "$reward" "{\"zero_check\": $check, \"zero_run\": $run, \"stdout_match\": $stdout_match}"
fi
