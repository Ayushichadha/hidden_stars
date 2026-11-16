"""Compare archived memorization predictions with input copying; no inference."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def encode(lines):
    mapping = {str(i): i + 2 for i in range(10)}
    mapping.update({".": 0, "_": 0, "|": 1})
    return np.array([mapping[c] for line in lines for c in line], dtype=np.int32)


def diagnose(data, grids):
    ids = np.load(data / "all__puzzle_identifiers.npy", mmap_mode="r")
    indices = np.load(data / "all__puzzle_indices.npy", mmap_mode="r")
    inputs = np.load(data / "all__inputs.npy", mmap_mode="r")
    labels = np.load(data / "all__labels.npy", mmap_mode="r")
    rows = []
    for example, grid in enumerate(grids):
        target = encode(grid["target"])
        predicted = encode(grid["prediction"])
        candidates = []
        for puzzle in np.flatnonzero(ids == grid["puzzle_id"]):
            for row in range(int(indices[puzzle]), int(indices[puzzle + 1])):
                if np.array_equal(labels[row], target):
                    candidates.append(row)
        if len(candidates) != 1:
            raise ValueError(
                f"Expected unique archived target match, found {len(candidates)}"
            )
        row = candidates[0]
        mask = target != 0
        changed = mask & (inputs[row] != target)
        correct = predicted == target
        # Identical inputs under this same puzzle identifier must have one target.
        conflicting = []
        for puzzle in np.flatnonzero(ids == grid["puzzle_id"]):
            for other in range(int(indices[puzzle]), int(indices[puzzle + 1])):
                if np.array_equal(inputs[other], inputs[row]) and not np.array_equal(
                    labels[other], target
                ):
                    conflicting.append(other)
        rows.append(
            dict(
                saved_example=example,
                dataset_row=row,
                puzzle_id=grid["puzzle_id"],
                scored_tokens=int(mask.sum()),
                changed_tokens=int(changed.sum()),
                model_correct=int((correct & mask).sum()),
                copy_correct=int(((inputs[row] == target) & mask).sum()),
                model_correct_changed=int((correct & changed).sum()),
                prediction_equals_input_on_scored_tokens=bool(
                    np.array_equal(predicted[mask], inputs[row][mask])
                ),
                conflicting_same_input_rows=conflicting,
            )
        )
    total = sum(row["scored_tokens"] for row in rows)
    changes = sum(row["changed_tokens"] for row in rows)
    return dict(
        scope="Archived predictions matched to preprocessed training data; no fresh inference",
        examples=rows,
        model_token_accuracy=sum(row["model_correct"] for row in rows) / total,
        copy_token_accuracy=sum(row["copy_correct"] for row in rows) / total,
        changed_token_accuracy=(
            sum(row["model_correct_changed"] for row in rows) / changes
            if changes
            else None
        ),
        changed_tokens=changes,
        caveat="Input copying is an observed behavior, not an identified optimization or architecture defect.",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data", type=Path, default=ROOT / "HRM/data/conceptarc-mini/train"
    )
    parser.add_argument(
        "--grids", type=Path, default=ROOT / "outputs/hrm-memorization-grids.json"
    )
    args = parser.parse_args()
    result = diagnose(args.data, json.loads(args.grids.read_text()))
    result["artifact_hashes"] = {
        str(
            path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
        ): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in [args.grids]
        + [
            args.data / f"all__{name}.npy"
            for name in ("puzzle_identifiers", "puzzle_indices", "inputs", "labels")
        ]
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
