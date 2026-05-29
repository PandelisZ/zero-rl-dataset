# Conversion Report — Zero RL dataset v0.2

Generated against `zero 0.2.0`. Substrate: `zerolang-examples` (now 26 projects,
expanded from 10 by an agent team).

## Families produced

| Family | Tasks | How |
|---|---:|---|
| `zero_native` | 92 | Synthetic single-file templates (28 builders × params). Each fixture compiled + run through `zero`; **expected stdout captured from the real run** (never hand-written). |
| `zero_repair` | 92 | Each verified native fixture broken by one transform (drop `raises`, drop `check`, wrong return type, misspelled call). Each before-state **verified to fail `zero check`**; diagnostics recorded. |
| `zero_package_edit` | 47 | Tested functions across all 26 `zerolang-examples` projects (auto-discovered, up to 3/project) replaced with a type-correct but wrong stub → **compiles but fails `zero test`**. Oracle = original project. |
| `harbor_env` | 0 | Deferred — needs Harbor/TerminalBench + container infra (see `envs/.../tasks/harbor/README.md`). |

**Total: 231 tasks** (v0.1 was 126). Splits (deterministic, balanced ~80/10/10): train 187, val 22, test 22.

Difficulty distribution: 1→35, 2→87, 3→104, 4→5.

## Generation guarantees

- No fixture was accepted unless it compiled and ran (native) or failed exactly as intended (repair/package). Generators report `N verified, 0 failed`.
- Expected outputs are observed from the toolchain, eliminating drift between the dataset and the grader.
- Every row carries `provenance` (source, license, zero_version, content_hash) and an `_fixture` oracle that is stripped before the model sees the task.

## Not done in this pilot (honest scope)

- TerminalBench → Harbor and Harbor → CIR converters (`tools/converters/`): deferred; external repos not fetched.
- Any container/Docker task execution.
- Prime hosted baseline eval on `poolside/Laguna-XS.2` (requires Prime account + GPUs). Configs are provided and the local scoring path is fully verified.
