"""Roder-Zero harness for sandboxed zerolang editing tasks.

Adapted from graphlanger's `harbor_terminal_bench` RoderZero, with one key
addition: the sandbox `setup` script installs the **zerolang toolchain** (`zero`)
alongside Roder, because the tasks in this dataset are zerolang projects and the
agent (and the in-sandbox scorer) must be able to run `zero check/run/test`.

This module is imported lazily by `load_environment(harness="roder-zero")`; it
requires the `verifiers` package and a linux/amd64 sandbox (the public Roder
binary is amd64-only). Reward is produced by the taskset rubric / score.sh, not
here — Roder is only the agent runner.
"""
from __future__ import annotations

import json
import shlex
from pathlib import PurePosixPath
from typing import Any

from verifiers.v1.packages.harnesses.cli import CLIHarness
from verifiers.v1.utils.prompt_utils import (
    state_system_prompt_text,
    task_text as task_instruction_text,
)

DEFAULT_AGENT_WORKDIR = "/app"
DEFAULT_BINARY_URL = "https://dl.roder.sh/zero-coder-roder-x86_64-unknown-linux-gnu"
DEFAULT_CONFIG_URL = "https://dl.roder.sh/zero-coder-roder.config.toml"
DEFAULT_ZERO_INSTALL_URL = "https://zerolang.ai/install.sh"
DEFAULT_INSTRUCTION_PATH = "/roder/instruction.txt"
DEFAULT_SYSTEM_PROMPT_PATH = "/roder/system.txt"
DEFAULT_LOG_PATH = "/logs/agent/roder-cli.txt"
DEFAULT_EVENTS_PATH = "/logs/agent/roder-events.jsonl"
DEFAULT_STDERR_PATH = "/logs/agent/roder-stderr.txt"
DEFAULT_LAST_MESSAGE_PATH = "/logs/agent/roder-last-message.txt"
DEFAULT_SETUP_SUMMARY_PATH = "/logs/agent/setup-summary.txt"
DEFAULT_SYSTEM_PROMPT = """\
You are Roder running as a Zero coding agent. You are editing a zerolang (`.0`)
project in the sandbox. Make the requested change, then verify with the native
toolchain: `zero check .` must pass and, for package tasks, `zero test .` must
pass. Prefer checked, minimal edits; do not rewrite unrelated files.
"""


class RoderZero(CLIHarness):
    def __init__(
        self,
        *,
        agent_workdir: str = DEFAULT_AGENT_WORKDIR,
        binary_url: str = DEFAULT_BINARY_URL,
        config_url: str = DEFAULT_CONFIG_URL,
        zero_install_url: str = DEFAULT_ZERO_INSTALL_URL,
        instruction_path: str = DEFAULT_INSTRUCTION_PATH,
        system_prompt_path: str = DEFAULT_SYSTEM_PROMPT_PATH,
        log_path: str = DEFAULT_LOG_PATH,
        events_path: str = DEFAULT_EVENTS_PATH,
        stderr_path: str = DEFAULT_STDERR_PATH,
        last_message_path: str = DEFAULT_LAST_MESSAGE_PATH,
        setup_summary_path: str = DEFAULT_SETUP_SUMMARY_PATH,
        system_prompt: object | None = DEFAULT_SYSTEM_PROMPT,
        policy_mode: str = "bypass",
        reasoning: str = "medium",
        soft_timeout_sec: int | None = 900,
        task_ledger_required: bool = True,
        max_turns: int | None = 8,
        **kwargs: Any,
    ):
        files: dict[str, object] = {instruction_path: task_instruction_text}
        if system_prompt is not None:
            files[system_prompt_path] = state_system_prompt_text

        artifacts = {
            "roder_log": {"path": log_path, "format": "text", "optional": True},
            "roder_events": {"path": events_path, "format": "text", "optional": True},
            "roder_stderr": {"path": stderr_path, "format": "text", "optional": True},
            "roder_last_message": {"path": last_message_path, "format": "text", "optional": True},
            "roder_setup_summary": {"path": setup_summary_path, "format": "text", "optional": True},
        }

        super().__init__(
            command=[
                "bash",
                "-lc",
                build_roder_run_script(
                    agent_workdir=agent_workdir,
                    instruction_path=instruction_path,
                    system_prompt_path=system_prompt_path if system_prompt is not None else None,
                    log_path=log_path,
                    events_path=events_path,
                    stderr_path=stderr_path,
                    last_message_path=last_message_path,
                    setup_summary_path=setup_summary_path,
                    policy_mode=policy_mode,
                    reasoning=reasoning,
                    soft_timeout_sec=soft_timeout_sec,
                    task_ledger_required=task_ledger_required,
                ),
            ],
            files=files,
            setup=build_install_script(
                binary_url=binary_url, config_url=config_url, zero_install_url=zero_install_url
            ),
            artifacts=artifacts,
            system_prompt=system_prompt,
            max_turns=max_turns,
            **kwargs,
        )


