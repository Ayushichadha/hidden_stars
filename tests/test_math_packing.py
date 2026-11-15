"""Numerical validity checks for the mathematical search feasibility pilot."""

import numpy as np
from scripts.check_math_packing import verify
from scripts.pilot_math_revision import constraints, constraint_jacobian, repair


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
