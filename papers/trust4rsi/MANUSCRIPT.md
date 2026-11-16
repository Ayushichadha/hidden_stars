# When Revision Has No Successful Alternative: Auditing Persistent Subgoals in Hierarchical Reasoning

Ayushi Chadha

Working manuscript, November 16, 2026. Diagnostic framing based on completed
local evidence. Related-work verification, venue formatting, and final submission
metadata remain pending. This title does not assert an improvement result.

## Abstract

Persistent latent subgoals offer a mechanism for coordinating computation across
multiple reasoning steps, but deciding when to replace them requires evidence
that revision improves downstream outcomes. We audit this question in Scout,
an extension of the Hierarchical Reasoning Model with manager-generated
directional goals and worker alignment. In an archived 64-episode diagnostic,
persistence is preferred by the recorded loss comparison in 347 of 384 decision
states. Yet neither persistence nor a forced revision produces an exact solve.
A broader development audit covering 80 source problems likewise records no
exact solves under either intervention. A repeated-batch competence control
reaches 96.72% token accuracy after 1,600 updates while solving none of four
examples. These observations limit the interpretation of score-based revision
preferences: they do not establish successful subgoal selection or improved
problem solving. We distinguish the HRM mechanism from partial latent-goal and
explicit search-controller explorations, and specify an evaluation sequence
based on worker competence, causal goal utility, terminal revision opportunity,
and frozen-policy comparisons. The current evidence motivates these checks;
it does not demonstrate an advantage for adaptive HRM revision.

## 1. Introduction

Hierarchical reasoning separates slower coordination from faster computation.
A manager can communicate a persistent goal to a worker rather than choose each
worker action directly. Persistence creates a further decision: should the
current goal remain active, or should the manager replace it using the new
reasoning state? Updating too frequently may interrupt useful computation;
retaining an unsuitable goal may waste the remaining budget.

Scout investigates this decision within HRM. The scientific question is whether
state-dependent revision of persistent feudal subgoals can improve final task
outcomes beyond time-based schedules and observable reactive rules. A convincing
test requires more than a predictor that distinguishes the losses of two
branches. The worker must solve tasks, its behavior must depend on the goals,
and the available revisions must sometimes improve terminal success.

This report examines whether the available evidence satisfies those conditions.
Its contribution is a scoped empirical diagnosis and an explicit evaluation
protocol. It does not introduce an established superior revision policy. The
observations concern the audited checkpoints and data regime, and do not imply
that HRM or hierarchical reasoning is generally unable to solve these tasks.

## 2. Persistent directional goals inside HRM

HRM maintains high- and low-level recurrent hidden states. Scout projects the
manager's high-level state into a directional goal, optionally with a scalar
gate. The recurrent carry caches the goal, gate, and worker anchor until the
next update. The worker consumes that cached commitment during refinement.

In the corrected causal interface, a manager emission after outer pass t first
influences pass t+1. The manager period counts outer ACT refinement calls rather
than inner transformer cycles. Under the eight-pass evaluation budget, the
first pass is initially unsteered and an emission after the terminal pass cannot
affect the scored outcome. Goal resets are per sample.

The directional configuration aligns worker displacement from the commitment
anchor with the cached goal. Schematically, for worker representation w, anchor
b, and goal g, the auxiliary term is 1 − cos(w − b, g), combined with the task
and halting objectives using the configured weight. This describes the
directional configuration; the code also preserves a historical absolute-state
alignment mode. Stored recurrent commitments are detached between calls. The
adaptive implementation provides local manager/trigger credit through a
value-preserving reconstruction on the consuming pass, rather than full
backpropagation through the entire episode.

The implementation lives in `HRM/models/subgoal_head.py`,
`HRM/models/hrm/hrm_act_v1.py`, and `HRM/models/losses.py`. Mechanism tests
check properties such as timing and gradients. Passing those tests establishes
implementation behavior under the tested conditions, not empirical goal utility.

