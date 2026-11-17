# Revision Quality and Adaptive Timing in Verified Mathematical Search

Ayushi Chadha

Working manuscript, November 17, 2026. Completed numerical studies and limitations
are reported below. Submission formatting, public artifact packaging, and final
reference editing remain pending. No mathematical record improvement is claimed.

## Abstract

A controller can change its decisions with state without improving terminal
performance. We investigate two possible limitations of adaptive revision:
insufficient observations and ineffective revision actions. In 26-circle packing,
a frozen numerical worker maintains a search recipe and replaces it exactly once
under a matched objective-evaluation budget. An initial prediction pilot finds no
advantage for progress-conditioned timing over a clock. A predeclared follow-up
uses 24 training, 12 validation, and 48 fresh confirmation seeds to separate richer
geometric observations from a moderate replacement recipe. Geometry improves
mean score over progress-only control by 0.000281, but the multiplicity-adjusted
97.5% paired interval includes zero. In contrast, a moderate replacement with its
validation-selected fixed schedule improves over the broad recipe's selected
fixed schedule by 0.006012, with interval [0.003712, 0.008490]. The latter is an
improvement in a revision-policy configuration, not evidence for learned adaptive
timing. Geometry-conditioned policies do not establish superiority over simpler
controls. A fresh doubled-budget replication also supports the fixed-configuration gain
(+0.007796; 97.5% interval [0.005102, 0.010785]). These results motivate separating the quality of available revisions
from the value of deciding when to invoke them. Conclusions are limited to one
problem, worker, replacement family, and small-sample policy-selection procedure.

## 1. Research question and scope

The scientific question is whether observations of a running search process help
a controller decide when to replace a persistent strategy, beyond time-based
schedules and reactive rules. This extends the adaptive-controller question of
our earlier hierarchical-reasoning work [12,13]. That work provides the conceptual
commitment/revision interface; the present worker is a numerical optimizer, not
an HRM model or a transfer of feudal latent goals.

The hypothesis is conditional: useful state-dependent control requires both
informative observations and useful alternative actions. A poor replacement can
make waiting a sensible policy; a good replacement can make an early fixed
switch sufficient. Neither pattern requires a learned adaptive controller.
Consequently, prediction error, action variability, and final decision value are
reported separately.

Our contributions are a frozen, verifiable commitment interface; matched timing
and observation comparisons with disjoint trajectory splits; and a predeclared
positive result for a moderate revision configuration alongside a negative result
for richer observation features. We do not claim a new metareasoning principle,
a superior general controller, a record-breaking packing, or an autonomous
code-discovery system. The existing bounded parameter-autoresearch runner is
execution infrastructure, not the learned controller evaluated here.

## 2. Task, worker, and intervention contract

We use AlphaEvolve problem 36: maximize the sum of radii of 26 non-overlapping
circles contained in the unit square [8]. The source is pinned to commit
`8f447457957deac61e28bf1676746f0753b3b2f8`. The archived reference score
2.6359830849176076 is a reference construction, not an independently verified
current world record. Equal-radius packing tables concern a different objective.
Rounded table entries and tolerance-relaxed constructions cannot be used as
interchangeable record comparators [9–11].

The worker is SciPy SLSQP with analytic constraints and derivatives. Each episode
starts from a seeded repaired random arrangement and consumes eight windows of
80 objective evaluations: exactly 640 per policy. Each SLSQP call permits at most
40 iterations; a new call consumes any remaining window allowance if optimization
terminates early. Every call starts afresh, so there is no hidden optimizer history
across window boundaries. A conservative radius repair is checked by a separate
floating-point geometry verifier. The best verified incumbent is always retained.
The optimizer's loss is not accepted as proof of feasibility. Floating-point
checking does not constitute an exact rational certificate.

For the single-replacement studies, the initial commitment uses position perturbations with standard deviation 0.015.
KEEP retains the recipe. REVISE replaces it with a new perturbation scale that
persists thereafter. Each matched policy must replace the commitment once before
one of windows 1 through 7 (zero-based); no change is allowed before consuming
window 0 or after the terminal window. All matched policies have two emissions.
Never-revise is reported separately because it has only the initial emission.

A common never-revise rollout provides cloned incumbent, score, commitment,
window and evaluation-counter checkpoints. Random draws are keyed by seed,
window and within-window call index. Corresponding calls therefore share
standardized noise without outcome-dependent random-stream selection. Different
recipes can cause different solver paths and call counts; identical noise keys
do not imply identical solver trajectories.

