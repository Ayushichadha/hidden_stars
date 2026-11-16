# Paired search decisions — November 16

Completed development experiment: twelve fresh 26-circle starts, three checkpoints
per start. Checkpoints follow local search. Each action receives 60 objective
evaluations followed by the same 60-evaluation local continuation. Shared random
streams and initial incumbents isolate the initial local/broad intervention.
Initialization consumes 30 evaluations. Checkpoints occur after 30, 90, and 150.

| Checkpoint | Broad wins | Local wins | Ties | Mean broad minus local |
|---|---:|---:|---:|---:|
| 30 | 5 | 5 | 2 | 0.002847 |
| 90 | 5 | 1 | 6 | 0.001389 |
| 150 | 2 | 2 | 8 | 0.002407 |

Ties use absolute difference <=1e-7. There are 36 pairs but only twelve independent
initial trajectories. These are development outcomes, not held-out policy results.
Both actions sometimes win: there is an action-selection opportunity. This does
not establish that pre-decision features predict the winner. The checkpoint means
also motivate a budget-only comparator. No API calls were made.

Reproduce from repository root with:
`python -m scripts.collect_math_pairs`
The output directory must not already exist. Detailed paired scores and checkpoint
arrays stay under ignored outputs/math-paired-20261116.

Next: fit state-aware and budget-only decision predictors on separate complete
trajectories, then evaluate frozen choices on fresh trajectories. Include a fixed
broad-first strategy and local search; group uncertainty by trajectory.
