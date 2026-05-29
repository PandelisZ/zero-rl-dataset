# Conversion Report — Zero RL dataset v0.2

Generated against `zero 0.2.0`. Substrate: `zerolang-examples` (now 26 projects,
expanded from 10 by an agent team).

## Families produced

| Family | Tasks | How |
|---|---:|---|
| `zero_native` | 92 | Synthetic single-file templates (28 builders × params). Each fixture compiled + run through `zero`; **expected stdout captured from the real run** (never hand-written). |
| `zero_repair` | 92 | Each verified native fixture broken by one transform (drop `raises`, drop `check`, wrong return type, misspelled call). Each before-state **verified to fail `zero check`**; diagnostics recorded. |
| `zero_package_edit` | 47 | Tested functions across all 26 `zerolang-examples` projects (auto-discovered, up to 3/project) replaced with a type-correct but wrong stub → **compiles but fails `zero test`**. Oracle = original project. |
| `zero_graph_edit` | 180 | **The graph-native family.** Back-translation: dump a fixture's ProgramGraph, mutate one literal node's value; the model must recover the target via a CHECKED `zero graph patch` (graphHash + node id + `expect`), NOT by rewriting text. Each task's gold `--op` is applied at generation to a compiling target. Graded by a tool-trajectory rubric (graph_patch_success 0.50 / target_match 0.20 / check 0.15 / surface_used 0.15). |
| `harbor_env` | 0 | Deferred — needs Harbor/TerminalBench + container infra (see `envs/.../tasks/harbor/README.md`). |

**Total: 411 tasks** (v0.1 was 126). Splits (deterministic, balanced ~80/10/10): train 331, val 40, test 40.

Difficulty distribution: 1→35, 2→87, 3→284, 4→5.

> **Graph-edit is the primary target.** It rewards the compiler-mediated
> ProgramGraph edit surface (`zero graph dump` / `graph patch --op` ≈ Roder's
> `zerolang_edit`), not `.0` text output. The source-emit families (native /
> repair / package) remain as a baseline contrast. A gold trajectory scores 1.0
> on the rubric (verified offline).

## Generation guarantees

- No fixture was accepted unless it compiled and ran (native) or failed exactly as intended (repair/package). Generators report `N verified, 0 failed`.
- Expected outputs are observed from the toolchain, eliminating drift between the dataset and the grader.
- Every row carries `provenance` (source, license, zero_version, content_hash) and an `_fixture` oracle that is stripped before the model sees the task.

## Not done in this pilot (honest scope)

- TerminalBench → Harbor and Harbor → CIR converters (`tools/converters/`): deferred; external repos not fetched.
- Any container/Docker task execution.
- Prime hosted baseline eval on `poolside/Laguna-XS.2` (requires Prime account + GPUs). Configs are provided and the local scoring path is fully verified.