## 3. What revision value should measure

For a frozen worker, define the terminal revision advantage at state s and pass
t as the expected success after refreshing the goal minus expected success
after retaining it, conditional on the same remaining budget and subsequent
policy. Both branches must begin from the same complete state. If the worker
or environment is stochastic, branch randomization and repeated continuations
must be specified.

This quantity differs from a local loss difference. A small improvement in token
loss can leave the exact predicted solution unchanged. It can also improve many
already-correct tokens while retaining the few errors that determine failure.
Consequently, loss preference is a secondary diagnostic rather than a substitute
for terminal success.

A selective policy also needs more than hindsight headroom. Its observable
features must identify beneficial actions before their outcomes are available.
Evaluation must therefore distinguish branch opportunity, supervised prediction
on held-out states, and whole-trajectory performance of a frozen policy. Repeated
states from the same problem belong to the same partition and uncertainty unit.

## 4. Audit methods

We inspect saved artifacts rather than rerun checkpoint inference. The original
endpoint table contains 64 episodes and six eligible revision positions per
episode, producing 384 branch rows. The development table contains 80 episodes
from 80 recorded sources and the same six positions, producing 480 rows.
Persistence outcomes repeat across decision positions and must not be counted
as independent successful trials. Both tables score exact completion after the
fixed eight-pass trajectory.

The archived score diagnostic contains 384 state-level preferences. We count
its PERSIST labels separately from the endpoint audit. To inspect fitting
capacity, we also examine saved decoded predictions and configuration from a
1,600-update repeated-batch run. All four examples share one puzzle identifier.
This control concerns fitting on that batch, not source-level generalization.

The accompanying audit script recomputes counts and records SHA-256 identities
for the input artifacts. It neither authenticates the original execution nor
reconstructs absent checkpoints. The audit output makes this boundary explicit. The current repository test suite passes 96 tests; those
checks do not constitute a fresh experimental replication.

## 5. Findings

| Audit | Evaluation units | Observed outcome |
|---|---|---|
| Score preference | 384 states / 64 episodes | PERSIST preferred in 347 states (90.4%) |
| Original endpoint comparison | 64 episodes / 384 revision branches | Zero persistence solves; zero revision solves |
| Development endpoint comparison | 80 sources / 480 revision branches | Zero persistence solves; zero revision solves |
| Repeated-batch control | Four examples / one puzzle ID | 13 errors among 396 scored tokens; zero exact solves |

The endpoint comparisons contain no successful rescues and no successful
solutions lost by revision. They therefore cannot establish whether a policy
chooses between successful and unsuccessful alternatives. They still permit
analysis of score changes, provided those changes are described as such.

The repeated-batch control yields 96.72% token accuracy. Its remaining errors
illustrate why this number cannot be read as task-solving competence. The
saved predictions establish failure on these four examples; they do not identify
the cause. Data handling, representation, training dynamics, and alignment
interference remain candidate explanations requiring controlled checks.

Taken together, these results put competence ahead of further revision-policy
optimization in the current regime. They do not justify another increase in
training budget without investigating the observed plateau, nor do they prove
that useful revision is impossible with a competent worker.

## 6. Supporting explorations and mechanism boundaries

Three experimental families share an abstract retain/revise question while
implementing different mechanisms. They should be interpreted separately.

The explicit SQLite controller chooses when to switch between services under a
call budget and synthetic failures. Its frozen comparisons report state-aware
completion improvements of 1.90–3.63 percentage points over learned timing.
Advantages over reactive rules are inconsistent, and persistent-outage cases
show harms. These results concern explicit service commitments rather than
HRM latent goals. The numerical statements here are taken from the preserved
explicit protocol; the present evidence script does not recompute them.