A complete single-recipe timing landscape has seven replacement schedules plus
never-revise. Shared-prefix collection executes 2,880 objective evaluations per
seed. The two-recipe follow-up has fourteen schedules plus one shared baseline
and executes 5,120 evaluations per seed. Shared work is included in each policy's
logical 640-evaluation budget; it is not free policy compute. Counts of objective
calls are a reproducible work proxy, not equality of constraints, derivatives,
FLOPs, or wall time. Geometry extraction, repair, controller overhead and branch
collection must be distinguished from this proxy.

## 3. Single-replacement prediction and causal policy evaluation

At boundary t, the terminal regression target is the score from revising now
minus the mean terminal score of all strictly later replacement times with the
same recipe. This is advantage over a uniform delayed-revision comparator, not
an optimal-stopping value function. Ridge regression predicts that target.
Policies revise at the first threshold crossing; otherwise they must revise
before window 7. A separate local-target control in the initial pilot predicts
immediate-window rather than terminal advantage.

The time-only model uses time indicators. The progress model adds current
incumbent score, latest and previous gains, trailing stagnation length, and
interactions with time. The geometry model additionally includes:

- radius coefficient of variation and minimum-to-mean radius;
- circle-pair near-contact fraction and contact-degree standard deviation;
- fraction of circles in near contact with a wall;
- maximum clearance on a fixed 9x9 interior grid and occupied area.

Contact gaps use a predeclared 1e-4 threshold. Geometry is permutation invariant
and computed only from the current verified incumbent after a consumed window.
Features cannot read future windows or branch outcomes. Standardization uses
training data only. The corresponding feature dimensions are 7, 39, and 95.

All model families use ridge penalties {0.1, 1, 10, 100}, thresholds
{0, 0.0005, 0.001}, and validation mean terminal score for selection. Fixed clocks
are selected from all seven timings; reactive rules use validation-selected
stagnation patience {1, 2, 3} with improvement tolerance 1e-7. Ties use the first
predeclared candidate. Policies are not refit after selection.

Confirmation uses causal replay of complete deterministic branches. The policy
examines consumed never-revise prefixes until its first replacement, then takes
that schedule's full terminal outcome. Because the worker and random streams are
fixed and no subsequent replacement is permitted, this selects the trajectory
the policy would execute. It is not a live-controller latency test. Outcomes
are evaluation targets, never inputs to the stopping decision. Seeds—not branch
rows—are the independent units for paired bootstrap intervals.

## 4. Initial audits and hypothesis formation

A twelve-seed development audit with broad replacement scale 0.12 found a
retrospective per-seed timing-oracle advantage of 0.002429 over its best mean fixed
timing. This optimistic ceiling established observed timing heterogeneity, not
state predictability. These seeds were subsequently training-only.

A first prediction pilot used 24 training, 12 validation, and 24 untouched
confirmation seeds. Progress-conditioned and time-only terminal policies both
revised before window 7 on all 24 confirmation seeds and scored 2.616691995 on
average. Their paired difference was zero. Prediction MSE was slightly lower
for progress conditioning, but sign accuracy was below the always-nonpositive
baseline. Neither its comparison with reactive control nor with a local-target
policy established an advantage. This pilot motivated the follow-up; its
confirmation seeds were never reused for selection or confirmation there.

The follow-up predeclared two hypotheses:

**H1: observations.** Adding geometry improves terminal policy value over progress
features with the original broad revision held fixed.

**H2: revision configuration.** A moderate recipe, with its validation-selected
fixed schedule, improves over the broad recipe's selected fixed schedule. The
moderate scale is the geometric midpoint sqrt(0.015 * 0.12) = 0.0424264, fixed
before collection rather than chosen from a sweep. H2 compares complete fixed
configurations and does not isolate strength at an identical switch time.
It also does not establish that an adaptive controller adds value.

All 84 follow-up seeds are fresh: 24 training, 12 validation, and 48 confirmation.
The larger confirmation sample improves precision but is not a formal power
guarantee. Policies and baselines freeze before confirmation collection. For
each primary contrast, success requires mean gain at least 0.0005 and a positive
lower endpoint of a paired 97.5% bootstrap interval (20,000 resamples). The
interval level uses a Bonferroni adjustment for two primary hypotheses. Secondary
comparisons are exploratory. The source-hashed protocol was committed as
`876717a` before collection; no outcome-dependent changes were made.

