"""Numerical validity checks for the mathematical search feasibility pilot."""

import numpy as np
from scripts.check_math_packing import verify
from scripts.pilot_math_revision import constraints, constraint_jacobian, repair, solve
from scripts.run_math_search import action, episode


def test_constraint_derivatives():
    x = np.random.default_rng(7).uniform(0.01, 0.9, 18)
    h = 1e-6
    numeric = np.column_stack(
        [
            (constraints(x + h * e) - constraints(x - h * e)) / (2 * h)
            for e in np.eye(len(x))
        ]
    )
    np.testing.assert_allclose(constraint_jacobian(x), numeric, atol=1e-8)


def test_geometry_rejects_invalid_constructions():
    radii = np.array([0.1, 0.1])
    for centers in (
        np.array([[0.5, 0.5], [0.5, 0.5]]),
        np.array([[0.01, 0.01], [0.8, 0.8]]),
    ):
        assert not verify(centers, radii)["strictly_feasible"]


def test_repair_yields_feasible_construction():
    x = np.random.default_rng(7).uniform(0.01, 0.9, 18)
    z = repair(x).reshape(-1, 3)
    assert verify(z[:, :2], z[:, 2])["strictly_feasible"]


def test_search_policies_and_incumbent():
    assert action("stagnation2", 3, 1) == "local"
    assert action("stagnation2", 3, 2) == "broad"
    assert [action("fixed4", s, 0) for s in range(4)] == [
        "local",
        "local",
        "local",
        "broad",
    ]
    row, candidate = episode(19, 4, 3, 15, "stagnation2")
    scores = [item["best_score"] for item in row["trace"]]
    assert len(scores) == 4
    assert np.all(np.diff(scores) >= 0)
    z = candidate.reshape(-1, 3)
    assert verify(z[:, :2], z[:, 2])["strictly_feasible"]
    assert np.isclose(z[:, 2].sum(), row["score"])


def test_hard_evaluation_budget_and_reproducibility():
    for budget in (1, 7, 29):
        for policy in ("local", "stagnation2", "restart"):
            row, candidate = episode(79, 4, 1, 15, policy, budget)
            assert row["evaluations"] == budget
            assert sum(t["function_evaluations"] for t in row["trace"]) == budget
            assert np.all(np.diff([t["best_score"] for t in row["trace"]]) >= 0)
            z = candidate.reshape(-1, 3)
            assert verify(z[:, :2], z[:, 2])["strictly_feasible"]
    repeat, _ = episode(79, 4, 1, 15, "restart", 29)
    assert repeat["score"] == row["score"]


def test_solver_stops_at_one_evaluation():
    initial = repair(np.random.default_rng(12).uniform(0.01, 0.9, 18))
    candidate, metrics = solve(initial, 40, 1)
    assert metrics["function_evaluations"] == 1
    assert candidate[2::3].sum() >= repair(initial)[2::3].sum()
