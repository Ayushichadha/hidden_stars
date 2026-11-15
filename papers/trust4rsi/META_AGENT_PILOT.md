# Meta search-manager integration — November 16, 2026

Implemented in `scripts/meta_search_agent.py`. This is an integration pilot,
not a trained controller or a completed paper evaluation. It preserves the
manager/worker interface: a manager selects a search subgoal, the worker acts
under that subgoal for a fixed window, and a verifier checks the construction.
It does not reproduce HRM hidden-state goals or FeUdal training.

## Interface and controls

- Muse Spark 1.3, Standard mode; minimal reasoning effort; JSON action output.
- Action menu: local (center perturbation std 0.015) or broad (std 0.12).
- Observation: current score, budget remaining, and preceding window outcomes.
  No counterfactual outcomes, future measurements, or historical baseline results
  are included. A short action justification is logged, not used as evidence.
- Initialization consumes 30 objective evaluations; three action windows consume
  60 each. All compared policies receive exactly 210 evaluations.
- The numerical worker, feasible incumbent retention, and random streams are
  shared. The model cannot write or execute code. A fixed action is maintained
  throughout each window, potentially spanning multiple optimizer calls.
- Meta inference latency and token costs are additional costs, not included in
  the optimizer evaluation allowance. This is not equal total system compute.

Credentials load from MODEL_API_KEY or ignored `.env.research.local`. TLS uses
certifi with certificate verification enabled. No credential values are logged.
`outputs/meta-api-ledger.jsonl` is a shared locked ledger: reserve $0.05 before
each request, deny reservations that would exceed the authorized $10 Meta cap,
settle valid returned usage, and keep reservations for ambiguous failures.
No automatic retries. The cap covers requests through this runner only; retain
the ledger across runs. It is not an account-wide provider spending limit.

Requests are capped at 8,000 serialized bytes and 1,024 generated tokens, including
reasoning tokens. Cost estimates use uncached input $1.25/M and output $4.25/M,
verified against [Meta pricing](https://dev.meta.ai/docs/pricing-rate-limits).
Ignoring cache discounts is conservative. Pricing must be rechecked before
future scaling. The provider billing dashboard remains the authoritative charge.

## Completed pilot

Two fresh starts of the 26-circle problem, seeds 2026111800–2026111801.
Six successful Meta requests used 1,167 input tokens and 1,176 output tokens.
Estimated total API cost: **$0.00645675**. Modal spend: **$0**.

| Policy | Seed 2026111800 | Seed 2026111801 |
|---|---:|---:|
| Always local | 2.618677 | 2.594340 |
| Local / broad / local | 2.615410 | 2.611056 |
| Stagnation-triggered | 2.618677 | 2.588138 |
| Meta manager | 2.618289 | 2.622618 |
| Broad / local / local replay | 2.618289 | 2.622618 |

Meta selected broad / local / local in both episodes. A post-hoc fixed replay
reproduced both scores exactly, with no API calls. This replay was added after
observing the model's actions and is a diagnostic, not a predeclared competitor.
Meta lost slightly to local search on one start and improved the other. Two
episodes and an invariant action sequence do not demonstrate state-aware control
or superiority over fixed schedules. The successful result is operational:
authenticated model decisions, bounded spending, executed search, verified
geometry, reproducible traces, and baseline comparisons work end to end.

## Reproduction and next use

```bash
OPENBLAS_NUM_THREADS=1 .venv/bin/python -m scripts.meta_search_agent --output outputs/meta-agent-reproduction
OPENBLAS_NUM_THREADS=1 .venv/bin/python -m pytest tests/test_meta_search_agent.py tests/test_math_packing.py -q
```

The reproduction performs six paid requests and now includes the broad-first
baseline. Model actions need not be deterministic across reruns. Numerical
replay uses recorded actions and makes no API calls. Raw prompts, decisions,
usage, optimizer traces, and arrays remain in ignored outputs, not Git.

Next: use this adapter in the paired-checkpoint protocol described in
MATH_SEARCH_PILOT.md. Compare state-aware prompting with budget-only prompting
and the broad-first fixed schedule on fresh episodes. Freeze prompts before
evaluation. Do not infer that the LLM uses state merely because state is supplied.