## 5. Confirmation results

All 84 seed collections completed and passed local geometry and trace-accounting
revalidation: 1,260 distinct schedule trajectories, including 720 in confirmation.
The duplicate serialized never-revise row across recipe families is counted once.

| Predeclared primary contrast | Mean paired gain | Adjusted 97.5% interval | Gate |
|---|---:|---|---|
| H1: geometry-broad minus progress-broad | 0.000281255 | [-0.000208784, 0.001007672] | Failed |
| H2: fixed-moderate minus fixed-broad | 0.006011583 | [0.003712203, 0.008490446] | Passed |

H1 had three wins, two losses and 43 ties in terminal score. Different timing
choices often retained the same incumbent. H2 had 36 wins, seven losses and five
ties. The fixed moderate policy switches before window 4; the fixed broad policy
switches before window 5. Both choices were selected on validation data.
The positive result therefore concerns the selection procedure's two fixed
configurations, not a learned adaptive decision or a pure same-clock effect.

| Frozen policy | Broad recipe mean | Moderate recipe mean |
|---|---:|---:|
| Time-only | 2.617156225 | 2.626121931 |
| Progress-conditioned | 2.616899924 | 2.626121931 |
| Geometry-conditioned | 2.617181179 | 2.625974326 |
| Validation-selected fixed | 2.618358471 | 2.624370054 |
| Validation-selected reactive | 2.617696655 | 2.625064616 |
| Retrospective timing oracle | 2.621320568 | 2.629660981 |

Never-revise scored 2.617123205. Oracle scores use confirmation outcomes and are
not deployable policies. The highest individual confirmation construction scored
2.634292399, below the archived reference; no new bound is claimed.

Geometry-moderate minus progress-moderate averaged -0.000147605, with interval
[-0.000833543, 0.000460980]. Geometry-moderate minus fixed-moderate averaged
0.001604272, with interval [-0.001012204, 0.004133562]. Geometry-broad minus
time-broad averaged 0.000024954, with interval [-0.000685179, 0.000841260]. These
secondary comparisons do not establish an adaptive geometry-policy advantage.

The moderate time-only and progress policies both switch at window 1 on every
confirmation seed. Their higher mean than the validation-selected fixed window 4
is therefore not evidence for adaptation: they are alternative clocks. This also
illustrates uncertainty in schedule selection from twelve validation seeds.

For broad revision, geometry MSE (3.36217e-5) is slightly lower than progress MSE
(3.45088e-5) but higher than time-only MSE (3.33145e-5). Geometry sign accuracy is
65.28%, compared with 80.90% for the always-nonpositive baseline. Prediction
improvements relative to one comparator do not establish useful decisions.

### Descriptive same-clock sensitivity check

After the primary analysis, we inspected every clock rather than selecting one
favorable timing. Moderate mean scores exceeded broad means at all seven clocks:

| Revision before window | Broad mean | Moderate mean |
|---|---:|---:|
| 1 | 2.614637223 | 2.626121931 |
| 2 | 2.616159093 | 2.625006927 |
| 3 | 2.616862318 | 2.624416474 |
| 4 | 2.617740322 | 2.624370054 |
| 5 | 2.618358471 | 2.623020515 |
| 6 | 2.617417265 | 2.621032510 |
| 7 | 2.617156225 | 2.620042382 |

This post-hoc descriptive check is consistent with a recipe-quality effect, but
is not a new predeclared confirmatory endpoint or proof of a particular disruption
mechanism. Confirmation data will not be reused to tune a new recipe or controller.

### Predeclared doubled-budget replication

A subsequent single-hypothesis replication doubled the objective budget from
640 to 1,280 evaluations (160 per window), preserving the two recipes and their
previously selected schedules: moderate before window 4, broad before window 5.
No schedules or models were reselected. Forty-eight fresh paired seeds
2026230000–2026230047 were allocated before execution. Success retained the
minimum mean gain of 0.0005 and a positive 97.5% paired bootstrap lower bound;
this interval is conservative for the single replication hypothesis.

Moderate averaged 2.627881209 versus broad 2.620085056. The mean paired gain was
0.007796153, with interval [0.005102243, 0.010784626]: 38 wins, two losses and
eight ties. The declared gate passed. All 96 saved constructions passed independent
geometry, score and exact-budget revalidation. The 124-test suite passed.

