# Conversion Report — Zero RL dataset v0.1

Generated against `zero 0.2.0`. Substrate commit (zerolang-examples):
`cb9b454f3b4df21c2f8cd8ff09ee7fcb69007d4f`.

## Families produced

| Family | Tasks | How |
|---|---:|---|
| `zero_native` | 58 | Synthetic single-file templates (17 builders × params). Each fixture compiled + run through `zero`; **expected stdout captured from the real run** (never hand-written). |
| `zero_repair` | 58 | Each verified native fixture broken by one transform (drop `raises`, drop `check`, wrong return type, misspelled call). Each before-state **verified to fail `zero check`**; diagnostics recorded. |
| `zero_package_edit` | 10 | One tested function in each of the 10 `zerolang-examples` projects replaced with a type-correct but wrong stub → **compiles but fails `zero test`**. Oracle = original project. |
| `harbor_env` | 0 | Deferred — needs Harbor/TerminalBench + container infra (see `envs/.../tasks/harbor/README.md`). |

**Total: 126 tasks.** Splits (deterministic, balanced ~80/10/10): train 104, val 11, test 11.

Difficulty distribution: 1→23, 2→53, 3→45, 4→5.

## Generation guarantees

- No fixture was accepted unless it compiled and ran (native) or failed exactly as intended (repair/package). Generators report `N verified, 0 failed`.
- Expected outputs are observed from the toolchain, eliminating drift between the dataset and the grader.
- Every row carries `provenance` (source, license, zero_version, content_hash) and an `_fixture` oracle that is stripped before the model sees the task.

## Not done in this pilot (honest scope)

- TerminalBench → Harbor and Harbor → CIR converters (`tools/converters/`): deferred; external repos not fetched.
- Any container/Docker task execution.
- Prime hosted baseline eval on `poolside/Laguna-XS.2` (requires Prime account + GPUs). Configs are provided and the local scoring path is fully verified.
