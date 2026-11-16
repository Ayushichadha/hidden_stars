"""Leakage, causal stopping, and terminal evaluation contract tests."""

from copy import deepcopy

import numpy as np
import pytest

from scripts.predict_revision import features, choose, train, evaluate, samples


def episode(seed):
    trace = [
        dict(score_before=1 + t * 0.01, score_after=1 + (t + 1) * 0.01)
        for t in range(8)
    ]
    return [
        dict(
            seed=seed,
            revision_before_window=t,
            score=2 + (0 if t is None else t * 0.001),
            trace=deepcopy(trace),
        )
        for t in [None, *range(1, 8)]
    ]


def test_features_never_read_future_or_terminal_labels():
    rows = episode(1)
    prefix = features(rows[0]["trace"], 3, True)
    rows[0]["trace"][3:] = [{"unavailable": True}] * 5
    assert features(rows[0]["trace"], 3, True) == prefix
    assert len(features(rows[0]["trace"], 3, False)) == 7


def test_mandatory_final_revision_and_causal_trigger():
    trace = episode(1)[0]["trace"]
    assert choose(trace, dict(kind="reactive", patience=2)) == 7
    trace[0]["score_after"] = trace[0]["score_before"]
    assert choose(trace, dict(kind="reactive", patience=1)) == 1
    assert choose(trace, dict(kind="fixed", timing=4)) == 4


def test_target_is_terminal_now_minus_future_mean():
    x, y = samples([episode(1)], False)
    assert x.shape == (6, 7)
    np.testing.assert_allclose(
        y[0], 2.001 - np.mean([2 + t * 0.001 for t in range(2, 8)])
    )


def test_train_freezes_then_evaluate_without_mutation():
    frozen = train([episode(i) for i in range(3)], [episode(4)])
    before = deepcopy(frozen)
    report = evaluate([episode(5), episode(6)], frozen)
    assert frozen == before
    assert frozen["policies"]["fixed"]["timing"] == 7
    assert report["mean_scores"]["fixed"] == 2.007
    assert not report["primary_success"]
    assert report["primary_state_minus_time"]["mean"] == 0


def test_overlapping_splits_rejected():
    with pytest.raises(ValueError, match="overlap"):
        train([episode(1)], [episode(1)])


def test_confirmation_labels_cannot_change_policy_choices():
    frozen = train([episode(1), episode(2)], [episode(3)])
    heldout = [episode(4), episode(5)]
    original = evaluate(heldout, frozen)
    for rows in heldout:
        for row in rows:
            row["score"] = 100 - row["score"]
    changed = evaluate(heldout, frozen)
    assert original["timings"] == changed["timings"]
    assert original["mean_scores"] != changed["mean_scores"]
    with pytest.raises(ValueError, match="overlap"):
        evaluate([episode(1)], frozen)