The SQLite latent bridge conditions a small learned worker on cached Scout
goals and permits refresh. It is a partial mechanism transfer: it does not
instantiate full HRM recurrence and omits the original directional auxiliary
loss. Across three runs totaling 1,500 workflows, state-aware refresh rescues zero
and loses one workflow relative to learned timing. This does not demonstrate
added value from state over learned timing. It cannot supply the missing HRM competence evidence.

The circle-packing branch chooses between local and broad numerical search.
Its completed neural study uses 80 fitting, 20 validation, and 40 test
trajectories. On test, neural supervision minus checkpoint-only selection is
+0.001146 in final radius sum, with a trajectory-bootstrap interval of
[−0.000263, +0.002800]. Against always-local search the difference is −0.000333,
with interval [−0.001957, +0.001253]. Neither comparison establishes neural
superiority. Three checkpoint decisions within each trajectory are grouped for
uncertainty. This experiment, including its external-model supervisor variant,
does not implement HRM's recurrent hierarchy, directional goals, or feudal loss.

These explorations inform evaluation design. They do not establish a chain
from HRM subgoals to a successful general meta-agent.

Mathematical search was selected to move toward substantive, independently
verifiable research tasks. An autonomous research system must additionally choose
experiments sequentially, retain evidence from failures, verify proposed results,
and preserve an auditable decision history. The existing single-decision study
establishes neither such a complete research loop nor a mathematical record.
For trustworthy evolution, the relevant proposed safeguards are independent
verification, explicit resource accounting, regression checks against the incumbent,
and rejection of unsupported improvements. Their effectiveness remains to be tested.

## 7. Required controlled evaluation

The next HRM study should first establish held-out exact-solving competence in
a bounded task regime, with matched ablations for goal injection and alignment.
Saved color errors should be traced through tokenization, masking, embeddings,
and training before selecting further training changes. Source partitions and
competence criteria must be fixed using development data before final evaluation.

A frozen competent worker then permits causal goal interventions. Retained,
refreshed, and shuffled goals can distinguish behavioral influence from task
utility. Endpoint tables should report persist-only success, refresh-only
success, both, and neither, stratified by decision pass. Useful intervention
outcomes are a prerequisite for fitting a revision selector.

Finally, time-only and state-aware supervisors should use identical paired
training outcomes, action availability, continuation rules, and tuning effort.
Whole-trajectory evaluation must include persistence, validation-selected fixed
schedules, and an observable reactive baseline. Any exact-count intervention comparison must enforce the same action count;
matching only the mean number of emissions is insufficient. Report both macro
and micro token accuracy with explicit denominators and source/augmentation
lineage. Deployable schedules must be selected on validation data, with any
test-selected best schedule labeled retrospective. Source-level paired uncertainty,
rescues and losses, independent seed variation, worker computation, controller
overhead, and branch-data collection cost should be reported separately. These
experiments are proposed work, not completed results in this manuscript.

## 8. Limitations and related-work completion

The present audit is confined to saved local artifacts and a compact HRM regime.
Its zero-success outcomes make exact-success action selection uninformative in
the examined sample. Historical calibration and development data cannot be
promoted to a fresh final test set. The memorization control covers one puzzle
identifier. The exploratory systems use different objectives and action spaces,
preventing a pooled performance conclusion.

The final related-work section must verify primary sources for HRM, FeUdal
Networks, metareasoning, and learned replanning, including the reviewer references
recorded in the project notes. That verification and novelty assessment are
pending. The manuscript makes no claim to reproduce those algorithms from their
motivational summaries. Prior Scout studies should be cited with their exact
protocols and metric definitions after publication metadata is checked.

## 9. Conclusion

The available HRM evidence distinguishes score preference from successful
revision. Persistence often wins the recorded loss comparison, but neither
branch solves the audited tasks. A high-token-accuracy memorization control
also leaves exact solutions unresolved. The immediate experimental need is a
competent HRM worker whose goals have useful causal effects and whose revision
choices offer measurable terminal headroom. Adaptive revision remains the
research question; the current manuscript records why its answer is still open.
