# Converters

In this pilot the Zerolang path is implemented as **generators** (see
`tools/generators/`) rather than source converters, because the task substrate
is the locally-available `zerolang-examples` corpus plus synthetic templates —
not an external benchmark dump.

The brief's TerminalBench/Harbor converters are **deferred** (they need the
external TerminalBench/Harbor repositories and container infra, which were out
of scope for the locally verified zero-native pilot):

- `terminalbench_to_harbor.py` — not built. Would migrate legacy TerminalBench
  tasks into Harbor task directories (`instruction.md`, `task.toml`,
  `environment/`, `solution/`, `tests/`).
- `harbor_to_cir.py` — not built. Would emit `harbor_env` CIR rows pointing at
  Harbor task dirs (loaded at train time via Prime's `HarborTaskset`).

The Zerolang generators that ARE built and verified:

- `tools/generators/gen_zero_native.py` — synthetic single-file tasks; each
  fixture is compiled + run through `zero` and its real stdout captured.
- `tools/generators/gen_zero_repair.py` — breaks verified native fixtures into
  before-states that genuinely fail `zero check`.
- `tools/generators/gen_zero_package_edit.py` — stubs a tested function in each
  of the 10 `zerolang-examples` projects so `zero test` fails.
- `tools/generators/assemble_cir.py` — merges families into the canonical CIR.
