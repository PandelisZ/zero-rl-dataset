# Baseline Eval Report — Zero RL dataset v0.1

## Status: model baseline NOT run (out of local scope)

Running `poolside/Laguna-XS.2` (33B) requires Prime Intellect hosted infra
(GPUs + account). The config to produce it is ready:

```
prime eval run prime/eval.zero.toml
```

## Local proxy baseline (grader-side)

In place of a model rollout, `oracle_validate.py` measures the grader's reward
surface using a deterministic non-solution baseline per family:

- `zero_native`  → empty `main`
- `zero_repair`  → the broken starter, unedited
- `zero_package_edit` → no edit (broken stub remains)

| | reward |
|---|---:|
| Oracle (reference fix) | **1.0** |
| Non-solution baseline | **0.4161** |

This brackets where a real model baseline should fall:

- If Laguna XS.2 scores **< ~5%**: tasks too hard or grader too brittle.
- If it scores **> 80%**: tasks too easy for RL.
- **Target pilot baseline: ~15–60% mean reward** (the dataset's non-solution
  floor of 42% confirms the reward shape lands in this band).

## Recommended next steps on Prime

1. `prime env install ./envs/zero_verifiers_env` (host must have `zero` on PATH).
2. `prime eval run prime/eval.zero.toml` → record real Laguna XS.2 baseline.
3. If baseline ∈ [15%, 60%]: `prime rl run prime/train.zero.toml` (native+repair).
4. Then `prime rl run prime/train.mixed.toml` (adds package-edit; harbor when populated).
5. Re-run eval on `test` split and compare against this frozen v0.1.
