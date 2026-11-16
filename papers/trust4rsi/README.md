# HRM revision study

Updated November 16, 2026. This is the single current experiment plan.

**Question:** Can state-dependent revision of persistent feudal subgoals improve
hierarchical reasoning under a controlled computational budget?

Start writing in [MANUSCRIPT.md](MANUSCRIPT.md). It contains the mechanism,
completed findings, claim boundaries, limitations, and proposed evaluation.
Its current framing is diagnostic: adaptive HRM improvement is not established.

## What is settled

- HRM is the main system. SQLite bridges and mathematical search remain supporting
  explorations; neither demonstrates successful HRM transfer to a general agent.
- The saved HRM endpoint tables contain zero exact solves under either action:
  64 original episodes and 80 source-separated development episodes.
- The 1,600-update repeated-batch control reaches 96.72% token accuracy but 0/4
  exact solves. All four examples share one puzzle identifier.
- The neural packing study is complete and does not establish superiority over
  always-local search. It implements numerical search supervision, not HRM.

## Remaining work, in order

1. Diagnose the saved 13 color errors through data processing, masks, embeddings,
   and training; compare matched HRM goal-injection/alignment ablations.
2. Establish held-out exact-solving competence in a bounded HRM task regime.
   Set a competence criterion on development data before testing.
3. Freeze the worker; verify causal goal influence and useful terminal revision
   opportunity using cloned-state persist/refresh branches and goal interventions.
4. Only then compare time-only, state-aware, fixed, reactive, and persistence
   policies on untouched source problems under matched budgets. Report rescues,
   losses, source-level uncertainty, seed variation, and controller overhead.
5. Verify primary references, novelty, venue requirements, and author metadata;
   format and visually inspect the final manuscript.

The draft can be developed now. A positive improvement paper requires steps 1–4.
No further substantial training, cloud job, or API experiment was launched during
this cleanup. Existing compute preferences require Modal for substantial future
runs; authentication and authorization status need checking before execution.

## Verify saved evidence

```bash
.venv/bin/python scripts/audit_manuscript_evidence.py
.venv/bin/python -m pytest tests/ -q -rs
```

The audit prints counts and SHA-256 identities without training or checkpoint
inference; missing local files are explicit. Raw outputs remain ignored. Hashes
identify artifacts but do not independently verify the original execution.
During consolidation, all 96 existing tests passed. The audit script also passed
Ruff and Black checks after formatting. No new experimental replication is claimed.

## Completed supporting records

Keep [explicit SQLite results](EXPLICIT_PROTOCOL.md),
[latent-controller methods/results](CONTROLLER_DESIGN.md),
[math pilot](MATH_SEARCH_PILOT.md), [paired math results](PAIRED_MATH_RESULTS.md),
[Meta integration](META_AGENT_PILOT.md), and
[completed neural study](NEURAL_SUPERVISOR_PROTOCOL.md) as experiment records.
Their earlier suggested next steps do not override the plan above. Seed labels
and dated headings are not independently verified execution dates. Prior-paper
artifacts remain in [beyond-the-clock](../beyond-the-clock/README.md).

Superseded manuscript outlines and research plans were removed. No raw results,
checkpoints, or source code were removed.

## Direction after the hackathon clarification

Mathematical search was deliberately selected as a serious, independently
verifiable application after the software task proved too narrow. Retain it as
an active research direction. The present local/broad controller is a baseline
for that direction, not an implementation of the HRM mechanism.

The shared question is whether persistent commitments and evidence-based revision
improve verified outcomes under a fixed resource budget. Trust4RSI and the
hackathon have different success criteria: a rigorous controlled finding can
support a workshop paper; the hackathon additionally seeks a verified improvement
over a current mathematical record with an auditable autonomous research loop.
No record improvement has been established here.

For Trust4RSI, prioritize a four-page empirical diagnostic paper using the existing
HRM audit and a clearly scoped mathematical-search case study. Keep the main claim
about evaluating revision value; do not promise an HRM-powered mathematical agent.
A stronger architectural paper requires the competence and mechanism gates above.

For the mathematical research system, the next concrete work is:

1. Pin one problem, its exact objective/constraints, public verifier version,
   reference construction, and dated best-known bound. Verify the existing packing
   outputs with the external problem definition before comparing scores.
2. Implement and evaluate complete sequential research runs: propose a search
   change, execute within budget, independently verify, accept or reject, record
   failed ideas, and choose the next experiment. The current single-decision
   neural study does not establish this capability.
3. Compare that loop with strong optimizer-only, fixed-schedule, reactive, and
   time-only baselines using equal total search budgets and independent seeds.
   Log proposals, costs, verifier outputs, incumbent changes, and failures.
4. Treat an HRM-to-search bridge as a separate unproven engineering milestone:
   specify the search-state representation, persistent goal semantics, learned
   worker and training objective, then demonstrate causal goal utility. Renaming
   an external supervisor or importing only SubgoalHead does not achieve this.

The official Trust4RSI page currently lists November 20, 2026 AoE, four-page short
papers and eight-page full papers. Use the short-paper scope unless new evidence
supports more. Prepare an anonymous submission separately from this public draft.
Source: https://trust4rsi-agent.github.io/AAAI2027/
Benchmark sources checked November 16: https://teorth.github.io/optimizationproblems/
and https://github.com/google-deepmind/alphaevolve_repository_of_problems .
These links establish benchmark resources, not a verified target record for our run.

## Active autoresearch protocol — November 16

