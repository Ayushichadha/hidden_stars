# Adaptive revision: current evidence and next decision

Updated November 17, 2026. This is the single active research brief. Completed
protocols remain evidence records, not competing experiment plans.

## Research objective

Extend paper 2's adaptive-controller question: can observations identify when a
persistent strategy should be revised to improve terminal verified outcomes under
a controlled budget? [Paper 1](https://arxiv.org/abs/2606.03741) supplies the
persistent-commitment mechanism; [paper 2](https://arxiv.org/abs/2609.00874)
distinguishes scores, actions and useful policy value. Numerical search tests the
question with an explicit worker. It is not an HRM/feudal architecture transfer.

## What the completed work establishes

| Study | Data | Main finding |
|---|---|---|
| Timing opportunity | 12 development seeds | Retrospective oracle exceeds best fixed timing by 0.002429; not a deployable result |
| Progress-conditioned prediction | 24 train / 12 validation / 24 confirmation | State and time policies choose the same late clock on every confirmation seed; zero advantage |
| Geometry/revision-quality follow-up | 24 train / 12 validation / 48 fresh confirmation | Moderate fixed configuration improves; richer geometry does not establish adaptive benefit |

The follow-up had two predeclared primary contrasts with adjusted 97.5% paired
intervals and a minimum useful mean gain of 0.0005:

- **H1, geometry-broad minus progress-broad:** +0.000281255,
  interval [-0.000208784, 0.001007672]. Failed the gate.
- **H2, selected fixed-moderate minus selected fixed-broad:** +0.006011583,
  interval [0.003712203, 0.008490446]. Passed; 36 wins, 7 losses and 5 ties.

H2 compares two validation-selected fixed configurations (moderate at window 4,
broad at window 5). It does not establish learned adaptive timing or isolate
strength at an identical clock. The manuscript reports all seven same-clock
means as a post-hoc descriptive check, not a new confirmation endpoint.
Geometry-conditioned policies did not establish superiority over simpler controls.
The strongest mean moderate policy is also a clock, not useful state adaptation.

This is consequential but scoped progress: a controlled revision-configuration
improvement and evidence against the tested observation upgrade. It is not yet
a successful adaptive-controller system or a record-breaking autoresearch agent.
The best follow-up confirmation construction scores 2.634292399, below the
archived reference 2.6359830849176076. No world-record claim is verified.

## Stop rule and next decision

This protocol is complete. Do not retune on any confirmation seeds, expand the
feature/model sweep to manufacture a positive result, or infer that a larger
controller is justified. The moderate recipe is now a supported baseline.

A further experiment needs a separately specified robustness question—for example,
a distinct search budget or circle count—and new confirmation trajectories. A
controller study needs evidence that observable state distinguishes useful
alternatives beyond clocks. The current negative result is limited to the tested
features, model, target and action space, not an impossibility theorem.

The manuscript [MANUSCRIPT.md](MANUSCRIPT.md) now centers the controlled
mathematical experiments and retains the HRM audit as scoped prior evidence.
It is a working research draft. Public raw-artifact packaging, submission format,
final reference editing and venue-specific checks remain before submission.

## Frozen task and implementation

AlphaEvolve problem 36: 26 disjoint circles in the unit square, maximize sum of
radii. Upstream commit: `8f447457957deac61e28bf1676746f0753b3b2f8`.
Fresh-start SLSQP calls, eight windows, 80 objective evaluations per window,
40 iterations per call. Each policy gets exactly 640 objective evaluations and
one replacement. Never-revise is a separate baseline. Equal objective counts do
not imply equal wall time, repair, constraint, or derivative work.

Initial perturbation scale is 0.015. Broad replacement is 0.12; moderate is the
predeclared geometric midpoint sqrt(0.015 * 0.12). Replacements persist. The
independent floating-point checker verifies serialized geometry and accounting;
a mathematical record would require an appropriately rigorous certificate.

- `scripts/matched_revision.py`: frozen commitments and exhaustive timings.
- `scripts/predict_revision.py`: progress/time models and causal policy replay.
- `scripts/revision_hypotheses.py`: geometry and moderate-recipe hypotheses.
- Corresponding `modal_*.py` files: bounded CPU collection and analysis.

For the follow-up, preparation is local and performs no numerical experiment:

```bash
.venv/bin/python -m scripts.revision_hypotheses --output outputs/revision-hypotheses-v1
```

That directory already exists and contains the completed run. Preparation refuses
overwrite. The existing run command resumes saved results without recollecting:

```bash
.venv/bin/modal run scripts/modal_revision_hypotheses.py --output outputs/revision-hypotheses-v1
```

Do not run it needlessly. Source changes invalidate the manifest. Pending calls
and stale locks require inspection; never delete them to infer that paid work
has not executed. All numerical studies used Modal CPU. L4 remains the user's
preference for any separately justified GPU experiment; its billing restriction
was not removed by the successful CPU runs.

## Execution, costs and evidence

| Run | Modal app | Local artifacts |
|---|---|---|
| Timing audit | `ap-t9i8xxYa5udMCVRbvFO57I` | `outputs/matched-revision-v1/` |
| Prediction | `ap-Rytpt3uN9q2tNQhczLx9S1` | `outputs/revision-prediction-v2/` |
| Follow-up | `ap-tRiwWPhOlw520FyvrXHGW6` | `outputs/revision-hypotheses-v1/` |

[Follow-up run](https://modal.com/apps/ayushichadha/main/ap-tRiwWPhOlw520FyvrXHGW6).
The follow-up completed 84 collections and two analyses, validating 1,260 distinct
schedule trajectories. Aggregate collection CPU time was 2,763.05 seconds.
Displayed workspace usage was $0.10 before and $0.17 afterward, fully credit-offset
with $0 billed. Rounded billing can lag or reconcile. No payment method was added.
The authorized $10 allowance was not approached. No further run was launched.

Protocol commit `876717a` precedes follow-up collection. Models freeze before
confirmation. Raw artifacts remain ignored locally; manuscript hashes identify
manifest, frozen models and summary but do not replace public artifact access.
Prediction v1 was prepared but never launched; v2 fixed a numerical implementation
issue before collection, without using experimental results.

## Verification and reviewer obligations

```bash
.venv/bin/python -m pytest tests/ -q
.venv/bin/python scripts/audit_manuscript_evidence.py
.venv/bin/python -m scripts.diagnose_hrm_copy_baseline
```

124 tests passed; the seven follow-up tests also passed with warnings as errors.
Saved HRM audits are artifact inspections, not training replications. The decoded
memorization predictions copy all 396 scored input tokens and miss all 13 changed
tokens; this establishes behavior for those artifacts, not an architecture bug.

The October review audit is a saved summary, not verbatim reviews
(commit `5264e9e`, historical `analysis/PAPER2_REVISION_PLAN.md`). Current obligations:

| Concern | Evidence/status |
|---|---|
| Test-selected baselines | New schedules/models selected on validation; confirmation frozen and separate |
| Mean versus exact revisions | New comparisons enforce exactly one replacement; never-revise labeled separately |
| Local versus terminal credit | Initial pilot includes matched targets; neither establishes adaptive superiority |
| Strong controls | Time-only, progress, geometry, fixed and reactive controls included |
| Independent evidence | Fresh trajectory splits; seed-level intervals, two-hypothesis adjustment |
| HRM zero solves / multiseed architectural claims | Unresolved; numerical search cannot close these concerns |
| Dataset lineage / original micro-macro tables | Historical HRM closure remains pending; not used as new math evidence |
| Literature and writing | Primary-source audit and revised math-centered draft; final formatting remains pending |

## Supporting infrastructure

The bounded parameter-autoresearch runner is `scripts/run_packing_autoresearch.py`.
It is not arbitrary LLM code evolution or a trained revision policy. Do not launch
its prepared L4 sweep as a substitute for a new hypothesis. Karpathy's original
[autoresearch](https://github.com/karpathy/autoresearch) provides the fixed-evaluation,
experiment-ledger pattern; implementing that pattern is not the empirical result.

Exa skill is installed at `.agents/skills/build-with-exa/SKILL.md`; its key is read
from the environment or ignored `.env.research.local`. The audit CLI is
`scripts/exa_research_audit.py`; successful search/content requests cost $0.014 as
reported by Exa. Evidence is retained in `outputs/exa-audit/`. No credentials are
stored in result files. A future LLM Exa tool must follow the skill's required
query/objective and freshness instructions. Current integration is an audit CLI.

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
