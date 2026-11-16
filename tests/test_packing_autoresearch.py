"""Synthetic orchestration tests; no optimizer or Modal execution."""

import json
import pytest
from scripts.run_packing_autoresearch import hashes, run, save, score


def report(seed, radius):
    points = [[0.1 + 0.15 * (i % 6), 0.1 + 0.15 * (i // 6), radius] for i in range(26)]
    return dict(
        seed=seed,
        starts=32,
        steps_per_schedule=2000,
        results=[dict(constructions=[points] * 32)],
    )


def prepare(tmp_path):
    save(
        tmp_path / "state.json",
        dict(
            hashes=hashes(),
            history=[],
            pending=None,
            development_seed=1,
            confirmation_seed=2,
        ),
    )


def test_keep_discard_confirmation_and_resume(tmp_path):
    prepare(tmp_path)
    calls = []

    def evaluate(candidate, seed):
        calls.append((candidate, seed))
        return report(seed, [0.01, 0.02, 0.015, 0.018, 0.01, 0.019][len(calls) - 1])

    result = run(tmp_path, evaluate)
    assert [r["status"] for r in result["history"]] == [
        "keep",
        "keep",
        "discard",
        "discard",
    ]
    assert len(calls) == 6
    assert calls[-1][0]["schedule"] == "linear10to1000"
    assert result["confirmation"]["mean_difference"] > 0
    run(tmp_path, evaluate)
    assert len(calls) == 6


def test_failed_call_is_not_silently_retried(tmp_path):
    prepare(tmp_path)

    def fail(*args):
        raise ConnectionError("simulated failure")

    with pytest.raises(ConnectionError):
        run(tmp_path, fail)
    with pytest.raises(RuntimeError, match="Uncertain"):
        run(tmp_path, fail)
    assert json.loads((tmp_path / "state.json").read_text())["pending"]


def test_invalid_geometry_and_changed_evaluator_rejected(tmp_path):
    with pytest.raises(ValueError, match="geometry"):
        score(report(1, 0.2), 1)
    prepare(tmp_path)
    path = tmp_path / "state.json"
    state = json.loads(path.read_text())
    state["hashes"] = {}
    save(path, state)
    with pytest.raises(RuntimeError, match="changed"):
        run(tmp_path, lambda *args: None)
