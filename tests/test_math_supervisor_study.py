import copy
import numpy as np
from scripts.run_math_supervisor_study import evaluate, predict


def test_prediction_uses_only_predecision_features():
    rows = [
        dict(
            seed=1,
            checkpoint=k,
            features=[k, 2.6, 0, 0.1, 0.01, 0.2, 0.5, 0.2],
            delta=0.01,
            outcomes={"local": 2.6, "broad": 2.61},
        )
        for k in range(3)
    ]
    normalization = dict(mean=[0] * 8, scale=[1] * 8, yscale=1)
    model = dict(kind="ridge", beta=[-1, 1, 0, 0, 0, 0, 0, 0, 0])
    before = predict(model, rows, normalization)
    changed = copy.deepcopy(rows)
    for row in changed:
        row["delta"] = -100
        row["outcomes"] = {"local": 100, "broad": 0}
    np.testing.assert_array_equal(before, predict(model, changed, normalization))


def test_clustered_evaluation_counts_trajectories():
    rows = [
        dict(
            seed=s,
            checkpoint=k,
            features=[k, 2.6, 0, 0.1, 0.01, 0.2, 0.5, 0.2],
            delta=0.01,
            outcomes={"local": 2.6, "broad": 2.61},
        )
        for s in (1, 2)
        for k in range(3)
    ]
    # Constant models make the expected paired difference exact.
    clock = dict(kind="clock", means=[-1] * 3)
    broad = dict(kind="clock", means=[1] * 3)
    models = dict(
        clock=clock,
        ridge=clock,
        neural=broad,
        normalization=dict(mean=[0] * 8, scale=[1] * 8, yscale=1),
    )
    result = evaluate(models, rows)
    assert result["trajectories"] == 2
    assert result["decisions"] == 6
    np.testing.assert_allclose(
        result["policies"]["neural"]["comparisons"]["clock"]["ci95"], [0.01, 0.01]
    )
