#!/usr/bin/env bash
set -euo pipefail
if command -v zero >/dev/null 2>&1; then echo "zero present: $(zero --version)"; exit 0; fi
[ -x "$HOME/.zero/bin/zero" ] || curl -fsSL https://zerolang.ai/install.sh | bash
export PATH="$HOME/.zero/bin:$PATH"
echo "installed: $(zero --version)"
echo 'add to profile: export PATH="$HOME/.zero/bin:$PATH"'
