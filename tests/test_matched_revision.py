"""Contract checks with fake workers plus one tiny numerical integration check."""

from dataclasses import replace
import json

import numpy as np
import pytest

from scripts.matched_revision import (
    Commitment,
    Protocol,
    advance,
    collect,
    initialize,
    prepare,
    summarize,
)


def fake_solver(candidate, iterations, budget):
    # Deliberately return a worse feasible solution: incumbent must survive.
    candidate = candidate.copy()
    candidate[2::3] = 0
    return candidate, {"function_evaluations": min(2, budget)}


def test_frozen_commitment_and_no_mutation():
    p = Protocol(circles=3, windows=4, evaluations_per_window=3)
    initial = initialize(42, p)
    with pytest.raises(ValueError):
        advance(initial, "REVISE", p, fake_solver)
    state, _ = advance(initial, "KEEP", p, fake_solver)
    revised, event = advance(state, "REVISE", p, fake_solver)
    assert initial.window == 0 and state.commitment == Commitment()
    assert revised.commitment == Commitment("broad", 1)
    assert event["commitment"]["recipe"] == "broad"
    kept, _ = advance(revised, "KEEP", p, fake_solver)
    assert kept.commitment == revised.commitment
    assert kept.score == initial.score
    assert kept.evaluations == 9
    np.testing.assert_array_equal(initial.incumbent, kept.incumbent)
    kept.incumbent[:] = 0
    assert initial.incumbent.sum() > 0
    with pytest.raises(ValueError):
        advance(revised, "REVISE", p, fake_solver)


def test_every_timing_matches_prefix_budget_and_count():
    p = Protocol(circles=3, windows=4, evaluations_per_window=5)
    rows = collect(11, p, fake_solver)
    assert len(rows) == 4
    for row in rows:
        assert row["evaluations"] == 20
        assert row["emissions"] == (1 if row["revision_before_window"] is None else 2)
        timing = row["revision_before_window"]
        if timing is not None:
            assert row["trace"][:timing] == rows[0]["trace"][:timing]
            assert sum(t["action"] == "REVISE" for t in row["trace"]) == 1
            assert all(
                t["commitment"]["recipe"] == "broad" for t in row["trace"][timing:]
            )
    report = summarize(rows)
    assert report["oracle_minus_best_fixed"] == 0
    assert report["development_selected_fixed_timing"] == 1


def test_common_random_numbers_and_independent_verification():
    p = Protocol(circles=3, windows=3, evaluations_per_window=1)
    state, _ = advance(initialize(22, p), "KEEP", p, fake_solver)
    # Identical recipes force identical draws even with different emission labels.
    q = replace(p, revised_std=p.local_std * 2)
    captured = []

    def record(candidate, iterations, budget):
        captured.append(candidate.copy())
        return fake_solver(candidate, iterations, budget)

    advance(state.clone(), "KEEP", q, record)
    advance(state.clone(), "KEEP", q, record)
    np.testing.assert_array_equal(*captured)

    def invalid(candidate, iterations, budget):
        candidate[:] = np.nan
        return candidate, {"function_evaluations": budget}

    with pytest.raises(ValueError, match="Nonfinite"):
        advance(state, "KEEP", p, invalid)
    with pytest.raises(ValueError, match="budget"):
        advance(state, "KEEP", p, lambda x, i, b: (x, {"function_evaluations": b + 1}))


def test_tiny_solver_integration_and_replay():
    p = Protocol(circles=3, windows=3, evaluations_per_window=4, iterations_per_call=3)
    first = collect(5, p)
    second = collect(5, p)
    assert [r["score"] for r in first] == [r["score"] for r in second]
    for row in first:
        assert row["evaluations"] == 12
        assert np.all(np.diff([t["score_after"] for t in row["trace"]]) >= 0)


def test_prepare_is_offline_and_refuses_overwrite(tmp_path):
    output = tmp_path / "run"
    manifest = prepare(output, Protocol(), [12, 13])
    assert json.loads((output / "manifest.json").read_text()) == manifest
    assert list(output.iterdir()) == [output / "manifest.json"]
    with pytest.raises(FileExistsError):
        prepare(output, Protocol(), [12, 13])


def test_dispatch_resume_and_pending_fail_closed(tmp_path):
    from scripts.modal_matched_revision import execute

    output = tmp_path / "run"
    prepare(output, Protocol(), [12])
    calls = []

    def remote(config, seed, hashes):
        calls.append(seed)
        return {"rows": collect(seed, Protocol(**config), fake_solver)}

    execute(output, remote)
    execute(output, remote)
    assert calls == [12]
    (output / "seed-12.pending").write_text("interrupted")
    with pytest.raises(RuntimeError, match="Pending"):
        execute(output, remote)
    assert not (output / "dispatch.lock").exists()


def test_dispatch_failure_does_not_retry(tmp_path):
    from scripts.modal_matched_revision import execute

    output = tmp_path / "run"
    prepare(output, Protocol(), [12])

    def failure(*args):
        raise RuntimeError("remote failed")

    with pytest.raises(RuntimeError, match="remote failed"):
        execute(output, failure)
    assert (output / "seed-12.pending").exists()
    with pytest.raises(RuntimeError, match="Pending"):
        execute(output, failure)


def test_opportunity_is_oracle_not_best_fixed():
    rows = []
    for seed, scores in ((1, (1.0, 3.0, 1.0)), (2, (1.0, 1.0, 3.0))):
        for timing, score in zip((None, 1, 2), scores):
            rows.append(
                dict(
                    seed=seed,
                    score=score,
                    revision_before_window=timing,
                    group="never_revise" if timing is None else "exact_one_replacement",
                )
            )
    report = summarize(rows)
    assert report["oracle_minus_best_fixed"] == 1.0
    assert report["best_fixed_minus_never"] == 1.0
    assert report["per_seed_best_timing"] == [1, 2]


def test_returned_geometry_and_causal_trace_are_replayed():
    from scripts.matched_revision import validate_rows

    p = Protocol(circles=3, windows=3, evaluations_per_window=2)
    rows = collect(15, p, fake_solver)
    validate_rows(rows, 15, p)
    rows[1]["emissions"] = 1
    with pytest.raises(ValueError, match="budget mismatch"):
        validate_rows(rows, 15, p)
    rows[1]["emissions"] = 2
    rows[1]["construction"][0][2] = 2
    with pytest.raises(ValueError, match="geometry"):
        validate_rows(rows, 15, p)
