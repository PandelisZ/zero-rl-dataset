# zero-rl-dataset

A dataset package for RL fine-tuning a code model (target: `poolside/Laguna-XS.2`
via **Prime Intellect** hosted training) to **edit and write [zerolang](https://github.com/vercel-labs/zerolang)
projects using the native `zero` toolchain**.

Every task ships with a **before state**, an **oracle after state**, and a
**deterministic grader** that scores submissions by actually running
`zero check` / `zero run` / `zero test` — no simulated compiler.

> **Scope honesty.** This is the *verified zero-native pilot*. Everything in the
> Zerolang path was generated and validated against `zero 0.2.0` on this machine.
> The Harbor / TerminalBench / Prime-hosted-eval pieces from the original brief
> are **scaffolded and documented but not executed here** (they need external
> repos, containers, and Prime GPUs). Such parts are clearly marked throughout.

## What's in the box (verified)

| | count | grader signal |
|---|---:|---|
| `zero_native` | 58 | source-only → `zero check` → `zero run` → exact stdout → source patterns |
| `zero_repair` | 58 | broken before-state → fix → `zero check`/`run`/stdout + compiler-error reduction |
| `zero_package_edit` | 10 | one of the 10 real projects with a stubbed function → make `zero test` pass |
| `harbor_env` | 0 | deferred (container substrate) — plumbing + docs only |
| **total** | **126** | splits: train 104 / val 11 / test 11 |

**Validation results (all local, `zero 0.2.0`):**
- CIR schema: 126 rows valid.
- **Oracle mean reward 1.0** (0 failures) — every reference solution provably solves its task.
- **Baseline mean reward 0.42** — non-solutions score low; 0 trivial tasks. (In the brief's healthy 15–60% pilot band.)

See `reports/` for the full conversion / validation / baseline reports.

## Quick start

```sh
scripts/setup.sh                                  # install the `zero` toolchain
export PATH="$HOME/.zero/bin:$PATH"
scripts/regenerate.sh                             # regenerate + assemble all tasks
scripts/validate.sh                               # schema + oracle + env-path checks
```

Grade a single submission against a task:

```sh
python tools/graders/zero_grader.py <task.json> <submission.json>
```

## Layout

```
zero-rl-dataset/
  datasets/
    cir/tasks.{train,val,test}.jsonl       # canonical intermediate representation (source of truth)
    zero_native/   cases.{split}.jsonl + cases.generated.ts (derived)
    zero_repair/   repair.{split}.jsonl
    zero_package_edit/ package.{split}.jsonl
    manifests/     dataset_manifest.json, source_manifest.json, hashes.json
  tools/
    schema/cir.schema.json
    generators/    gen_zero_{native,repair,package_edit}.py, assemble_cir.py, cir_to_zero_cases.py
    graders/       zero_grader.py, zero_runner.py, zero_reward.py
    validators/    validate_cir.py, oracle_validate.py, compute_hashes.py
    converters/    (deferred TerminalBench/Harbor converters — see README)
  envs/zero_verifiers_env/                 # Prime `verifiers` environment package (self-contained)
    zero_verifiers_env/{load_environment,taskset,harness,rewards}.py
    zero_verifiers_env/{zero_grader,zero_runner,zero_reward}.py   # vendored grader
    zero_verifiers_env/roder_zero.py       # Roder agent harness (CLIHarness)
    sandbox/{install.sh,Dockerfile,score.sh}  # zero + roder sandbox image
    tasks/{zero_native,zero_repair,zero_package_edit,harbor}/
  prime/           eval.zero.toml, train.zero.toml, train.mixed.toml, train.roder.toml
  reports/         conversion_report.md, validation_report.md, baseline_eval_report.md, oracle_results.json
```

## How it works

**CIR** (`datasets/cir/*.jsonl`) is the source of truth; per-family files and the
TypeScript cases are derived from it. Each row carries the prompt, optional
`starter_files` (the before-state), `expected` behaviour, a typed `grader`
spec, `provenance` (+ content hash), and a private `_fixture` (the oracle
after-state). **`_fixture` is stripped before the model ever sees a task.**

**Grader** (`tools/graders/zero_grader.py`) materializes a submission into a temp
workspace and shells out to `zero`. Reward shaping (v1) lives in `zero_reward.py`:

- native: `0.05 format + 0.25 check + 0.20 run + 0.25 stdout + 0.15 patterns + 0.05 forbidden + 0.05 style`
- repair: `0.10 source-only + 0.15 error-reduction + 0.30 check + 0.20 run + 0.20 stdout + 0.05 minimality`
- package: `0.05 format + 0.25 check + 0.50 tests-pass + 0.20 run`

Hard-zero on: no submission, timeout, or unextractable source.

**Prime env** (`envs/zero_verifiers_env`) exposes `load_environment(family, split, harness=...)`,
wrapping the grader in a `verifiers` rubric for the Zero families and delegating
`harbor_env` to Prime's `HarborTaskset`. The host must have `zero` on PATH. The
grader is **vendored** into the package so it installs standalone on the Hub.

## Sandbox + Roder harness

Two execution paths (`harness=`):

- **`deterministic`** (default) — single-turn, model emits Zero source, scored
  locally by `zero check/run/test`. No sandbox; fully verified offline.
- **`roder-zero`** — agentic: the [Roder](https://roder.sh) coding agent edits
  the zerolang project inside a Prime sandbox that has **both `zero` and `roder`**
  installed, scored by `sandbox/score.sh` → `/logs/verifier/reward.json`.

The sandbox is defined in `envs/zero_verifiers_env/sandbox/`:
`install.sh` (zerolang.ai + dl.roder.sh), `Dockerfile` (amd64 image
`zero-roder-sandbox`), and `score.sh` (Harbor reward contract). The harness
(`roder_zero.py`) is adapted from graphlanger's proven `harbor_terminal_bench`
roder-zero, extended to install `zero`. Roder's binary is linux/amd64 only, so
this path is validated on Prime, not on this host. Train with
`prime/train.roder.toml`.

## Reproducibility

`datasets/manifests/hashes.json` hashes every artifact; `source_manifest.json`
records the substrate (`zerolang-examples` @ `cb9b454`) and `zero 0.2.0`. Re-running
the generators on the same toolchain reproduces the dataset.

## Next steps on Prime (not run here)

See `reports/baseline_eval_report.md` — install the env, run the Laguna XS.2
baseline eval, then `prime/train.zero.toml` → `prime/train.mixed.toml`.
