# Repository-task pilot setup

Official mini-SWE-agent source inspected at commit
04d809ceab9df28f9adaed044884180159172930.
Temporary source checkout is /tmp/saint-mini-swe-agent.

The inspected DefaultAgent stores message history, model-call count, cost,
format-error count, template variables, and elapsed-time origin. Calling run()
resets message history. A restored branch must resume the step loop with explicit
state restoration rather than calling run() as if it preserved history.
Environment reconstruction must include tracked and untracked file changes.
Matching a Git diff alone does not establish equal execution state.

Single-issue upstream entry point is
minisweagent.run.benchmarks.swebench_single. Model and environment backends
are configurable. Pin the source revision and task/image identifiers in pilot
artifacts. Keep grading tests outside agent-visible observations.

Current local preflight found ARM64 macOS and no docker/podman executable.
Model provider, usable model identifier, and spending cap remain unresolved.
No repository issue has been run or graded. The user reports possible Meta API
access; verify the actual service before choosing a model adapter.

## Research positioning to resolve before scaling

A generic persist/replan controller already has direct precedents.
Executable Prefix Values estimates success from reconstructed SWE-bench states
and tests restart decisions. Fail-Fast, Restart-Smart predicts failure and
restarts with prior repository edits available as an optional overlay.
Accordingly, failure detection, state reconstruction, and retaining useful
edits are established nearby ideas.

The pilot should measure action-specific outcomes from identical states,
including continuation and a precisely defined replanning intervention.
Its initial purpose is feasibility and characterization. A distinct research
contribution requires comparison with the full methods of these papers.
The prior FeUdal work motivates persistent commitments; this coding-agent
interface uses explicit plans and a different worker.

Sources inspected:
- https://mini-swe-agent.com/latest/usage/swebench/
- https://arxiv.org/abs/2610.17633
- https://arxiv.org/abs/2608.03222
