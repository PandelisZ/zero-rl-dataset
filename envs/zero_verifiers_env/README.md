# zero_verifiers_env

Prime `verifiers` environment package for the Zero RL dataset. Exposes
`load_environment(family, split, harness=...)`.

## Self-contained

The native grader is **vendored** into this package
(`zero_grader.py`, `zero_runner.py`, `zero_reward.py`) so it installs and runs
standalone on the Prime Hub. The grader shells out to the `zero` binary, so the
host/sandbox must have zerolang installed (`curl -fsSL https://zerolang.ai/install.sh | bash`).

## Two harnesses

`load_environment(..., harness=...)`:

| harness | execution | sandbox | verified |
|---|---|---|---|
| `deterministic` (default) | single-turn: model emits Zero source → graded by `zero check/run/test` | no | ✅ local + online |
| `tools` | multi-turn tool use with the **Roder zero-coder tool surface** (local `zero`); final source graded | no | ✅ local + online |
| `roder-zero` | agentic: the **Roder** agent binary edits the project in a sandbox; scored by `score.sh` → `reward.json` | yes (linux/amd64) | ⚠️ needs Prime + amd64 |

### Zero-coder tools (`harness="tools"`)

Mirrors `roder-ext-zerolang` exactly (same names/semantics, backed by local
`zero`), so a policy trained here transfers to the Roder harness:

`zerolang_skills_get`, `zerolang_check`, `zerolang_graph_dump`,
`zerolang_graph_view`, `zerolang_fix_plan`, `zerolang_edit` (checked
ProgramGraph patch via graphHash + node/`expect`/`value` operations),
`zerolang_graph_roundtrip`. The system prompt teaches Roder's checked edit loop
(dump → edit with `expect` precondition → check). Adaptation: tool `input` is
source TEXT (stateless) rather than a workspace path.

Online proof (gpt-4.1-mini, zero_repair val): the model issued 4.2 tool
calls/rollout (graph_dump 1.9, edit 1.7) — see eval
`zjlz90huing3mbb604pubmbs`.

### Families
`zero_native`, `zero_repair`, `zero_package_edit` (graded by the Zero toolchain),
and `harbor_env` (delegated to Prime `HarborTaskset`; no tasks in the pilot).

## The sandbox (`sandbox/`)

Provisions a Prime training/eval sandbox with **both** `zero` and `roder`:

- `install.sh` — installs the zerolang toolchain (zerolang.ai) **and** Roder
  (dl.roder.sh) + base deps. Used by the Dockerfile and by the Roder harness `setup`.
- `Dockerfile` — bakes `zero-roder-sandbox` (linux/amd64) for Prime's `docker_image`.
  `docker build --platform=linux/amd64 -t zero-roder-sandbox sandbox`
- `score.sh` — in-sandbox verifier: runs `zero check/test/run` after the agent
  edits and writes `/logs/verifier/reward.json` (+ `reward.txt`), the Harbor
  reward contract. Mirrors `zero_reward.py` shaping.

`roder_zero.py` is the `CLIHarness` (adapted from graphlanger's
`harbor_terminal_bench` roder-zero, **extended to install `zero`**). It runs:

```
roder exec --json --profile eval --mode bypass --skip-git-repo-check --task-ledger-required -
```

with an API-intercepted config (`OPENAI_BASE_URL`). Roder is amd64-only.

## load_environment args

| arg | default | notes |
|---|---|---|
| `family` | `zero_native` | task family / env id |
| `split` | `train` | `train`/`val`/`test` |
| `max_examples` | `None` | cap for smoke runs |
| `harness` | `deterministic` | or `tools` (zero-coder tools) or `roder-zero` |
| `max_turns` | `6` | `tools` harness only |
| `dataset_root` | repo `datasets/cir` | CIR location |
| `docker_image` | `zero-roder-sandbox:latest` | roder-zero only |
| `roder_binary_url` / `roder_config_url` | `dl.roder.sh` defaults | roder-zero only |
| `roder_soft_timeout_sec` | `900` | roder-zero only |

## Validate

```sh
# deterministic path (works anywhere with `zero`):
python -m zero_verifiers_env.harness zero_package_edit val

# Prime (deterministic):
prime env install ./envs/zero_verifiers_env
prime eval run prime/eval.zero.toml

# Prime (roder-zero sandbox, amd64):
docker build --platform=linux/amd64 -t zero-roder-sandbox envs/zero_verifiers_env/sandbox
prime eval run prime/train.roder.toml   # smoke before rl run
```