This supports the fixed-configuration advantage at a second budget. It does not
prove an interaction with budget or that the advantage increased: the budgets
used different seed cohorts, and no cross-budget interaction test was specified.
The schedules differ between recipes, so this remains a configuration comparison,
not a pure same-time strength intervention or learned adaptive-controller result.
The same problem and optimizer were retained; cross-problem robustness remains open.

The manifest was saved before calls in `outputs/budget-replication-v1/`; unlike
the preceding study, this compact runner was not committed before collection.
It refuses an existing output directory and leaves interrupted batch markers;
it has no automatic retry/resume mechanism. Collections ran on Modal CPU in batches
of four with 600-second per-seed limits. The small paired bootstrap was computed
locally from saved outcomes, not as a new optimization run. Workspace billing
subsequently displayed $0.18 total, credit-offset with $0 billed (rounded and
potentially delayed), versus the previous displayed $0.17. App:
`ap-it57xwYJQ7gSiRDKGI5c8H`. Script: `scripts/modal_budget_replication.py`.

### Frozen sequential-control follow-up (results pending)

The earlier experiments evaluate a single irreversible replacement. We now
specify a separate finite-horizon decision problem with repeated choices among
local perturbation (sigma=0.015), moderate perturbation
(sigma=sqrt(0.015*0.12)), and restart (uniform centers in [0.05,0.95], initial
radii 0.01). Each option receives exactly 80 objective evaluations, with eight
windows per rollout. Each returned candidate is independently checked; the
incumbent changes only on feasible improvement. Repeated switches are allowed,
counted, and do not carry an invented reward penalty. Computation and controller
wall time are reported separately from the matched objective budget.

We compare ridge and ExtraTrees critics, each with myopic and sequential credit.
For each window t and option a, finite-horizon fitted Q iteration [14] regresses
`1000*(score_next-score) + max_b Q_(t+1)(observation_next,b)`; the final-window
bootstrap is zero. Myopic critics omit the continuation term. Gamma=1 makes
accumulated unscaled improvement telescope to terminal minus initial score.
Critics receive 16 consumed-state features: remaining budget, score, two recent
gains, stagnation, option age, previous-option indicators, and seven geometry
features. They cannot read future states. These compressed features need not be
Markov; this is approximate finite-horizon control, not a convergence guarantee.

Ridge standardizes training features, uses an unpenalized intercept and alpha=10.
ExtraTrees uses 64 trees, maximum depth 5, minimum leaf size 8, random seed 731,
and a single CPU thread. Separate window/action heads avoid imposing a common
action slope. All settings are fixed; no hyperparameter sweep is conducted.
We export numerical model arrays to JSON and log observations, action values,
choices and independently verified constructions on every evaluation window.

Training uses 96 fresh seeds (2026240000–2026240095). At each visited state all
three actions branch from the same incumbent; a seeded uniform behavior policy
selects which branch continues. This yields 2,304 transitions from 96 paths,
with shared noise keys within a window. Coverage of all immediate actions does
not guarantee support for future learned-policy states. Sixteen separate seeds
(2026250000–2026250015) select a static comparator from always-local,
always-moderate and local-to-moderate/window-4. Four learned policies are fixed
from training; validation does not tune their hyperparameters. A two-stagnant-
window reactive rule is also retained. Forty-eight untouched paired seeds
(2026260000–2026260047) then execute full live rollouts, with 640 objective calls
per policy; old single-switch counterfactual replay is not used.

The two primary hypotheses are H1: tree-sequential exceeds ridge-sequential
(model capacity), and H2: tree-sequential exceeds tree-myopic (sequential credit).
Each requires mean score gain >=0.0005 and a positive lower endpoint of a 97.5%
paired seed bootstrap interval (20,000 resamples, Bonferroni adjustment for two
primary contrasts). Ridge-myopic and the gap to the validation-selected static
policy are descriptive controls. No automatic policy promotion follows a result.
Learning a superior controller would additionally require evidence against a
strong fixed comparator and replication; primary contrast support alone is
insufficient. Collection, fitting and substantive analysis run on Modal CPU.
The frozen protocol caps function execution at $1.725936 plus $0.50 overhead
reserve, within the user's cumulative $10 allowance. Numerical results are pending.

A pre-fitting portability amendment replaces bitwise equality of recomputed
observations/rewards/trace scores with absolute tolerance 1e-12 (zero relative
tolerance). macOS and Linux reconstruction of one initial score differed by
7e-16. Independent feasibility remains strict, and evaluation counts/actions
remain exact. Original training artifacts and their original manifest identity
are retained; no data are recollected, and no model, action, split, hypothesis
or selection rule changes. The amendment occurs before model fitting or any
validation/confirmation dispatch. It is a software portability correction,
not an outcome-driven protocol change.

