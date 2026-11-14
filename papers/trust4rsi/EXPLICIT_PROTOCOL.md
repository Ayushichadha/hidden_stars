# Explicit commitment evaluation protocol

Recorded before the runs below. The primary comparison is state-aware versus
time-only switching on unseen workflows. Both learned policies use decision
times 2–10, zero or one switch, twelve total calls, the same branch outcomes,
and validation selection among ridge penalties 0.1, 1, 10. Their feature
dimensions differ. A switch consumes a call restoring the cursor.

Use seeds 2026111801, 2026111901, 2026112001 with 2,000 fitting, 500 validation,
and 3,000 evaluation workflows each. Partitions share a generator distribution
but have distinct identifiers. Freeze the current generator, features, and
training algorithm before inspecting these runs. This is a prospective
evaluation after earlier development experiments, not an external benchmark.

Report completion, paired differences and bootstrap intervals by workflow,
rescues/losses, regime-specific performance, verified trace count, and hindsight
best-switch success. The hindsight score is an opportunity bound, not a policy.
Compare fixed timing and validation-selected reactive failure streaks as well.
Policy computation beyond the matched tool-call budget requires separate
measurement. These experiments do not establish performance under new fault
distributions or general autonomous coding.

## Completed evaluation

Each run verified 15,000 online policy traces. Completion percentages were:

| Seed | Fixed | Learned time | Learned state | Reactive |
| --- | --- | --- | --- | --- |
| 2026111801 | 80.20 | 79.93 | 83.57 | 82.57 |
| 2026111901 | 80.90 | 80.77 | 82.67 | 82.87 |
| 2026112001 | 80.60 | 81.97 | 84.20 | 84.07 |

State-minus-time paired differences were +3.63 [2.33, 4.93], +1.90 [0.70, 3.17],
and +2.23 [1.07, 3.40] percentage points. These are per-run workflow bootstrap
intervals conditional on the fitted policies. They do not quantify uncertainty
over arbitrary training seeds or environmental distributions.

State-minus-reactive differences were +1.00 [0.20, 1.80], -0.20 [-1.13, 0.70],
and +0.13 [-0.83, 1.07] percentage points. Persistent-outage subgroup gaps versus
reactive were -2.46, -7.29, and -7.26 percentage points. Stable and transient
subgroups improved in each run. Report this tradeoff alongside the aggregate.

Hindsight best-switch completion was 95.93%, 95.73%, and 95.97%. This uses
future outcomes and includes luck in service availability. It is not evidence
that the observed histories permit an executable policy to attain these scores.
