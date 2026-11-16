"""Geometry invariance, branch matching, causal features and paired testing."""

from copy import deepcopy
import numpy as np
import pytest
from scripts.matched_revision import Protocol
from scripts.revision_hypotheses import (
    geometry,
    collect,
    validate,
    feature,
    choose,
    train,
    evaluate,
    contrast,
    RECIPES,
)


def worker(x, iterations, budget):
    x = x.copy()
    x[2::3] = 0
    return x, {"function_evaluations": budget}


def test_geometry_is_permutation_invariant_and_finite():
    z = np.array([[0.2, 0.2, 0.1], [0.8, 0.2, 0.05], [0.5, 0.8, 0.08]])
    np.testing.assert_allclose(geometry(z), geometry(z[[2, 0, 1]]))
    assert len(geometry(z)) == 7
    assert RECIPES["moderate"] == np.sqrt(0.015 * 0.12)


def test_families_share_prefix_and_equal_budgets():
    p = Protocol(circles=3, windows=3, evaluations_per_window=2)
    data = collect(7, p, worker)
    validate(data, 7, p)
    assert data["families"]["broad"][0] == data["families"]["moderate"][0]
    for family in data["families"].values():
        assert all(r["evaluations"] == 6 for r in family)
        assert all(r["emissions"] == 2 for r in family[1:])
        assert family[1]["trace"][0] == family[0]["trace"][0]


def episode(seed):
    return collect(seed, Protocol(circles=3, evaluations_per_window=1), worker)


def test_geometry_features_only_read_consumed_prefix():
    rows = episode(8)["families"]["broad"]
    trace = rows[0]["trace"]
    x = feature(trace, 2, "geometry")
    trace[2:] = [{"future": "forbidden"}] * 6
    assert feature(trace, 2, "geometry") == x
    assert choose(trace, dict(kind="fixed", timing=3)) == 3


def test_frozen_policies_and_confirmation_label_independence():
    frozen = train([episode(8), episode(9)], [episode(10)])
    snapshot = deepcopy(frozen)
    heldout = [episode(11), episode(12)]
    first = evaluate(heldout, frozen)
    assert not first["H1_geometry_vs_progress_broad"]["success"]
    for e in heldout:
        for rows in e["families"].values():
            for r in rows:
                r["score"] += 1
    assert evaluate(heldout, frozen)["timings"] == first["timings"]
    assert frozen == snapshot
    with pytest.raises(ValueError, match="overlap"):
        evaluate([episode(8)], frozen)


def test_adjusted_interval_and_practical_threshold():
    assert contrast(np.ones(10) * 0.001, np.zeros(10))["success"]
    assert not contrast(np.ones(10) * 0.0001, np.zeros(10))["success"]
    assert contrast(np.ones(10), np.ones(10))["paired_seed_97_5_interval"] == [0, 0]


def test_tiny_numerical_geometry_collection():
    p = Protocol(circles=3, windows=3, evaluations_per_window=2, iterations_per_call=2)
    data = collect(14, p)
    validate(data, 14, p)


def test_failed_batch_remains_pending_without_retry(tmp_path):
    from scripts.revision_hypotheses import prepare
    from scripts.modal_revision_hypotheses import execute

    output = tmp_path / "run"
    prepare(output)
    calls = []

    def failed_batch(seeds, sources):
        calls.append(list(seeds))
        raise RuntimeError("remote failed")

    with pytest.raises(RuntimeError, match="remote failed"):
        execute(output, failed_batch, None)
    assert len(calls) == 1 and len(calls[0]) == 4
    assert len(list(output.glob("*.pending"))) == 4
    assert not (output / "dispatch.lock").exists()
    with pytest.raises(RuntimeError, match="pending"):
        execute(output, failed_batch, None)
    assert len(calls) == 1
