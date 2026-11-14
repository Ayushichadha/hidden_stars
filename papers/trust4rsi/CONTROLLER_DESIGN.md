# Controller design for the SQLite experiment

## Three components

The worker observes tool responses and decides whether to switch services.
A manager produces a normalized 16-dimensional goal and a gate. The worker
uses its encoded observation plus the gated cached goal to predict the value
of switching services. The supervisor decides when to refresh that goal.

The worker and manager are trained together on training workflows, then frozen.
The supervisor is fitted afterward. This is the SQLite implementation of the
persistent-goal idea. HRM uses a recurrent reasoning worker with a different
state representation.

## State available before the decision

At call k, observation includes an intercept, latest response, success fraction
over the latest two calls, cumulative success fraction, remaining required
records divided by twelve, total required records divided by twelve, and k/12.
The supervisor also receives the distance between a newly proposed goal and
the cached goal. Each call position has its own fitted coefficient vector.
Final outcomes and future tool responses are excluded from inference inputs.

Computing the candidate goal is already required by the current state features.
Thus this implementation tests the effect of adopting a refreshed goal. Any
claim of saving manager computation requires separately measuring or changing
that candidate-goal computation.

## Actions and budget

Persist keeps the cached goal. Refresh replaces the goal and gate using current
observations. Each workflow has twelve tool calls, at most one service switch,
and at most one optional goal refresh at calls 3–10. A service switch consumes
the environment's restoration cost. Manager inference and supervisor overhead
are additional computation beyond the matched tool-call budget.

## Training target

For each training workflow, evaluate completion under every allowed fixed
refresh time and under persistence. Fit the supervisor backwards through time.
At call k its target is completion when refreshing now minus completion under
the already-fitted future revision policy. Fit ridge regression with penalty
10 and an unpenalized intercept. Refresh when predicted advantage is positive;
otherwise continue. The worker keeps making service decisions during this wait.

The time-only baseline follows the same backwards construction using a constant
predictor at each call. Its prediction is mean training advantage at that time.
This tests whether observations add value beyond a learned temporal schedule.
The state model has additional coefficients, so capacity is not identical.

## Evaluation and interpretation

Compare whole trajectories with persistence, validation-selected fixed refresh,
learned time-only refresh, and learned state-aware refresh. A reactive service
switch rule is a system-level reference with a different action interface.
Report endpoint rescues and losses, paired intervals, and refresh frequency.

The hindsight oracle chooses the best refresh time separately for each
evaluation workflow using its outcomes. It measures available opportunity and
is an upper bound over these interventions, not an executable supervisor.
Synthetic service faults and the small worker define the scope of the results.

## Reviewer connections

Russell and Wefald motivate final utility and computation cost. Hay et al.
motivate the value of computation for later decisions. Honda et al. motivate
fixed, reactive, and learned replanning comparisons. Xu et al. motivate
trajectory-outcome training while freezing the worker. Our ridge supervisor
is a proposed adaptation of these principles, not a reproduction of BCP.
See RESEARCH_DIRECTION.md for references and experiment status.

## Architecture assessment from the current evidence

The worker can respond directly to current observations while retaining an old
goal. Consequently persistence of a goal is compatible with changing tool
actions. The goal need not be the worker's sole source of adaptation. This
architecture tests goal refresh only insofar as the learned worker uses that
goal; a nonzero logit effect alone does not establish useful task structure.

A frozen-worker gate-removal intervention on seeds 2026111401–2026111403 scored
80.8%, 82.8%, and 84.0% versus 77.6%, 82.6%, and 84.2% with the initial goal
retained. It rescued/lost 37/21, 40/39, and 4/5 workflows, respectively.
Removing a trained input changes its distribution, so these numbers measure
sensitivity to the goal channel. A separately trained observation-only worker
is still required before claiming that goals help or hurt learning.

The next architectural comparison should train goal-conditioned and
observation-only workers on the same endpoint supervision, partitions, and
training budget. Evaluate competence and revision headroom separately. Keep
the existing goal-refresh action definition when evaluating the controller.

The matched observation-only training comparison is now implemented. Both
workers start with identical encoder and action-head weights and receive the
same sampled decision positions, targets, training workflows, and 600 updates.
The observation-only worker trains with zero goal injection and excludes manager
parameters from its optimizer. The goal model has extra manager capacity.

