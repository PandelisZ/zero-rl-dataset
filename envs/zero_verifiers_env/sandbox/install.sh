#!/usr/bin/env bash
# Provision a Prime training/eval sandbox with BOTH the zerolang toolchain
# (`zero`) and the Roder agent harness (`roder`).
#
# Target platform: linux/amd64 (the public Roder binary is amd64-only).
# Idempotent-ish: safe to re-run; re-downloads binaries.
#
# Used by:
#   * sandbox/Dockerfile (bakes an image for Prime's `docker_image`)
#   * the RoderZero harness `setup` script (installs at rollout start)
set -euo pipefail

LOG_DIR="${LOG_DIR:-/logs/agent}"
mkdir -p "$LOG_DIR" "$HOME/.roder/bin"
: > "$LOG_DIR/setup-summary.txt"

log() { printf '%s\n' "$*" | tee -a "$LOG_DIR/setup-summary.txt"; }

# --- base OS deps -----------------------------------------------------------
if command -v apt-get >/dev/null 2>&1; then
    apt-get update -qq
    apt-get install -y -qq --no-install-recommends \
        ca-certificates curl coreutils python3 git build-essential >/dev/null 2>&1
    apt-get install -y -qq --no-install-recommends ripgrep >/dev/null 2>&1 || true
fi
if ! command -v python >/dev/null 2>&1 && command -v python3 >/dev/null 2>&1; then
    ln -sf "$(command -v python3)" /usr/local/bin/python
fi

# --- zerolang toolchain -----------------------------------------------------
# Tasks in this dataset are zerolang projects, so the sandbox MUST have `zero`.
if ! command -v zero >/dev/null 2>&1 && [ ! -x "$HOME/.zero/bin/zero" ]; then
    curl -fsSL https://zerolang.ai/install.sh | bash
fi
export PATH="$HOME/.zero/bin:$PATH"
log "zero: $(zero --version 2>&1 | head -1)"

# --- Roder harness ----------------------------------------------------------
case "$(uname -m)" in
    x86_64) ;;
    *) echo "Roder public binary is linux/amd64 only; got $(uname -m)" >&2; exit 1 ;;
esac
RODER_BINARY_URL="${RODER_BINARY_URL:-https://dl.roder.sh/zero-coder-roder-x86_64-unknown-linux-gnu}"
RODER_CONFIG_URL="${RODER_CONFIG_URL:-https://dl.roder.sh/zero-coder-roder.config.toml}"
curl -fsSL "$RODER_BINARY_URL" -o "$HOME/.roder/bin/roder"
chmod 0755 "$HOME/.roder/bin/roder"
curl -fsSL "$RODER_CONFIG_URL" -o "$HOME/.roder/zero-coder.config.toml" || true
export PATH="$HOME/.roder/bin:$PATH"
log "roder: installed from $RODER_BINARY_URL"
roder exec --help >"$LOG_DIR/roder-exec-help.txt" 2>&1 || true

log "sandbox ready: zero + roder on PATH ($HOME/.zero/bin, $HOME/.roder/bin)"