Use Karpathy's original README and program.md as the loop reference:
https://github.com/karpathy/autoresearch and
https://github.com/karpathy/autoresearch/blob/master/program.md .
Our adaptation fixes the verifier, measures a baseline first, permits one bounded
search-code change per experiment, and records keep/discard/crash decisions.
Use immutable candidate snapshots rather than resetting the shared working tree.
Each proposal must state a hypothesis before execution. Preserve failed proposals.
All numerical experiments run on Modal; local work is editing and artifact inspection.
The initial numerical optimizer needs CPU, not GPU. GPU allocation requires a
specific learned-worker experiment; renting a GPU alone adds no scientific value.

Selected task: AlphaEvolve problem 36, maximize the sum of radii of 26 disjoint
circles in the unit square. Retain the existing pinned upstream commit
8f447457957deac61e28bf1676746f0753b3b2f8 and checker described in
MATH_SEARCH_PILOT.md. The archived reference sum 2.6359830849176076 is a historical
construction, not a verified current world record. Recheck the live bound and
external verifier before any record claim. Do not expand to additional tasks yet.

Execution order: Modal smoke; frozen optimizer baseline; bounded candidate edits;
independent verification; keep/discard ledger; fresh-seed confirmation of the
selected candidate. Log candidate/source/evaluator hashes, parent, hypothesis,
seed, objective and constraint calls, runtime, resources, feasibility margins,
raw construction, and decision reason. Acceptance requires verified feasibility
and development improvement; final claims require untouched confirmation seeds.
Start with at most three candidate experiments, one container and no automatic
retries, within the previously recorded $10 Modal allowance. A timeout/resource
limit is not an account-wide dollar cap. Check remaining allowance before scaling.

The existing Modal entry point is a transport/paired-rollout smoke test, not the
complete code-editing research loop. A smoke success must not be reported as an
autoresearch improvement. Karpathy's indefinite-loop instruction is not adopted
as permission for unbounded paid experiments.

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

Modal check on November 16: the network-enabled smoke invocation returned
`Token has expired`; no numerical experiment started. Renew authentication with
`.venv/bin/modal token new`, then rerun
`.venv/bin/modal run scripts/modal_math_runner.py`. Execution remains blocked
until authentication succeeds; no baseline or candidate result is claimed.


GPU execution update: Modal credentials were verified and the profile activated.
The first GPU image built successfully, but Modal rejected function creation:
`Please add a payment method to use L4 GPU functions.` No optimizer steps ran.
The runner `scripts/modal_gpu_packing.py` now requests one L4 following the author's final GPU preference, retaining a 600-second timeout, one container, and no retries. It tests
three penalty schedules over 32 paired starts with 2,000 steps per schedule.
This is a GPU optimizer development pilot, not an HRM or learned-policy study.
Modal requires a payment method for GPU access; changing GPU type does not remove
that account prerequisite. After billing is enabled, launch with
`.venv/bin/modal run scripts/modal_gpu_packing.py`.


Local completion update: decoded-grid auditing independently confirms all 13
memorization errors (4/2/2/5 per example), all color substitutions. The manuscript
now includes the causal timing diagram and primary-source related-work discussion
covering the four reviewer references, HRM, FeUdal Networks, autoresearch, and
AlphaEvolve. This closes the missing introductory positioning, not the empirical
comparisons requested by reviewers. Full reference formatting and submission
rendering remain pending. The GPU runner now logs failure status and evaluator
hashes, rejects nonfinite loss, and saves completed reports atomically. No new
training or search results were produced by this update.


## Ready-to-run bounded parameter autoresearch

Implemented in `scripts/run_packing_autoresearch.py`, using the L4 evaluator.
Prepare without cloud calls:

```bash
.venv/bin/python -m scripts.run_packing_autoresearch --output outputs/autoresearch-l4-v1
```

After billing is enabled, execute the same frozen run:

```bash
.venv/bin/python -m scripts.run_packing_autoresearch --output outputs/autoresearch-l4-v1 --execute
```

One baseline and three proposals use the same 32 development starts. The proposer
tries penalty schedules and adapts the learning rate based on retained outcomes.
The winner is saved before comparing baseline and winner on 32 fresh starts.
At most six calls run sequentially: one L4, 600 seconds per call, no retries.
This permits up to one hour of function execution, rather than one ten-minute
pilot; image/startup costs are additional. The historical $10 allowance remains
in force. No new cloud calls were made while implementing the loop.

Candidate snapshots, raw constructions, source/evaluator hashes, keep/discard
ledger, failure markers, and confirmation outcomes are saved under the run folder.
A process lock prevents concurrent execution of the same run. Changed evaluator
hashes are rejected. Completed calls are not repeated. A pending call after an
interruption requires inspection of Modal and saved artifacts before a retry;
the program deliberately refuses to infer that an interrupted paid call did not run.

This is a complete bounded **parameter-search execution loop**, not arbitrary
LLM-generated source-code evolution, a learned revision policy, or HRM transfer.
The proposer and hypothesis space are fixed in the frozen orchestrator. A broader
code-editing agent still requires an isolated candidate execution interface and
a proposal model; it must be compared against this restricted baseline. Equal
Adam steps do not mean equal wall time or equal SLSQP evaluations. Fresh starts
on one problem do not establish generalization to different mathematical problems.
Synthetic orchestration tests cover acceptance/rejection, frozen confirmation,
resume without repeated calls, invalid geometry, evaluator changes, and failures.


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
