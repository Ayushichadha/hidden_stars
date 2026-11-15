# Mathematical search: feasibility and experimental contract

Status: November 15, 2026. Development exploration approved by the author.
Existing HRM and SQLite evidence remains part of the project. This pilot does
not implement an LLM research agent, learned controller, or FeUdal training.

## Task and provenance

Pack 26 nonoverlapping circles inside a unit square, maximizing total radius.
This is problem 36 in the official
[AlphaEvolve problem collection](https://github.com/google-deepmind/alphaevolve_repository_of_problems),
pinned at `8f447457957deac61e28bf1676746f0753b3b2f8`.
The notebook is `experiments/packing_circles_max_sum_of_radii/packing_circles_max_sum_of_radii.ipynb`.
The collection supplies problems and constructions, not the AlphaEvolve framework.
Its problem page mentions subsequent improvements: these constructions must not
be described as verified current world records.

The independent checker reads literal arrays using AST without executing notebook
code. Published 26-circle sum: 2.6359830849176076, minimum numerical margin 0.
Published 32-circle sum: 2.9395727712063233, minimum margin -1.39e-17.
Reducing every radius by 1e-12 yields positive numerical margins in both cases.
These are floating-point checks, not certified interval-arithmetic proofs.

## Completed pilot

Eight random starts, seed base 2026111500; 26 circles; SciPy SLSQP with analytic
constraint derivatives. Optimize for up to 50 iterations, then compare:

- Persist: start a fresh SLSQP invocation at the checkpoint coordinates.
- Revise: add Gaussian center perturbations with standard deviation 0.04,
  repair feasibility, then run SLSQP.

Both branches retain the identical checkpoint incumbent. Both receive a cap of
50 additional iterations. Actual evaluations and seconds are recorded; this is
not an equal-compute comparison. SLSQP optimizer internal state is not preserved.
Feasibility repair scales radii down conservatively; reported objectives use
repaired geometry and raw scores remain in the logs.

All eight initial runs converged in 10–19 iterations. Persistence then took two
iterations; revision took 8–21. Revision improved retained score in 5/8 cases
using a 1e-7 difference threshold; 3/8 were ties. No meaningful persistence wins.
The best candidate among checkpoint and branch endpoints scored 2.6125567316,
below the published 26-circle construction. There is no record improvement.

Interpretation: the runner, geometric checks, and branch intervention work.
The sampled decision is largely explained by optimizer convergence. This does
not establish a need for learned control, nor generalization across problems.
Eight starts on one problem are not eight independent benchmark problems.

## Next substantive experiment

1. Make a search episode a sequence of bounded local-search experiments. A
   persistent subgoal specifies a search family (e.g. local basin refinement);
   revision selects a different family or structural perturbation. Persist must
   perform useful additional exploration even after one local optimizer ends.
2. Collect branch outcomes at early and late checkpoints. Retain all valid
   incumbents. Record time, function evaluations, model tokens/cost if used, and
   objective improvement. Measure improvement per remaining search budget.
3. Compare always-persist, fixed revision, convergence/stagnation-triggered
   revision, random restarts, and a standard basin-hopping baseline before
   training a supervisor. Keep worker, archive, action menu, and budget shared.
4. Separate development and evaluation instances before selecting features or
   tuning. Seeds measure stochastic variability; transfer requires additional
   circle counts or mathematical problem families, explicitly reported as such.
5. Add a learned state-aware and time-only supervisor only if branch outcomes
   expose nontrivial opportunities beyond the reactive baseline. Use uncertainty
   across independent search episodes; do not present one best trajectory alone.

Meta can later propose search families or code changes; Modal can run isolated
experiments; past.dev can store searchable experiment history. Give every policy
the same memory access. None is necessary for this CPU feasibility step, and no
paid resource has been used by this pilot. This protocol does not authorize an
unbounded paid sweep. An agent-written optimizer requires independent checking
and sandboxed execution before accepting candidates.

## Reproduction

```bash
git clone https://github.com/google-deepmind/alphaevolve_repository_of_problems /tmp/saint-math-problems
git -C /tmp/saint-math-problems checkout 8f447457957deac61e28bf1676746f0753b3b2f8
.venv/bin/python -m scripts.check_math_packing /tmp/saint-math-problems/experiments/packing_circles_max_sum_of_radii/packing_circles_max_sum_of_radii.ipynb
OPENBLAS_NUM_THREADS=1 .venv/bin/python -m scripts.pilot_math_revision --seeds 8 --iterations 50 --output outputs/math-packing-reproduction
.venv/bin/python -m pytest tests/test_math_packing.py -q
```

Detailed candidate arrays and logs stay under ignored `outputs/`. The script
records package versions and refuses to overwrite a completed results directory.

## Sustained-search comparison

`scripts/run_math_search.py` implements six development baselines with a shared
worker and incumbent archive: always-local Gaussian perturbation (std 0.015),
always-broad perturbation (std 0.12), alternating local/broad, broad every fourth
call, broad after two consecutive failures to improve by 1e-7, and independent
uniform random restarts. The stagnation counter resets on improvement; after
two failures it stays broad until an improvement. These are simple search
baselines, not a full basin-hopping implementation or an LLM agent.

Every episode gets one initialization and twelve search calls, each with a
40-iteration cap. Each call performs fresh exploration, including persistence.
An episode retains its best numerically feasible candidate. Counter-based seeds
align random noise across policies; execution order rotates across seeds.
Actual solver evaluations and seconds remain separate from the equal call budget.
Perturbation magnitudes and rules were fixed before this development run.

```bash
OPENBLAS_NUM_THREADS=1 .venv/bin/python -m scripts.run_math_search --output outputs/math-sustained-reproduction
```

This run uses twelve new starts of the same 26-circle problem. Paired bootstrap
intervals describe variability over starts and are not evidence of generalization
to new mathematical problems. This is development data, not a held-out evaluation.

Completed: 72 episodes, 936 numerically feasible solver outputs. All 72 saved
incumbents passed a separate reload and geometry check; archived scores were
monotonic within every episode. Four focused tests pass, including analytic
derivatives and incumbent preservation.

| Policy | Mean radius sum | Mean objective evaluations | Mean solver seconds |
|---|---:|---:|---:|
| Local | 2.603211 | 157.4 | 0.580 |
| Broad | 2.600627 | 696.4 | 1.672 |
| Alternating | 2.607108 | 419.7 | 1.139 |
| Broad every fourth call | 2.605683 | 320.7 | 0.892 |
| Stagnation-triggered | 2.608477 | 374.3 | 1.137 |
| Random restarts | 2.606549 | 462.3 | 1.357 |

Stagnation-triggered search has the highest observed mean, but its paired
difference from local search is 0.005266 with a descriptive bootstrap interval
[-0.003330, 0.014044]. Every alternative's interval versus local includes zero.
Broad search uses about 4.4 times as many objective evaluations as local search.
Equal experiment counts therefore do not establish equal computational cost.
No learned-controller superiority is established. Next priority is enforcing a
common computation allowance and testing whether state-informed action choice
beats these simple baselines; adding an LLM before that would obscure the cause
of any improvement.

## Resource authorization

On November 15 the author approved a pilot cap of **US$10 Meta plus US$10 Modal**.
These are separate caps, not authorization to spend the full account balances.
No paid calls have been made for these math experiments. At the setup check,
the current process had no META_API_KEY or Modal token pair configured, and the
project environment did not have the Modal SDK installed. Credential values are
never logged or committed. The previously exposed chat key must not be reused.

## November 16: hard evaluation-budget comparison

The runner now accepts `--evaluation-budget`. Every call to the SLSQP objective
is counted, including initialization and line-search evaluations. An attempted
call beyond the allowance interrupts the optimizer before evaluating its input.
Episodes continue starting experiments until the shared allowance is exhausted;
`--calls` is ignored in this mode. Each individual experiment still has the
same 40-iteration cap. Six tests cover derivatives, geometry, incumbent
preservation, exact budget accounting, and deterministic replay.

The budgeted worker keeps the best feasible repair of every evaluated candidate,
including intermediate candidates, for every policy. This improves safe recovery
when optimization is interrupted. It changes the worker relative to the earlier
endpoint-only pilot, so comparisons must be made between policies within this
new experiment, not interpreted as a pure budget ablation against November 15.

Objective evaluations are a work proxy: objective computation itself is cheap,
and SLSQP also computes constraints, Jacobians, and quadratic-programming steps.
Constraint/Jacobian counts and elapsed solver time are logged separately. Equal
evaluation counts must not be described as identical FLOPs, wall time, or cost.
Concurrent local runs also make these timings unsuitable as clean latency
benchmarks. No LLM inference is part of this comparison.

Two development runs were specified before reading their results, each with
twelve fresh starts, all six policies unchanged, and 300 evaluations per episode:

```bash
OPENBLAS_NUM_THREADS=1 .venv/bin/python -m scripts.run_math_search --evaluation-budget 300 --seed-base 2026111600 --output outputs/math-budget300-reproduction
OPENBLAS_NUM_THREADS=1 .venv/bin/python -m scripts.run_math_search --circles 32 --evaluation-budget 300 --seed-base 2026111700 --output outputs/math-budget300-n32-reproduction
```

The second size checks sensitivity within circle packing; it is not a second
domain or a held-out learned-controller evaluation. Report results by size and
do not pool raw scores across sizes.

The 26-circle comparison completed with exactly 21,600 objective evaluations
across 72 episodes. All 1,132 returned solver candidates and all 72 saved final
incumbents passed numerical checks. Best observed score was 2.6297595642.
Local search had the highest mean (2.606685); stagnation-triggered search scored
2.602083, difference -0.004602 with descriptive paired 95% interval
[-0.009356, 0.001580]. The data do not support a stagnation-policy advantage.
These exploratory intervals are not corrected for multiple policy comparisons.

The 32-circle run also completed all 72 episodes with exactly 300 evaluations
each. All saved incumbents passed the same reload checks. Combined objective
evaluation count across both sizes is 43,200. Mean final scores:

| Policy | 26 circles | 32 circles |
|---|---:|---:|
| Local | 2.606685 | 2.918412 |
| Broad | 2.597696 | 2.897789 |
| Alternating | 2.600817 | 2.908392 |
| Broad every fourth call | 2.604390 | 2.915087 |
| Stagnation-triggered | 2.602083 | 2.908580 |
| Random restarts | 2.597176 | 2.901145 |

Local search has the highest mean at both sizes. At 32 circles the stagnation
policy difference versus local is -0.009832, descriptive interval
[-0.017633, -0.002228]. This argues against treating stagnation as sufficient
reason to broaden search in this setting. It does not prove that every possible
revision policy is inferior. Local search also has the largest mean measured
solver runtime in each run (1.322 and 3.082 seconds), reinforcing that this
comparison matches evaluations, not wall time. No learned policy was evaluated.

### Next decision experiment

Keep the local-search baseline. Collect paired local/broad continuations from
the identical archived state, at multiple consumed-budget checkpoints, with
equal remaining evaluation allowances and shared initial incumbents. An action
should occupy a bounded search window; use the same continuation policy after
that window so labels measure the downstream value of this decision. A single
unbounded local optimizer call is not a sufficient unit for the comparison.

Use only pre-decision observations: budget remaining, incumbent score, recent
improvements, unsuccessful calls, and geometric properties. Split by entire
search episode before feature fitting or tuning; never distribute checkpoints
from one trajectory across train and evaluation splits. Separate state-aware,
clock/budget-only, and reactive policies. Train only after measuring whether
there is meaningful branch disagreement; do not tune a search space until a
desired positive result appears. This experiment is planned, not completed.