On the three existing development seeds, observation-only completion was 79.8%,
82.4%, and 84.0%. State-supervised goal refresh scored 80.2%, 83.2%, and 84.4%.
These small differences require paired uncertainty and independent replication.
The observation-only evaluation currently uses the collected branch outcome
matrix; it does not yet produce its own online-policy trace.

Online SQLite evaluation now checks the trained observation-only worker against
the collected branch outcome matrix. All three runs verified 2,500 traces each.
State-refresh minus observation-only completion differences were 0.4, 0.8, and
0.4 percentage points, with respective paired 95% intervals [-0.8, 1.6],
[-0.4, 2.0], and [-1.0, 1.8]. Each interval includes zero.

Run scripts/render_sqlite_trace.py after the sqlite-visual-2026111401 through
sqlite-visual-2026111403 runs to create local PNG/PDF figures and an MP4 replay.
It requires matplotlib, imageio, and imageio-ffmpeg. The replay explicitly selects
the first state-refresh rescue versus persistence in seed 1 and records its
selection and original events. It is an illustration, not a representative
estimate. Generated media stay in outputs/sqlite-visuals/.

## Reactive goal-refresh baseline

The same-action reactive supervisor refreshes once after a streak of failed
calls. Select streak length from 1, 2, 3 on validation completion alone. It
uses the same frozen worker, goal-refresh action, eligible times, and call
budget as the learned supervisor. Online execution is checked against the
collected endpoint outcomes and service-switch times.

Three fresh seeds 2026111501–2026111503 each verified 3,000 online traces.
State-aware completion was 81.6%, 78.2%, 80.6%; reactive goal-refresh completion
was 81.8%, 78.0%, 80.6%. Paired differences in percentage points and 95% intervals
were -0.2 [-0.6, 0.0], +0.2 [0.0, 0.6], and 0.0 [-2.4, 2.4].
There is no consistent learned advantage across these runs. This baseline
addresses the same-action comparison missing from the earlier direct service
switch rule.

## Observed-history information experiment

scripts/analyze_refresh_information.py freezes each of the three existing
workers and collects 3,000 fresh fitting and 1,500 fresh evaluation workflows
per worker. At each fixed decision pass, it estimates refresh-minus-persistence
success using the full observed binary response prefix plus required workload.
Prefix means are shrunk toward the global training mean with ten pseudo-counts,
fixed before evaluation. The comparator uses the global training mean alone.
This is a fixed-pass diagnostic, not an end-to-end sequential controller.

Evaluation-prefix coverage ranges from about 88% to 100%. Across workers and
passes, completion differences versus the timing-only rule range from -0.13
to +0.20 percentage points; every exploratory paired interval includes zero.
One worker has only one discordant workflow at pass 3 and none at other passes.
The other workers show more branch disagreement, but this fitted prefix
estimator does not consistently identify helpful decisions. This does not
prove that the observed histories contain no useful information.

The result limits the case for simply increasing supervisor capacity on the
current task. Revision opportunity also varies substantially with the trained
worker. A publication claim must account for that dependence.

## Direct-observation path ablation

The --goal-only option removes the direct observation path to the action head.
The manager still observes current history when it emits a goal. Between goal
updates the action score is constant. This is a restricted commitment control
and changes worker expressivity; it is not a general FeUdal architecture.

Three paired fresh seeds 2026111601–2026111603 compared the original and
restricted workers using identical initial parameter tensors, tasks, target
sampling, and training budgets. Original state-aware completion was 78.4%,
82.6%, 79.2%; restricted state-aware completion was 78.8%, 77.6%, 78.6%.
Restricted time-only completion was 78.8%, 77.4%, 79.8%. Each of the six runs
verified 3,000 online traces. The restriction provides no consistent state-aware
advantage and substantially lowers competence in one seed.

The remaining structural issue is that the manager goal has no independently
specified subtask semantics. Worker and manager train jointly against immediate
switch-versus-never-switch endpoint differences. Goal injection is causal,
but that alone does not establish a useful task decomposition. A stronger
mechanism study should define the manager commitment and its downstream
execution contract before changing hidden dimension or controller capacity.