def build_install_script(*, binary_url: str, config_url: str, zero_install_url: str) -> str:
    """Install the zerolang toolchain AND Roder into the sandbox."""
    return f"""\
set -e
mkdir -p /logs/agent "$HOME/.roder/bin"
touch /logs/agent/setup-summary.txt /logs/agent/roder-stderr.txt

apt-get update -qq
apt-get install -y -qq --no-install-recommends ca-certificates curl coreutils python3 git > /dev/null 2>&1
apt-get install -y -qq --no-install-recommends ripgrep > /dev/null 2>&1 || true
if ! command -v python >/dev/null 2>&1 && command -v python3 >/dev/null 2>&1; then
  ln -s "$(command -v python3)" /usr/local/bin/python
fi

# zerolang toolchain (tasks are zerolang projects; agent + scorer need `zero`)
if ! command -v zero >/dev/null 2>&1 && [ ! -x "$HOME/.zero/bin/zero" ]; then
  curl -fsSL {shlex.quote(zero_install_url)} | bash
fi
export PATH="$HOME/.zero/bin:$PATH"
printf 'zero: %s\\n' "$(zero --version 2>&1 | head -1)" >> /logs/agent/setup-summary.txt

case "$(uname -m)" in
  x86_64) ;;
  *) echo "Roder Zero public binary is currently published for linux/amd64 only; got $(uname -m)" >&2; exit 1 ;;
esac

curl -fsSL {shlex.quote(binary_url)} -o "$HOME/.roder/bin/roder"
chmod 0755 "$HOME/.roder/bin/roder"
curl -fsSL {shlex.quote(config_url)} -o "$HOME/.roder/zero-coder.config.toml" || true

export PATH="$HOME/.roder/bin:$HOME/.zero/bin:$PATH"
roder exec --help >/logs/agent/roder-exec-help.txt 2>>/logs/agent/roder-stderr.txt
printf 'Roder Zero installed from %s\\n' {shlex.quote(binary_url)} >> /logs/agent/setup-summary.txt
"""


def build_roder_run_script(
    *,
    agent_workdir: str,
    instruction_path: str,
    system_prompt_path: str | None,
    log_path: str,
    events_path: str,
    stderr_path: str,
    last_message_path: str,
    setup_summary_path: str,
    policy_mode: str,
    reasoning: str,
    soft_timeout_sec: int | None,
    task_ledger_required: bool,
) -> str:
    log_dir = str(PurePosixPath(log_path).parent)
    timeout_prefix = ""
    if soft_timeout_sec:
        timeout_prefix = f"timeout -k 5s -s INT {shlex.quote(str(soft_timeout_sec) + 's')} "
    ledger_flag = " --task-ledger-required" if task_ledger_required else ""
    return f"""\
set -uo pipefail
export PATH="$HOME/.roder/bin:$HOME/.zero/bin:/usr/local/bin:$PATH"
export OPENAI_API_KEY="${{OPENAI_API_KEY:-intercepted}}"

RODER_WORKDIR="${{AGENT_WORKDIR:-}}"
if [[ -z "$RODER_WORKDIR" ]]; then
    RODER_WORKDIR={shlex.quote(agent_workdir)}
fi

RODER_CONFIG_DIR="${{RODER_CONFIG_DIR:-$HOME/.roder-zero}}"
export RODER_CONFIG_DIR
export RODER_DATA_DIR="${{RODER_DATA_DIR:-$RODER_CONFIG_DIR}}"

mkdir -p {shlex.quote(log_dir)} "$RODER_WORKDIR" "$RODER_CONFIG_DIR"
: > {shlex.quote(events_path)}
: > {shlex.quote(stderr_path)}
: > {shlex.quote(log_path)}
: > {shlex.quote(last_message_path)}
: > {shlex.quote(setup_summary_path)}

if [[ -z "${{OPENAI_BASE_URL:-}}" ]]; then
    printf 'OPENAI_BASE_URL is required for Verifiers API interception\\n' | tee -a {shlex.quote(stderr_path)}
    exit 2
fi

cat > "$RODER_CONFIG_DIR/config.toml" <<EOFCONFIG
provider = "poolside"
model = "model"
reasoning = {json.dumps(reasoning)}
runtime_profile = "eval"

[providers.poolside]
base_url = "${{OPENAI_BASE_URL}}"
api_key_env = "OPENAI_API_KEY"

[sessions]
store = "jsonl"

[zerolang]
timeout_seconds = 30
artifact_dir = ".zero/roder"

[context]
file_backed_dynamic_context = true

[speed_policy]
enabled = true
eval_deadline_seconds = 600

[policy_modes]
default = {json.dumps(policy_mode)}
warn_on_bypass = false
EOFCONFIG

cd "$RODER_WORKDIR"
printf 'roder exec starting in %s\\n' "$RODER_WORKDIR" >> {shlex.quote(setup_summary_path)}

if [[ -n {shlex.quote(system_prompt_path or "")} && -f {shlex.quote(system_prompt_path or "")} ]]; then
    RODER_PROMPT="$(printf '%s\\n\\nTask:\\n%s' "$(cat {shlex.quote(system_prompt_path or "/dev/null")})" "$(cat {shlex.quote(instruction_path)})")"
else
    RODER_PROMPT="$(cat {shlex.quote(instruction_path)})"
fi

set +e
printf '%s' "$RODER_PROMPT" | {timeout_prefix}roder exec \
  --json \
  --profile eval \
  --mode {shlex.quote(policy_mode)} \
  --skip-git-repo-check{ledger_flag} \
  --output-last-message {shlex.quote(last_message_path)} \
  - > {shlex.quote(events_path)} 2> {shlex.quote(stderr_path)}
status=$?
set -e

if [[ -s {shlex.quote(last_message_path)} ]]; then
    cp {shlex.quote(last_message_path)} {shlex.quote(log_path)}
else
    printf 'roder exec exited with status %s before writing a final message\\n' "$status" > {shlex.quote(log_path)}
fi

if [[ -s {shlex.quote(stderr_path)} ]]; then
    printf '\\n--- roder stderr ---\\n' >> {shlex.quote(log_path)}
    cat {shlex.quote(stderr_path)} >> {shlex.quote(log_path)}
fi

printf 'roder exec finished with status %s\\n' "$status" >> {shlex.quote(setup_summary_path)}
case "$status" in
  124|130|137|143)
    printf 'roder exec soft-timed-out before sandbox hard timeout\\n' >> {shlex.quote(setup_summary_path)}
    exit 0
    ;;
esac
exit "$status"
"""
