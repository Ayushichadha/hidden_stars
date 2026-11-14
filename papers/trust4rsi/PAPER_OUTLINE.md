# Working manuscript argument

## Question

Can execution feedback improve when a supervisor revises a persistent
commitment, beyond elapsed time, under the same tool-call budget?

## Proposed abstract content

We study revision timing in a stateful record-transfer environment with real
SQLite execution and synthetic service failures. Supervisors decide whether to
retain a primary service or switch once to a backup, paying a restoration call.
Matched endpoint-trained supervisors use either elapsed time alone or time
with observed execution history. Across three frozen evaluations totaling
9,000 workflows, state-aware control improves completion over learned timing
by 1.90–3.63 percentage points. Its advantage over a validation-selected
failure-streak rule is inconsistent, and it loses completion on persistent
outages while improving stable and transient cases. A separate latent-goal
worker study shows that causal goal influence does not by itself guarantee
useful revision control. These findings motivate evaluating revision through
paired terminal outcomes and condition-specific harms alongside average gains.

## Sections and evidence

1. Metareasoning question and persistent commitments. Connect Russell/Wefald
   and Hay to downstream utility and the computation budget.
2. Explicit service-choice testbed, observations, restoration semantics, and
   endpoint verification. State the synthetic fault model and scope.
3. Matched time/state training, fixed and reactive controls. Discuss Honda
   and Xu as direct precedents and distinguish our fitted stopping method.
4. Frozen evaluation and paired results from EXPLICIT_PROTOCOL.md. Lead with
   the learned-time comparison and include the reactive subgroup losses.
5. Latent-goal extension and HRM historical diagnostic, scoped to their evidence.
6. Limitations: hand-designed environment, few training seeds, unknown broader
   transfer, additional policy computation, and limited evidence for latent goals.

The manuscript must distinguish a proposed contribution from established
novelty. Full related-work positioning and the submission-ready PDF are pending.
