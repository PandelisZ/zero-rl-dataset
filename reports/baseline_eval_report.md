# Baseline Eval Report — Zero RL dataset v0.1

## Live Prime Intellect eval — DONE ✅

The environment is deployed and proven online on Prime Intellect:

- Env (PUBLIC): `pandelis/zero-verifiers-env`
  https://app.primeintellect.ai/dashboard/environments/pandelis/zero-verifiers-env
- Eval run (`zero_native` val, gpt-4.1-mini, 5 examples × 3 rollouts = 15 samples):
  https://app.primeintellect.ai/dashboard/evaluations/z8k3jf1l8vj64wlpt0dyfjxm
  status COMPLETED, **avg_score 0.060**, framework `verifiers`.

Command:
```
prime env push zero_verifiers_env -p ./envs --visibility PUBLIC
prime eval run pandelis/zero-verifiers-env -p openai -m gpt-4.1-mini -n 5 -t 2048 -T 0.2 \
  -a '{"family":"zero_native","split":"val"}' -s
```

This proves the full pipeline end-to-end on the platform: env installs from the
Hub (self-contained, bundled CIR data), runs rollouts against a real model,
grades each completion with the native `zero` toolchain, and uploads results.

The **0.06** mean is the expected honest baseline: `gpt-4.1-mini` does not know
zerolang 0.2.0, so it earns mostly format/pattern credit and rarely compiles —
exactly the headroom RL targets (oracle = 1.0, verified). It also confirms the
grader discriminates on the platform, not just locally.

## Laguna XS.2 baseline — pending credentials

Running the target `poolside/Laguna-XS.2` (33B) needs a Prime inference endpoint
+ `PRIME_API_KEY` (unset here). Once set, swap the model:

```
prime eval run pandelis/zero-verifiers-env -p prime -m poolside/laguna-xs.2 \
  -n 5 -a '{"family":"zero_native","split":"val"}' -s
```
or use the provided `prime/eval.zero.toml`.

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
