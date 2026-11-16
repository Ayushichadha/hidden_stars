"""CPU feasibility pilot: paired continue/perturb branches for circle packing.

This is a numerical search pilot, not an LLM agent or learned controller.
"""

import argparse
import json
import platform
import time
from pathlib import Path

import numpy as np
import scipy
from scipy.optimize import minimize

from scripts.check_math_packing import verify


def constraints(x):
    z = x.reshape(-1, 3)
    c, r = z[:, :2], z[:, 2]
    i, j = np.triu_indices(len(r), 1)
    return np.concatenate(
        (
            (c - r[:, None]).ravel(),
            (1 - c - r[:, None]).ravel(),
            ((c[i] - c[j]) ** 2).sum(axis=1) - (r[i] + r[j]) ** 2,
        )
    )


def constraint_jacobian(x):
    z = x.reshape(-1, 3)
    n = len(z)
    i, j = np.triu_indices(n, 1)
    jac = np.zeros((4 * n + len(i), 3 * n))
    for k in range(n):
        for d in range(2):
            jac[2 * k + d, 3 * k + d] = 1
            jac[2 * k + d, 3 * k + 2] = -1
            jac[2 * n + 2 * k + d, 3 * k + d] = -1
            jac[2 * n + 2 * k + d, 3 * k + 2] = -1
    rows = 4 * n + np.arange(len(i))
    for d in range(2):
        delta = 2 * (z[i, d] - z[j, d])
        jac[rows, 3 * i + d] = delta
        jac[rows, 3 * j + d] = -delta
    jac[rows, 3 * i + 2] = -2 * (z[i, 2] + z[j, 2])
    jac[rows, 3 * j + 2] = -2 * (z[i, 2] + z[j, 2])
    return jac


def repair(x):
    """Conservatively scale radii to obtain a numerically feasible candidate."""
    z = x.reshape(-1, 3).copy()
    z[:, :2] = np.clip(z[:, :2], 1e-10, 1 - 1e-10)
    z[:, 2] = np.maximum(z[:, 2], 1e-12)
    c, r = z[:, :2], z[:, 2]
    i, j = np.triu_indices(len(r), 1)
    factor = min(
        1.0,
        float((np.minimum(c, 1 - c) / r[:, None]).min()),
        float((np.linalg.norm(c[i] - c[j], axis=1) / (r[i] + r[j])).min()),
    )
    z[:, 2] *= max(0.0, factor * (1 - 1e-9))
    return z.ravel()


