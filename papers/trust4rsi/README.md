# Adaptive revision for verified mathematical search

Updated November 17, 2026. This is the single active research plan. It supersedes
prior directions in this file and prospective suggestions in completed protocols.

## Research objective and relationship to the two papers

The central question is whether state-dependent revision of a persistent search
strategy improves terminal verified outcomes under a fixed computational budget.
The objective is to extend the adaptive-controller question from paper 2, rather
than make HRM repair a prerequisite for all further research.

- [Paper 1](https://arxiv.org/abs/2606.03741) studies persistent directional
  commitments in an HRM manager–worker architecture.
- [Paper 2](https://arxiv.org/abs/2609.00874) distinguishes a state-dependent score,
  a state-dependent policy, and useful terminal revision. Its HRM results do not
  establish a reliable adaptive advantage over the best tested forced timing.
- The next study tests the controller question with an explicit, inspectable
  search commitment and an independently checked mathematical objective.
  It is a conceptual extension of paper 2, not demonstrated transfer of HRM,
  learned latent goals, or the feudal training loss.

HRM and feudal subgoals remain prior mechanisms and evidence. Further HRM training
is deferred unless an architectural transfer claim becomes an explicit objective.
The SQLite demonstrations remain engineering pilots, not the main evaluation.

## One benchmark, a frozen contract

Start with AlphaEvolve problem 36: 26 non-overlapping circles inside the unit
square, maximizing the sum of their radii. Retain the pinned upstream commit
8f447457957deac61e28bf1676746f0753b3b2f8 documented in MATH_SEARCH_PILOT.md.
This choice offers a concrete construction, numerical objective, and existing
implementation; its selection does not imply it is easy to improve or sufficient
by itself to establish general agent competence.

Before any new experiment, freeze the constraint convention, verifier, optimizer,
initial-state generator, seed partitions, resource budget, and failure handling.
Distinguish feasible raw outputs from repaired outputs and charge repair compute
to every policy. Independent verification must not reuse the optimizer's loss.
The archived reference sum 2.6359830849176076 is a reference construction, not a
verified current record. Strict and tolerance-relaxed certificates must not be
compared as if equivalent. Record claims require a current primary-source audit
and independently replayable construction/certificate.

## Controller contract to implement

A worker runs a frozen numerical optimizer in equal search windows. A commitment
specifies a search strategy (initially, a fixed local-search/perturbation recipe)
and remains active across windows. The controller sees only past and current
observations and chooses KEEP or REVISE. A shared, frozen revision rule generates
the replacement strategy; policies cannot receive different proposal quality.
Every policy preserves the best verified incumbent. Revising changes future
search, never the evaluator or a previously measured score.

Start with one initial commitment and exactly one optional-timing replacement
per episode: every eligible policy must eventually use that replacement before
the final window. This matches intervention counts and isolates timing. Evaluate
never-revise separately as a practical baseline, not as an exact-count control.
A variable-count controller is a later experiment with explicitly charged costs.
Choose window count and budget from development feasibility measurements and
freeze them before policy training and confirmation.

Candidate features: verified improvement history, stagnation duration, current
constraint residuals, incumbent quality, commitment age, and budget remaining.
Use a small interpretable terminal-value model first. A larger neural controller
is justified only by evidence that simpler models miss useful structure.

## Execution sequence and stopping rules

1. **Validate the worker and evaluator.** Reproduce the reference construction's
   score with the checker and measure a strong optimizer-only baseline from fresh
   starts. Loading a reference is a verifier test, not optimizer reproduction.
   Record feasibility, terminal score, runtime, and failure rate. Competence for
   this continuous task means useful feasible optimization, not ARC exact solves.
2. **Measure revision opportunity.** On development trajectories, clone full
   optimizer/RNG state and compare legal revision times with matched remaining
   budgets and common random streams where applicable. Exhaust the small timing
   space. An oracle using final outcomes is an analysis ceiling, never a deployable
   baseline. If different states do not benefit from different timings, stop
   controller training and report that this action space lacks opportunity.
3. **Test usable information.** Compare state-aware prediction against time-only,
   constant/majority, and within-time controls. Train on terminal score differences;
   compare with a matched local-improvement target to test credit horizon. Split
   by whole initial trajectory before generating branches: related branches and
   checkpoints cannot cross train/development/confirmation partitions.
4. **Evaluate complete policies.** Freeze features, thresholds, models, schedules,
   and hyperparameters using development data. Compare best development-selected
   fixed timing, random timing, reactive stagnation, time-only, and state-aware
   timing under identical worker, replacement rule, and exact intervention count.
   Include optimizer-only/never-revise as separately labeled resource baselines.
   Score complete untouched trajectories, charge controller and repair overhead,
   and report paired effects, uncertainty, seed variation, and failure rates.
5. **Expand only on evidence.** If terminal policy benefit survives confirmation,
   test a predeclared held-out circle count or budget regime before broader claims.
   A record attempt and a richer code-editing agent come after this controlled
   evaluation. Neither is assumed to succeed. If no benefit appears, distinguish
   lack of opportunity, uninformative observations, and policy/credit failure.

Before launches, record the primary endpoint (final verified sum of radii), a
practical effect threshold based on development variability, sample size/budget,
selection rules, and planned confidence intervals. No repeated peeking at the
confirmation set or changing the endpoint after seeing results.

## How autoresearch fits

Use [Karpathy's autoresearch](https://github.com/karpathy/autoresearch) as the
engineering pattern: frozen evaluation, baseline first, bounded experiments,
hypotheses, keep/discard/crash decisions, and retained failure history.
There are two distinct timescales: a controller revises a commitment within a
search episode; an outer research loop proposes algorithm/configuration changes
between experiments. Freeze the outer choices during a controller comparison.
Changing both simultaneously would obscure what caused an improvement.

The existing scripts/run_packing_autoresearch.py is a bounded parameter-search
baseline, not a learned revision controller or arbitrary source-code evolution.
It evaluates one baseline and three development proposals, freezes the winner,
then confirms baseline/winner on fresh starts. It retains source/evaluator hashes,
raw constructions, locks, failure markers, and a keep/discard ledger. Its presence
establishes orchestration capability, not scientific superiority.

## Existing evidence and compute status

- Saved HRM branch audits have no exact solves under either intervention.
  The four-example memorization predictions copy all 396 scored input tokens;
  accuracy equals the identity baseline and changed-token accuracy is 0/13.
  This is a scoped behavioral diagnosis, not proof of an architectural defect.
- The completed packing neural study does not establish superiority over
  always-local search and does not evaluate full sequential learned policies.
- The L4 optimizer image built, but Modal rejected GPU execution because a
  payment method was required. No GPU optimizer steps ran in that attempt.
- Numerical CPU/GPU experiments use Modal. Preserve the user's L4 preference,
  one-container/no-retry limits and historical $10 allowance. Verify availability
  and remaining allowance before launches. The prepared parameter protocol allows
  up to six sequential 600-second calls; timeout is not an account-wide cost cap.
- Local code, tests, manuscript work, and saved-artifact analysis can proceed.
  Do not launch the parameter sweep merely because it is ready: first determine
  which frozen worker configuration the controller experiment requires.

## Implemented timing experiment and commands

The interface and exhaustive development timing collector are implemented in
`scripts/matched_revision.py`; CPU transport is `scripts/modal_matched_revision.py`.
CPU suits this SciPy worker; the separate GPU optimizer retains the L4 preference.

Prepare locally without optimization or cloud calls:

```bash
.venv/bin/python -m scripts.matched_revision --output outputs/matched-revision-v1
```

Once Modal CPU access and remaining allowance are checked:

```bash
.venv/bin/modal run scripts/modal_matched_revision.py --output outputs/matched-revision-v1
```

The default is twelve development seeds, eight windows, 80 objective evaluations
per window, seven exact-one-replacement timings and a separate never-revise
baseline. Each policy receives 640 logical objective evaluations; shared-prefix
collection executes 2,880 per seed (34,560 for twelve). Local tests are tiny
verification checks, not research runs. The dispatcher uses one CPU container,
600-second per-seed timeout and no retries: twelve calls permit up to two hours
of function execution, with startup costs additional. Check the existing spending
allowance before execution; this is not a dollar cap or permission to exceed it.

The run folder stores a source-hashed manifest, traces/constructions, runtime
versions and retrospective development summary. Completed calls are reused only
with matching manifest identity and validated results. Pending calls and stale
locks require inspection; do not delete them and rerun blindly. Changed code
requires a fresh manifest/output directory. Only the default numerical protocol
is accepted by this bounded runner. Controller fitting and held-out policy
assessment are not implemented by this opportunity collector. Its best fixed
schedule is development-selected; its oracle is not a deployable policy.

## Completed Modal CPU audit — November 17

The prepared `outputs/matched-revision-v1/` batch completed: twelve seeds,
96 validated trajectories, no payment method added. Best fixed timing was
replacement before zero-based window 5: mean 2.619759325 versus never-revise
2.619093703. The retrospective per-seed oracle added 0.002429465 over that fixed
schedule. This is development timing opportunity, not learned policy performance
or a new record. All twelve seeds remain development-only.

[Modal run](https://modal.com/apps/ayushichadha/main/ap-t9i8xxYa5udMCVRbvFO57I).
The displayed workspace metered total increased from $0.08 to $0.09, offset by
credits; billed cost remained $0. Rounded billing can lag. Numerical worker time
was 212.42 seconds. The full audit stayed far below the $10 allowance. GPU billing
restrictions remain separate; this establishes CPU access for this account/run.
The existing prepared-run command now reuses completed local seed results rather
than executing them again. Next: state-information diagnostics and trajectory-level
training/confirmation design; no further compute was launched after this audit.

## Frozen prediction pilot

`scripts/predict_revision.py` and `scripts/modal_predict_revision.py` implement
training/validation/confirmation allocation (24/12/24 seeds), ridge state-versus-time
models, a local-target control, validation-selected fixed/reactive baselines,
causal full-trajectory replay, and paired confirmation intervals. Existing audit
seeds are training-only. The executed manifest lives in
`outputs/revision-prediction-v2/`; v1 was prepared but never launched and was
superseded by a numerically robust equivalent covariance implementation before
collection. No experimental result motivated that change.

The primary success gate is state-terminal minus time-terminal gain >= 0.0005
with paired 95% interval entirely positive. Policies freeze before confirmation
collection. Forty-eight new collection calls plus two analysis calls have a
maximum aggregate function timeout of 30,000 seconds (about $0.53 CPU/memory at
the checked rates, excluding setup). All calls are sequential and have no retries.
The user authorized this study within the existing $10 total allowance.

## Prediction pilot outcome — November 17

Completed all 48 new CPU collections and both analysis calls. Frozen policies
were evaluated on 24 untouched confirmation seeds. State-terminal, time-terminal,
and the validation-selected fixed policy all revised before window 7 on every
seed. Mean score was 2.616691995 for all three; paired gain was exactly zero,
so the predeclared success gate failed. State prediction MSE improved slightly,
but sign accuracy was below the always-nonpositive baseline. No useful adaptive
advantage was demonstrated. Reactive and local-target comparisons had intervals
crossing zero. Full table, limitations and artifact hashes are in the manuscript.

[Modal run](https://modal.com/apps/ayushichadha/main/ap-Rytpt3uN9q2tNQhczLx9S1).
Displayed metered usage increased from $0.09 to $0.11, covered by credits with $0
billed; billing is rounded and may lag. New numerical collection totaled 771.81
seconds. Tests: 117 passed; six prediction tests also passed with warnings treated
as errors. A whole-suite warning-as-error check exposed pre-existing SQLite
connection cleanup warnings; normal full-suite execution passed.

Do not retune on the confirmation set. A new hypothesis about geometry features,
replacement strategies, or credit targets needs a separate protocol and new
confirmation seeds. The current evidence does not justify a larger controller
or a claim of successful adaptive research. No further run was launched.

## Manuscript work

[MANUSCRIPT.md](MANUSCRIPT.md) contains the archived HRM evidence and completed mathematical timing/prediction
pilots. It remains a working draft rather than a submission-formatted paper. The prospective paper should lead with the
adaptive revision question, then formalize commitments/actions/budgets, describe
opportunity and credit-horizon tests, and report complete held-out policy results.
Use the HRM findings as motivation and clearly scoped prior evidence. Do not
present proposed math experiments as completed findings or claim a new record.
A reasonable provisional title is *When Should a Search Agent Revise Its Strategy?*
Final scope and title must follow results rather than a submission deadline.

## Completed supporting records

Keep [explicit SQLite results](EXPLICIT_PROTOCOL.md),
[latent-controller methods/results](CONTROLLER_DESIGN.md),
[math pilot](MATH_SEARCH_PILOT.md), [paired math results](PAIRED_MATH_RESULTS.md),
[Meta integration](META_AGENT_PILOT.md), and
[completed neural study](NEURAL_SUPERVISOR_PROTOCOL.md) as experiment records.
Their earlier suggested next steps do not override the active plan above. Seed labels
and dated headings are not independently verified execution dates. Prior-paper
artifacts remain in [beyond-the-clock](../beyond-the-clock/README.md).

Superseded manuscript outlines and research plans were removed. No raw results,
checkpoints, or source code were removed.

### Reviewer requirements and closure evidence

Recovered from the saved October 10 review audit in Git commit 5264e9e,
analysis/PAPER2_REVISION_PLAN.md. This is a review summary, not the verbatim reviews.

| Concern | Required evidence | Current status |
|---|---|---|
| Test-selected fixed baseline | Choose schedules/candidates on development; freeze before confirmation | Required for new runs |
| Mean versus exact intervention count | Exact-K comparisons or explicitly separate variable-count budget study | Unresolved HRM experiment |
| Local loss versus downstream value | Matched local-target/terminal-target controls; score whole trajectories | Endpoint audit exists; policy benefit unresolved |
| Seed-0-only mechanism/oracle | Repeat frozen schedule analysis across available seeds | Unresolved |
| Zero exact solves | Competent HRM task regime before revision-policy claims | Audit confirms gap; unresolved |
| Dataset and split ambiguity | Source IDs, augmentation lineage, disjoint partitions and hashes | Full lineage audit pending |
| Micro/macro discrepancies | One canonical table with denominators and separately selected winners | Pending |
| Weak critic comparison | Majority, time-only, within-time, reactive and optimizer-only controls | Partial historical evidence; new frozen comparison pending |
| Literature and workshop fit | Verified primary references and concrete difference from prior algorithms | Pending reference verification |
| Unclear writing and scope | Mechanism diagram, endpoint-first results, distinguish HRM from numerical search | Draft improved; final rewrite pending |

Do not mark a reviewer concern resolved merely because it appears in this table.
Math experiments address the general revision question; they cannot close missing
HRM competence, exact-K, or multi-seed architectural evidence.

## Reproduce saved audits

```bash
.venv/bin/python scripts/audit_manuscript_evidence.py
.venv/bin/python -m scripts.diagnose_hrm_copy_baseline
.venv/bin/python -m pytest tests/ -q -rs
```

These audits inspect saved artifacts; they do not replicate training. The current full test run passed 111 tests, including nine new timing-protocol
tests. No substantive numerical experiment or Modal call ran during this update.

## Exa literature and benchmark audit

The requested build-with-exa skill is installed at
`.agents/skills/build-with-exa/SKILL.md`; exa-py 2.28.0 is installed in `.venv`.
The reusable `scripts/exa_research_audit.py` uses the skill's documented raw HTTP
search/contents shapes. It reads EXA_API_KEY from the environment or ignored
`.env.research.local`; credentials are not written to audit outputs.
A successful benchmark search verified the key. One search plus two contents
requests cost $0.014 total as reported by Exa. All seven requested content pages
returned success. Raw evidence stays in ignored `outputs/exa-audit/`.

The audit found incompatible numerical feasibility contracts and rounded versus
full-precision packing comparisons. The manuscript now distinguishes source
reports from independently replayed certificates and excludes equal-radius
packing tables from the sum-of-radii comparison. No current world-record claim
is verified. Reviewer references now have explicit comparison obligations;
empirical review concerns remain open until their experiments are completed.

For a future LLM search tool, require both query and objective, forward objective
unchanged, and add to its system prompt: "Call web_search before answering unless
you're certain the answer can't have changed since your training cutoff."
Current integration is an explicit audit CLI, not a newly deployed LLM agent.


The delegated offline HRM diagnosis establishes that the 1,600-update saved
predictions copy all 396 scored input tokens. The 96.72% accuracy equals the
identity baseline; all 13 tokens requiring a transformation are incorrect.
Reproduce with `.venv/bin/python -m scripts.diagnose_hrm_copy_baseline`.
Targets match unique dataset rows; no conflicting labels for identical matched
inputs were found within puzzle ID 9872. This is a behavioral diagnosis, not
proof of an architecture or optimizer bug. Future competence checks must report
input-copy accuracy and changed-token accuracy as well as exact solves.
