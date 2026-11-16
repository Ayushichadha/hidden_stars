"""Synthetic archive checks; no HRM execution."""

import numpy as np
import pytest

from scripts.diagnose_hrm_copy_baseline import diagnose


def dataset(path, inputs, labels):
    for name, value in {
        "inputs": inputs,
        "labels": labels,
        "puzzle_identifiers": [7],
        "puzzle_indices": [0, len(inputs)],
    }.items():
        np.save(path / f"all__{name}.npy", np.array(value))


def test_identity_baseline_exposes_changed_token_failure(tmp_path):
    dataset(tmp_path, [[2, 3, 0]], [[2, 4, 0]])
    result = diagnose(tmp_path, [dict(puzzle_id=7, target=["02."], prediction=["01."])])
    assert result["copy_token_accuracy"] == 0.5
    assert result["model_token_accuracy"] == 0.5
    assert result["changed_token_accuracy"] == 0.0
    assert result["examples"][0]["prediction_equals_input_on_scored_tokens"]


def test_ambiguous_target_match_is_rejected(tmp_path):
    dataset(tmp_path, [[2, 3], [2, 4]], [[2, 4], [2, 4]])
    with pytest.raises(ValueError, match="unique"):
        diagnose(tmp_path, [dict(puzzle_id=7, target=["02"], prediction=["01"])])


def test_conflicting_input_labels_are_reported(tmp_path):
    dataset(tmp_path, [[2, 3], [2, 3]], [[2, 4], [2, 5]])
    result = diagnose(tmp_path, [dict(puzzle_id=7, target=["02"], prediction=["01"])])
    assert result["examples"][0]["conflicting_same_input_rows"] == [1]
