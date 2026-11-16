"""Development comparison of sustained circle-packing search policies."""

import argparse
import json
import platform
from pathlib import Path

import numpy as np
import scipy

from scripts.pilot_math_revision import repair, solve


POLICIES = ("local", "broad", "alternate", "fixed4", "stagnation2", "restart")


def action(policy, step, failures):
    if policy == "stagnation2":
        return "broad" if failures >= 2 else "local"
    if policy == "alternate":
        return "broad" if step % 2 else "local"
    if policy == "fixed4":
        return "broad" if (step + 1) % 4 == 0 else "local"
    return policy


def episode(seed, n, calls, iterations, policy, evaluation_budget=None):
    rng = np.random.default_rng(seed)
    initial = np.column_stack(
        (rng.uniform(0.05, 0.95, (n, 2)), np.full(n, 0.01))
    ).ravel()
    incumbent, metrics = solve(repair(initial), iterations, evaluation_budget)
    used = metrics["function_evaluations"]
    score = metrics["sum_radii"]
    trace = [dict(step=-1, action="initialize", best_score=score, **metrics)]
    failures = 0
    step = 0
    while used < evaluation_budget if evaluation_budget is not None else step < calls:
        # Counter-based random draws align noise across policies without using outcomes.
        rng = np.random.default_rng(np.random.SeedSequence([seed, step, 913]))
        selected = action(policy, step, failures)
        candidate = incumbent.reshape(n, 3).copy()
        if selected == "restart":
            candidate[:, :2] = rng.uniform(0.05, 0.95, (n, 2))
            candidate[:, 2] = 0.01
        else:
            candidate[:, :2] += rng.normal(
                0, 0.015 if selected == "local" else 0.12, (n, 2)
            )
        remaining = None if evaluation_budget is None else evaluation_budget - used
        candidate, metrics = solve(repair(candidate.ravel()), iterations, remaining)
        used += metrics["function_evaluations"]
        gain = metrics["sum_radii"] - score
        if gain > 0:
            incumbent, score = candidate, metrics["sum_radii"]
        failures = 0 if gain > 1e-7 else failures + 1
        trace.append(
            dict(
                step=step,
                action=selected,
                best_score=score,
                improvement=max(0.0, gain),
                **metrics,
            )
        )
        step += 1
    return (
        dict(
            seed=seed,
            policy=policy,
            circles=n,
            score=score,
            seconds=sum(t["seconds"] for t in trace),
            evaluations=sum(t["function_evaluations"] for t in trace),
            constraint_evaluations=(
                sum(t.get("constraint_evaluations", 0) for t in trace)
                if evaluation_budget is not None
                else None
            ),
            constraint_jacobians=(
                sum(t.get("constraint_jacobians", 0) for t in trace)
                if evaluation_budget is not None
                else None
            ),
            trace=trace,
        ),
        incumbent,
    )


def summarize(rows):
    summary = {}
    baseline = {r["seed"]: r["score"] for r in rows if r["policy"] == "local"}
    for policy in POLICIES:
        selected = [r for r in rows if r["policy"] == policy]
        differences = np.array([r["score"] - baseline[r["seed"]] for r in selected])
        rng = np.random.default_rng(193)
        bootstrap = rng.choice(
            differences, (10000, len(differences)), replace=True
        ).mean(axis=1)
        summary[policy] = dict(
            mean_score=float(np.mean([r["score"] for r in selected])),
            mean_seconds=float(np.mean([r["seconds"] for r in selected])),
            mean_evaluations=float(np.mean([r["evaluations"] for r in selected])),
            difference_vs_local=float(differences.mean()),
            descriptive_paired_95_interval=np.quantile(
                bootstrap, [0.025, 0.975]
            ).tolist(),
        )
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=12)
    parser.add_argument("--seed-base", type=int, default=2026111510)
    parser.add_argument("--circles", type=int, default=26)
    parser.add_argument("--calls", type=int, default=12)
    parser.add_argument("--iterations", type=int, default=40)
    parser.add_argument("--evaluation-budget", type=int)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if min(args.seeds, args.calls, args.iterations) < 1 or args.circles < 2:
        parser.error("Invalid experiment size")
    if args.evaluation_budget is not None and args.evaluation_budget < 1:
        parser.error("Evaluation budget must be positive")
    args.output.mkdir(parents=True, exist_ok=False)
    manifest = dict(
        vars(args),
        output=str(args.output),
        python=platform.python_version(),
        numpy=np.__version__,
        scipy=scipy.__version__,
        status="development",
        budget=(
            "hard objective evaluation cap including initialization; calls unrestricted"
            if args.evaluation_budget is not None
            else "equal solver-call counts and iteration caps; actual compute differs"
        ),
        candidate_retention=(
            "best repaired evaluated candidate"
            if args.evaluation_budget
            else "repaired final optimizer candidate"
        ),
        policies=POLICIES,
        local_std=0.015,
        broad_std=0.12,
    )
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    rows = []
    for index in range(args.seeds):
        # Rotate execution order to reduce systematic timing-order bias.
        for offset in range(len(POLICIES)):
            policy = POLICIES[(offset + index) % len(POLICIES)]
            row, incumbent = episode(
                args.seed_base + index,
                args.circles,
                args.calls,
                args.iterations,
                policy,
                args.evaluation_budget,
            )
            rows.append(row)
            with (args.output / "traces.jsonl").open("a") as f:
                f.write(json.dumps(row) + "\n")
            np.save(args.output / f"{row['seed']}-{policy}.npy", incumbent)
        print(f"Completed seed {index+1}/{args.seeds}", flush=True)
    summary = summarize(rows)
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
