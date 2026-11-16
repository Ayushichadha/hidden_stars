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
