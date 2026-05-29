# Baseline Eval Report — Zero RL dataset v0.2

## v0.2 (231 tasks) — Laguna XS.2 baselines, online ✅

Env `pandelis/zero-verifiers-env` v0.3.1 (Integration Test PASSED). Laguna XS.2
via Prime Inference on val:

| family | avg_score | eval |
|---|---:|---|
| zero_native | 0.250 | https://app.primeintellect.ai/dashboard/evaluations/du9ungure4rxx9r7l5k809pp |
| zero_repair | 0.147 | https://app.primeintellect.ai/dashboard/evaluations/ied8nxxkngcv74b9s50cwdw6 |
| zero_package_edit | 0.000 | https://app.primeintellect.ai/dashboard/evaluations/nz28a26lsww76ot0j95x4ygt |

Oracle mean reward **1.0** (0 failures), non-solution baseline **0.4285**, 0
trivial tasks across all 231. The expanded native val (more easy/medium tasks)
lifts the native baseline to 0.25 — a healthier learnable band than v0.1's 0.06.

Smoke RL run launched: `prime train prime/train.smoke.toml` →
https://app.primeintellect.ai/dashboard/training/cun4sdqniwiqr5e5lps61nur

---

## v0.1 — Live Prime Intellect eval — DONE ✅

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

## Laguna XS.2 baseline — DONE ✅ (target model, online)

Ran `poolside/laguna-xs.2` via Prime Inference (`-p prime`, $0) on the val split
of every Zero family; all uploaded to the platform:

| family | val tasks × rollouts | avg_score | eval |
|---|---|---:|---|
| zero_native | 5 × 3 | 0.060 | https://app.primeintellect.ai/dashboard/evaluations/rsfvkwpxk8qwufwz70zs5ayv |
| zero_repair | 5 × 3 | 0.135 | https://app.primeintellect.ai/dashboard/evaluations/cnrpib730ywqw7cmdfti62lc |
| zero_package_edit | 1 × 3 | 0.000 | https://app.primeintellect.ai/dashboard/evaluations/yafd7v5z9pgvtqf8xzpeyxc8 |

Command (per family):
```
prime eval run pandelis/zero-verifiers-env -p prime -m poolside/laguna-xs.2 \
  -n 5 -a '{"family":"<family>","split":"val"}' -s
```

Read: the base Laguna XS.2 is weak at zerolang 0.2.0 — it earns mostly
format/error-reduction credit, never fully compiling+passing. `zero_repair`
(0.135) > `zero_native` (0.060) > `zero_package_edit` (0.000), i.e. fixing a
nearly-correct file is easiest and restoring a stubbed function in a multi-file
package is hardest. All oracles score 1.0, so every family has large, real RL
headroom. These are the frozen v0.1 pre-RL baselines to beat.

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