## 6. Interpretation, limits, and next decision

The result supports a narrower claim than successful adaptive research: a
predeclared alternative revision configuration improves verified search under
matched objective-call budgets. Richer state features do not establish useful
adaptive timing in this setup. Increasing controller size is not supported by
these findings, nor is it justified to attribute gains from a better action to
a learned controller.

This study covers one circle count, one optimizer, a one-way persistent recipe
replacement, linear models, a uniform-delay credit target, and small training
and validation sets. Hypothesis support is conditional on this regime; negative
H1 evidence does not prove that geometry lacks predictive information. Quantifying
live controller/observation overhead, testing a distinct budget or problem regime,
and using exact certificates would be required for stronger claims. Secondary
intervals are exploratory, and bootstrap coverage is approximate at this size.

We stop this protocol after its declared comparisons. The moderate recipe is a
supported baseline for further work. Any next study should test its robustness
in a separately specified regime or identify a genuinely different decision
problem with useful alternatives. It should not enlarge the controller or tune
on these confirmation seeds merely to obtain a positive adaptive result.

## 7. Relation to prior work and the HRM project

Russell and Wefald [1] and Hay et al. [2] ground computational choices in terminal
decision utility. Honda et al. [3] show the importance of environment/planner
context and reactive replanning baselines; Xu et al. [4] train continuation
policies using trajectory outcomes. Our ridge stopping experiment is not a
reproduction of their reinforcement-learning methods and does not establish a
new theoretical metareasoning result.

HRM [5] and FeUdal Networks [6] motivate the earlier latent commitment interface.
Our first paper studies persistence; the second distinguishes state-dependent
scores, policies and useful revision [12,13]. The present mathematical worker
is an explicit extension of that question, not demonstrated transfer of HRM or
feudal alignment. Karpathy's autoresearch [7] motivates fixed evaluation,
bounded experiments and retained decisions. Our restricted parameter proposer
is infrastructure; these experiments do not implement autonomous source-code
invention or establish a record-beating research agent.

The saved HRM audits explain why a more inspectable worker was useful. In 64
original episodes, recorded loss preferred persistence at 347 of 384 states, but
neither action solved an example. A source-separated development audit of 80
problems likewise had no exact solves under either branch. In a 1,600-update,
four-example memorization control, all 396 scored predictions copied the input;
96.72% token accuracy matched the identity baseline and changed-token accuracy
was 0/13. Matched targets came from unique dataset rows within puzzle ID 9872.
This is a behavioral diagnosis of those artifacts, not a universal failure of
HRM or proof of an architectural bug. Mathematical results do not resolve missing
HRM competence, exact-count, or multiseed architectural evidence.

SQLite and earlier neural packing demonstrations remain supporting engineering
records. They are not pooled with the current study or used as independent
confirmation. The initial numerical neural study did not establish superiority
over always-local search.

## 8. Reproducibility and resource accounting

Core code: `scripts/matched_revision.py`, `scripts/predict_revision.py`, and
`scripts/revision_hypotheses.py`, with corresponding Modal runners. The worker
image pins NumPy 2.2.6 and SciPy 1.15.3 on Python 3.11. Manifests pin source hashes,
seed partitions and rules. Pending-call markers prevent silent paid retries;
changed source identities invalidate resumption. Output validation replays geometry,
intervention count, timing and budget checks. All 134 tests passed, including ten new checks of repeated switching, delayed
credit, model export equivalence, leakage, geometry, budgets and failed dispatch.
Three macOS BLAS warnings occurred inside the sklearn reference ridge calculation;
its finite outputs matched our exported model to 1e-12. Production ridge uses an
equivalent centered solve with einsum. Tests do not replace experimental evidence.

The first timing audit ran twelve development seeds; the prediction pilot ran
48 new collections plus two analyses. The follow-up ran 84 collections and two
analyses, up to four CPU collections concurrently, without retries or a payment
method. It used 2,763.05 aggregate collection CPU-seconds. A rate-based collection
estimate is $0.0485, excluding analysis/setup/idle. Workspace billing displayed
$0.10 before and $0.17 afterward, fully offset by credits and $0 billed. These
rounded totals can lag or reconcile; they are not exact per-run invoices. The
study stayed within the authorized $10 allowance.

