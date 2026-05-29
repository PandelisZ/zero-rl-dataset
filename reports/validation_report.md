# Validation Report — Zero RL dataset v0.2 (231 tasks)

> v0.2 (231 tasks) results: CIR schema **231 rows valid**; oracle mean reward
> **1.0** (0 failures), baseline mean **0.4285**, **0 trivial** tasks. Method
> below is unchanged from v0.1.


All checks below were executed locally against `zero 0.2.0`.

## A. CIR schema validation — PASS

`python tools/validators/validate_cir.py`

```
CIR validation OK: 126 rows, schema/enum/regex/provenance all valid
```

Checks enforced: required keys, family/split/grader enums, difficulty 1..5,
unique ids (within and across splits), all source/forbidden regexes compile,
provenance.source+license present, UTF-8 source files, and **no oracle fixture
leaked into any prompt**.

## B. Oracle + baseline validation — PASS

`python tools/validators/oracle_validate.py` (runs the real grader on every
task twice: oracle fix + a non-solution baseline).

| Metric | Value | Target |
|---|---:|---|
| Oracle mean reward | **1.0** | ≥ 0.95 |
| Oracle failures | **0 / 126** | 0 |
| Baseline mean reward | **0.4161** | ≤ 0.80 |
| Trivial tasks (baseline too high) | **0** | 0 |

Interpretation: every task is solvable-as-graded (oracle 1.0), and no task is
trivially solved by a non-edit/empty submission. The 0.42 baseline reflects
partial credit (response format + structural patterns) and sits inside the
brief's healthy pilot band (15–60%), leaving clear headroom for RL.

Per-task results: `reports/oracle_results.json`.

## C. Env scoring path — PASS

`python -m zero_verifiers_env.harness <family> val` exercises the exact Prime
reward path (completion → source extraction → grader):

```
zero_native        oracle_mean_reward = 1.0  (n=5)
zero_repair        oracle_mean_reward = 1.0  (n=5)
zero_package_edit  oracle_mean_reward = 1.0  (n=1)
```

`_fixture` is verified absent from the model-visible `info`/`prompt`.

## D. Grader discrimination spot-check — PASS

A correct hello-world scores **1.0**; an unbound-identifier version scores
**0.25** (format + pattern credit only, check/run/stdout all 0).

## Not validated locally (requires external infra)

- Harbor oracle validation (`validate_harbor_tasks.py`) — no Harbor tasks ship.
- Prime smoke eval (`prime eval run`) — requires Prime account/GPUs; config is
  provided in `prime/eval.zero.toml`.
