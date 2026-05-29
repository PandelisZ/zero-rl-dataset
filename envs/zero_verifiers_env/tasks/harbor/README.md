# Harbor-backed tasks (reserved directory)

Prime's `HarborTaskset` loads Harbor-format task directories from this reserved
`tasks/harbor/` directory (or fetches a Harbor Hub dataset by `owner/name`).
Each task directory follows the Harbor structure:

```
<org>/<task>/
  instruction.md
  task.toml
  environment/        # Dockerfile / compose / OS declaration
  solution/solve.sh
  tests/test.sh       # emits /logs/verifier/reward.json or reward.txt
```

## Status in this pilot: EMPTY (intentionally)

No Harbor tasks ship in dataset v0.1. Building them requires container build +
run infrastructure (Docker/Harbor) that was out of scope for the locally
verified zero-native pilot. The plumbing is in place: `load_environment(
family="harbor_env")` delegates to `HarborTaskset` over this directory and does
**not** re-implement Harbor scoring — Harbor test scripts own reward emission.

## To add Harbor tasks later

1. Convert TerminalBench/other tasks to Harbor format with
   `tools/converters/terminalbench_to_harbor.py` (not built in this pilot).
2. Drop the task dirs under `tasks/harbor/<org>/<task>/`.
3. Validate oracle solutions reach reward 1.0 before training
   (`tools/validators/validate_harbor_tasks.py` — not built in this pilot).
