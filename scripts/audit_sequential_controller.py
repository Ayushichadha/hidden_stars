"""Offline replay of saved sequential evidence; no fitting or cloud calls.

Reads the original and amended run directories. Validates data lineage, geometry,
resource counts, model predictions and reported statistics, then writes a receipt.
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from scripts.sequential_controller import (
    ACTIONS,
    LEARNED,
    STATIC,
    specification,
    validate_training,
    validate_rollout,
    predict,
    select_baseline,
    summarize,
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(output):
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    identity = digest(manifest_path)
    if manifest != specification():
        raise ValueError("Use the source version pinned by the manifest")
    if list(output.glob("*.pending")) or (output / "dispatch.lock").exists():
        raise ValueError("Run incomplete or still active")
    responses = {}

    def read(name):
        item = json.loads((output / (name + ".json")).read_text())
        if item["manifest_sha256"] != identity:
            raise ValueError("Artifact manifest mismatch")
        responses[name] = item["response"]
        return item["response"]["result"]

    imports = json.loads((output / "training-import.json").read_text())
    original = output.parent / "sequential-controller-v1"
    if digest(original / "manifest.json") != imports["original_manifest_sha256"]:
        raise ValueError("Original manifest mismatch")
    if identity != imports["amended_manifest_sha256"]:
        raise ValueError("Amendment mismatch")
    for seed in manifest["training_seeds"]:
        name = f"training-{seed}"
        before = json.loads((original / (name + ".json")).read_text())
        after = json.loads((output / (name + ".json")).read_text())
        expected = imports["original_artifacts"][name + ".json"]
        if (
            digest(original / (name + ".json")) != expected
            or after["original_artifact_sha256"] != expected
            or after["imported_from_manifest_sha256"] != before["manifest_sha256"]
            or before["manifest_sha256"] != imports["original_manifest_sha256"]
            or before["response"] != after["response"]
        ):
            raise ValueError("Imported training data changed")
        validate_training(read(name), seed)

    bundle, frozen = read("models"), read("frozen-policy")
    receipt = json.loads((output / "freeze-receipt.json").read_text())
    if receipt != dict(
        manifest_sha256=identity,
        models_sha256=digest(output / "models.json"),
        frozen_sha256=digest(output / "frozen-policy.json"),
    ):
        raise ValueError("Frozen policy or models changed")
    if (
        bundle["training_seeds"] != manifest["training_seeds"]
        or frozen["training_seeds"] != manifest["training_seeds"]
        or frozen["validation_seeds"] != manifest["validation_seeds"]
        or bundle["protocol"] != manifest["protocol"]
        or bundle["config"] != manifest["config"]
        or set(bundle["models"]) != set(LEARNED)
    ):
        raise ValueError("Model/split metadata mismatch")

    max_prediction_error = 0.0
    rows = {}
    rollout_count = 0
    for split in ("validation", "confirmation"):
        names = (
            list(STATIC)
            if split == "validation"
            else [*LEARNED, frozen["static"], "reactive"]
        )
        rows[split] = []
        for seed in manifest[split + "_seeds"]:
            row = read(f"{split}-{seed}")
            if row["seed"] != seed or set(row["policies"]) != set(names):
                raise ValueError("Rollout group mismatch")
            for name in names:
                rollout = row["policies"][name]
                validate_rollout(rollout, seed, name)
                rollout_count += 1
                if name in LEARNED:
                    for t, decision in enumerate(rollout["decisions"]):
                        q = [
                            float(predict(m, decision["observation"])[0])
                            for m in bundle["models"][name][t]
                        ]
                        err = float(
                            np.max(np.abs(np.array(q) - decision["q_milliscore"]))
                        )
                        max_prediction_error = max(max_prediction_error, err)
                        if not np.isfinite(err) or err > 1e-9:
                            raise ValueError("Logged values disagree with frozen model")
                        if (
                            rollout["trace"][t]["action"]
                            != ACTIONS[int(np.argmax(decision["q_milliscore"]))]
                        ):
                            raise ValueError("Action mismatch")
            rows[split].append(row)
    selected = select_baseline(rows["validation"])
    if selected["static"] != frozen["static"]:
        raise ValueError("Comparator not selected by frozen validation rule")
    report = read("summary")
    rebuilt = summarize(rows["confirmation"], frozen)

    # Floating-point aggregates can differ in the final bit across platforms.
    def equivalent(a, b):
        if isinstance(a, dict):
            return set(a) == set(b) and all(equivalent(a[k], b[k]) for k in a)
        if isinstance(a, list):
            return len(a) == len(b) and all(equivalent(x, y) for x, y in zip(a, b))
        if isinstance(a, float):
            return bool(np.isclose(a, b, rtol=0, atol=1e-12))
        return a == b

    if not equivalent(report, rebuilt):
        raise ValueError("Summary differs from raw paired rollouts")
    seconds = sum(r["function_seconds"] for r in responses.values())
    return dict(
        status="passed",
        cloud_calls_performed_by_audit=0,
        training_paths=len(manifest["training_seeds"]),
        training_transitions=2304,
        verified_evaluation_rollouts=rollout_count,
        unique_paid_calls=len(responses),
        max_model_prediction_error_milliscore=max_prediction_error,
        recorded_function_seconds=seconds,
        function_execution_estimate_USD=seconds
        * manifest["cost"]["rate_USD_per_second"],
        billing_caveat="Rate estimate excludes setup/idle/build/egress; not a refreshed invoice",
        manifest_sha256=identity,
        models_sha256=digest(output / "models.json"),
        summary_sha256=digest(output / "summary.json"),
        original_manifest_sha256=imports["original_manifest_sha256"],
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.output)
    (args.output / "audit-receipt.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
