"""Sequential semantics, delayed credit, leakage, geometry and resource contracts."""

from copy import deepcopy
import json

import numpy as np
import pytest

from scripts import sequential_controller as sc
from scripts.matched_revision import Protocol, initialize, advance
from scripts.revision_hypotheses import RECIPES
from dataclasses import replace


def worker(x, iterations, budget):
    x = x.copy()
    x[2::3] = 0
    return x, {"function_evaluations": min(2, budget)}


def test_repeated_actions_preserve_incumbent_and_exact_budget():
    p = Protocol(circles=3, windows=4, evaluations_per_window=3)
    initial = initialize(45, p)
    state = initial
    for action in ["local", "moderate", "restart", "local"]:
        state, _ = sc.step(state, action, p, worker)
    assert state.revisions == 3
    assert state.evaluations == 12
    assert state.score == initial.score
    np.testing.assert_array_equal(state.incumbent, initial.incumbent)
    assert initial.window == 0
    with pytest.raises(ValueError, match="terminal"):
        sc.step(state, "local", p, worker)


def test_old_fixed_moderate_schedule_is_identical():
    p = Protocol(circles=3, windows=3, evaluations_per_window=3, iterations_per_call=2)
    old, new = initialize(16, p), initialize(16, p)
    for t in range(3):
        old, _ = advance(
            old,
            "REVISE" if t == 1 else "KEEP",
            replace(p, revised_std=RECIPES["moderate"]),
        )
        new, _ = sc.step(new, "local" if t == 0 else "moderate", p)
    np.testing.assert_array_equal(old.incumbent, new.incumbent)
    assert old.score == new.score


def test_infeasible_and_over_budget_results_rejected():
    p = Protocol(circles=3)

    def bad_geometry(x, i, b):
        x[2::3] = 1
        return x, {"function_evaluations": b}

    with pytest.raises(ValueError, match="Infeasible"):
        sc.step(initialize(1, p), "restart", p, bad_geometry)
    with pytest.raises(ValueError, match="cap"):
        sc.step(
            initialize(1, p),
            "local",
            p,
            lambda x, i, b: (x, {"function_evaluations": b + 1}),
        )


def test_training_branches_and_causal_observations():
    p = Protocol(circles=3, windows=3, evaluations_per_window=3)
    data = sc.collect(4, p, worker)
    sc.validate_training(data, 4, p)
    assert data["objective_evaluations"] == 27
    for window in data["windows"]:
        assert len(window["branches"]) == 3
        assert len({tuple(b["x"]) for b in window["branches"]}) == 1
    broken = deepcopy(data)
    broken["windows"][0]["branches"][0]["x"][1] += 1
    with pytest.raises(ValueError, match="Noncausal"):
        sc.validate_training(broken, 4, p)
    broken = deepcopy(data)
    broken["windows"][1]["branches"][0]["reward"] += 1
    with pytest.raises(ValueError, match="reward"):
        sc.validate_training(broken, 4, p)


@pytest.mark.parametrize("kind", ["ridge", "tree"])
def test_json_model_predictions_match_sklearn(kind):
    from sklearn.linear_model import Ridge
    from sklearn.preprocessing import StandardScaler
    from sklearn.ensemble import ExtraTreesRegressor

    rng = np.random.default_rng(15)
    x = rng.normal(size=(100, 16))
    y = x[:, 0] ** 2 + x[:, 1] * x[:, 2]
    model = json.loads(json.dumps(sc.regress(x, y, kind), allow_nan=False))
    test = rng.normal(size=(30, 16))
    if kind == "ridge":
        scaler = StandardScaler().fit(x)
        expected = (
            Ridge(alpha=10, solver="svd")
            .fit(scaler.transform(x), y)
            .predict(scaler.transform(test))
        )
    else:
        expected = (
            ExtraTreesRegressor(
                n_estimators=64,
                max_depth=5,
                min_samples_leaf=8,
                random_state=731,
                n_jobs=1,
            )
            .fit(x, y)
            .predict(test)
        )
    np.testing.assert_allclose(
        sc.predict(model, test), expected, rtol=1e-12, atol=1e-12
    )


def test_backward_credit_changes_choice_on_delayed_reward_fixture(monkeypatch):
    # Abstract three-step MDP, deliberately independent of the packing verifier.
    # Local pays 1 now. Restart moves to a state paying 2 at the next step.
    monkeypatch.setattr(sc, "validate_training", lambda *args: None)
    p = Protocol(circles=3, windows=3)
    data = []
    for seed in range(96):
        windows = []
        for t in range(3):
            x = [float(seed % 3) if t == 1 else 0.0] + [0.0] * 15
            branches = []
            for a in range(3):
                reward = (
                    float(a == 0) if t == 0 else float(x[0] == 2) * 2 if t == 1 else 0.0
                )
                branches.append(
                    dict(
                        x=x,
                        reward=reward,
                        next_x=[float(a) if t == 0 else 0.0] + [0.0] * 15,
                    )
                )
            windows.append(dict(branches=branches))
        data.append(dict(seed=seed, windows=windows))
    fitted = sc.fit(data, p)
    for kind in ("ridge", "tree"):
        for horizon, expected in (("myopic", 0), ("sequential", 2)):
            heads = fitted["models"][kind + "_" + horizon]
            assert (
                np.argmax([sc.predict(m, np.zeros(16))[0] for m in heads[0]])
                == expected
            )
            np.testing.assert_allclose(
                [sc.predict(m, np.zeros(16))[0] for m in heads[2]], 0
            )


def test_confirmation_rollout_checks_and_overlap():
    p = Protocol(circles=3, windows=3, evaluations_per_window=2)
    bundle = dict(training_seeds=[1])
    row = sc.rollout(2, "reactive", bundle, p, worker)
    sc.validate_rollout(row, 2, "reactive", p)
    row["decisions"][1]["observation"][1] += 1
    with pytest.raises(ValueError, match="observation"):
        sc.validate_rollout(row, 2, "reactive", p)
    with pytest.raises(ValueError, match="overlaps"):
        sc.rollout(1, "reactive", bundle, p, worker)
    with pytest.raises(ValueError, match="overlap"):
        sc.summarize([dict(seed=2)], dict(training_seeds=[], validation_seeds=[2]))


def test_failed_dispatch_not_retried_and_budget_bound(tmp_path):
    from scripts.modal_sequential_controller import execute

    spec = sc.specification()
    (tmp_path / "manifest.json").write_text(json.dumps(spec))
    calls = []

    def failed(jobs):
        calls.extend(jobs)
        raise RuntimeError("network failure")

    with pytest.raises(RuntimeError, match="network failure"):
        execute(tmp_path, failed)
    assert len(calls) == 4
    with pytest.raises(RuntimeError, match="pending"):
        execute(tmp_path, failed)
    assert len(calls) == 4
    cost = spec["cost"]
    bound = (
        cost["hard_function_calls"]
        * cost["timeout_seconds"]
        * cost["rate_USD_per_second"]
    )
    assert bound <= cost["maximum_function_execution_USD"] + 1e-12
    assert bound + cost["reserve_USD"] + cost["previous_workspace_USD"] < 10
    assert not (tmp_path / "dispatch.lock").exists()