Follow-up app: `ap-tRiwWPhOlw520FyvrXHGW6`.
Raw constructions, traces, models and execution receipt are retained locally in
`outputs/revision-hypotheses-v1/` and remain ignored by Git. Public raw-artifact
packaging is pending; hashes alone do not replace access to those artifacts.

- Manifest SHA-256: `ff4be1a74bd00db5586d2efc3f3b0061f93b86e388da079fe9cec1fe9e7f5161`
- Frozen policies: `75fdd36b01b1e94f6bddf4c9fab6601708e211afe071dbdcf91db39adfac3a92`
- Confirmation summary: `ec1c45571132352a8657966c03aeeb17f194a28ae3a8d0a77d0b36fba5a5f42b`

Earlier run artifacts remain in `outputs/matched-revision-v1/` and
`outputs/revision-prediction-v2/`. The latter's protocol commit is `9a099c6`;
its confirmation summary hash is
`566b5ed98258c473cb0b98121a40c00f7ca63c2db0f7f86579c97f0cebcf3bde`.
Saved HRM evidence can be inspected with `scripts/audit_manuscript_evidence.py`
and `scripts/diagnose_hrm_copy_baseline.py`; these do not replicate training.

## 9. Conclusion

A controlled improvement occurred in the available revision configuration, while
learned adaptive timing remains unestablished. Moderate replacement improved a
validation-selected fixed policy on fresh seeds; geometry-conditioned timing
failed its predeclared improvement test. The scientific distinction is essential:
better actions, informative predictions and useful adaptive policies are separate
claims, each requiring its own controlled evidence.

## References

Primary sources checked November 16, 2026. Exa retrieved full text for Honda,
Xu, and Hay, and the publisher abstract for Russell and Wefald. Targeted methods
inspection informed the comparison below; none of these algorithms has been
reproduced in this study. Cached extraction does not establish a live leaderboard
snapshot. Audit requests and responses are retained locally under outputs/exa-audit/.

1. Russell, S., and Wefald, E. (1991). Principles of metareasoning.
   Artificial Intelligence 49(1–3), 361–395.
   https://doi.org/10.1016/0004-3702(91)90015-C
2. Hay, N., Russell, S., Tolpin, D., and Shimony, S. E. (2012).
   Selecting Computations: Theory and Applications. UAI 2012.
   https://arxiv.org/abs/1207.5879
3. Honda, K., Yonetani, R., Nishimura, M., and Kozuno, T. (2023; revised 2024).
   When to Replan? An Adaptive Replanning Strategy for Autonomous Navigation
   using Deep Reinforcement Learning. https://arxiv.org/abs/2304.12046
4. Xu, W., et al. (2026). Continue or Replan? Bernoulli-Continuation Policy
   Learning for Adaptive Horizon Execution. https://arxiv.org/abs/2608.03483
5. Hierarchical Reasoning Model (2025). https://arxiv.org/abs/2506.21734
6. FeUdal Networks for Hierarchical Reinforcement Learning (2017).
   https://arxiv.org/abs/1703.01161
7. Karpathy, A. (2026). autoresearch, README and program.md.
   https://github.com/karpathy/autoresearch
8. Georgiev, B., Gómez-Serrano, J., Tao, T., and Wagner, A. Z. (2025).
   Mathematical exploration and discovery at scale.
   https://arxiv.org/abs/2511.02864
   Problem 36: https://google-deepmind.github.io/alphaevolve_repository_of_problems/problems/36.html

9. OpenEvolve issue 156, original author report (2025).
   https://github.com/algorithmicsuperintelligence/openevolve/issues/156
10. Friedman, E. Circles in Squares: maximum sum of radii table.
    https://erich-friedman.github.io/packing/cirRsqu/
11. Göther Labs. Exact 26-circle unit-square packing, release v1.2.1.
    https://www.gotherlabs.com/results/circle-packing-26-unit-square/

12. Chadha, A. (2026). When to Re-Plan: Subgoal Persistence in Hierarchical
    Latent Reasoning. https://arxiv.org/abs/2606.03741
13. Chadha, A. (2026). A Score Is Not a Policy: Measuring the Value of Adaptive
    Revision. https://arxiv.org/abs/2609.00874

14. Ernst, D., Geurts, P., and Wehenkel, L. (2005). Tree-Based Batch Mode
    Reinforcement Learning. JMLR 6(18), 503–556.
    https://jmlr.org/papers/v6/ernst05a.html