def solve(x, iterations, evaluation_budget=None):
    if evaluation_budget is not None:
        return solve_budgeted(x, iterations, evaluation_budget)
    gradient = np.zeros_like(x)
    gradient[2::3] = -1
    start = time.perf_counter()
    result = minimize(
        lambda v: -v[2::3].sum(),
        x,
        jac=lambda v: gradient,
        method="SLSQP",
        bounds=[(0, 1), (0, 1), (0, 0.5)] * (len(x) // 3),
        constraints={"type": "ineq", "fun": constraints, "jac": constraint_jacobian},
        options={"maxiter": iterations, "ftol": 1e-10},
    )
    elapsed = time.perf_counter() - start
    candidate = repair(result.x)
    checked = verify(candidate.reshape(-1, 3)[:, :2], candidate[2::3])
    if not checked["strictly_feasible"]:
        raise RuntimeError("Repaired candidate failed independent geometry check")
    return candidate, dict(
        **checked,
        seconds=elapsed,
        iterations=int(result.nit),
        function_evaluations=int(result.nfev),
        solver_success=bool(result.success),
        solver_message=str(result.message),
        raw_score=float(result.x[2::3].sum()),
    )


def solve_budgeted(x, iterations, budget):
    """Hard objective-call cap; retain feasible repairs of evaluated candidates.

    Objective calls are a reproducible work proxy, not equal FLOPs or wall time.
    Constraint and derivative calls are counted separately.
    """
    if budget < 1:
        raise ValueError("Budget must be positive")
    counts = dict(objective=0, constraint=0, derivative=0, iterations=0)
    best = repair(x)
    raw_score = float(x[2::3].sum())
    gradient = np.zeros_like(x)
    gradient[2::3] = -1

    class BudgetExhausted(Exception):
        pass

    def objective(v):
        nonlocal best, raw_score
        if counts["objective"] >= budget:
            raise BudgetExhausted
        counts["objective"] += 1
        raw_score = float(v[2::3].sum())
        candidate = repair(v)
        if candidate[2::3].sum() > best[2::3].sum():
            best = candidate
        return -raw_score

    def constraint(v):
        counts["constraint"] += 1
        return constraints(v)

    def derivative(v):
        counts["derivative"] += 1
        return constraint_jacobian(v)

    def callback(v):
        counts["iterations"] += 1

    start = time.perf_counter()
    try:
        result = minimize(
            objective,
            x,
            jac=lambda v: gradient,
            method="SLSQP",
            bounds=[(0, 1), (0, 1), (0, 0.5)] * (len(x) // 3),
            constraints={"type": "ineq", "fun": constraint, "jac": derivative},
            callback=callback,
            options={"maxiter": iterations, "ftol": 1e-10},
        )
        success, message = bool(result.success), str(result.message)
    except BudgetExhausted:
        success, message = False, "Objective evaluation budget exhausted"
    checked = verify(best.reshape(-1, 3)[:, :2], best[2::3])
    if not checked["strictly_feasible"]:
        raise RuntimeError("Budgeted candidate failed geometry check")
    return best, dict(
        **checked,
        seconds=time.perf_counter() - start,
        iterations=counts["iterations"],
        function_evaluations=counts["objective"],
        constraint_evaluations=counts["constraint"],
        constraint_jacobians=counts["derivative"],
        solver_success=success,
        solver_message=message,
        raw_score=raw_score,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=8)
    parser.add_argument("--circles", type=int, default=26)
    parser.add_argument("--iterations", type=int, default=50)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if min(args.seeds, args.iterations) < 1 or args.circles < 2:
        parser.error("Need positive seeds/iterations and at least two circles")
    args.output.mkdir(parents=True, exist_ok=True)
    if (args.output / "results.json").exists():
        parser.error("Output already contains results; select a fresh directory")
    (args.output / "manifest.json").write_text(
        json.dumps(
            dict(
                seeds=args.seeds,
                circles=args.circles,
                iterations=args.iterations,
                perturbation_std=0.04,
                seed_base=2026111500,
                python=platform.python_version(),
                numpy=np.__version__,
                scipy=scipy.__version__,
                budget="equal iteration caps, not equal actual compute",
                continuation="fresh SLSQP invocation warm-started at checkpoint",
            ),
            indent=2,
        )
        + "\n"
    )
    rows = []
    for seed in range(args.seeds):
        rng = np.random.default_rng(2026111500 + seed)
        initial = np.column_stack(
            (rng.uniform(0.05, 0.95, (args.circles, 2)), np.full(args.circles, 0.01))
        ).ravel()
        checkpoint, initial_metrics = solve(repair(initial), args.iterations)
        continued, persist = solve(checkpoint, args.iterations)
        perturbed = checkpoint.reshape(-1, 3).copy()
        perturbed[:, :2] += rng.normal(0, 0.04, (args.circles, 2))
        revised, revise = solve(repair(perturbed.ravel()), args.iterations)
        # Both branches retain the identical valid checkpoint incumbent.
        for metrics in (persist, revise):
            metrics["best_score"] = max(
                initial_metrics["sum_radii"], metrics["sum_radii"]
            )
        row = dict(
            seed=2026111500 + seed,
            checkpoint=initial_metrics,
            persist=persist,
            revise=revise,
            revise_minus_persist=revise["best_score"] - persist["best_score"],
        )
        rows.append(row)
        np.savez(
            args.output / f"seed-{seed}.npz",
            checkpoint=checkpoint,
            persist=continued,
            revise=revised,
        )
        (args.output / "results.json").write_text(json.dumps(rows, indent=2) + "\n")
        print(json.dumps(row), flush=True)


if __name__ == "__main__":
    main()
