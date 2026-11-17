"""Bounded CPU-only sequential controller study, with fail-closed resume."""

import hashlib
import json
from pathlib import Path
import time

import modal

ROOT = Path(__file__).resolve().parent
# Rebuild from a source-free base: Modal disallows pip_install after local mounts.
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("numpy==2.2.6", "scipy==1.15.3", "scikit-learn==1.8.0")
    .env({"OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"})
)
for name in (
    "matched_revision.py",
    "pilot_math_revision.py",
    "check_math_packing.py",
    "modal_matched_revision.py",
    "predict_revision.py",
    "revision_hypotheses.py",
    "modal_revision_hypotheses.py",
    "sequential_controller.py",
    "modal_sequential_controller.py",
):
    image = image.add_local_file(ROOT / name, "/root/scripts/" + name)
app = modal.App("saint-sequential-controller")


@app.function(
    image=image,
    cpu=(1, 1),
    memory=(2048, 2048),
    timeout=600,
    max_containers=4,
    retries=0,
    scaledown_window=2,
)
def task(mode, payload, expected):
    import sys
    import platform
    import numpy
    import scipy
    import sklearn

    sys.path.insert(0, "/root")
    from scripts.sequential_controller import (
        hashes,
        collect,
        fit,
        rollout,
        select_baseline,
        summarize,
    )

    if hashes() != expected:
        raise RuntimeError("Remote source mismatch")
    start = time.perf_counter()
    if mode == "collect":
        result = collect(payload)
    elif mode == "fit":
        result = fit(payload)
    elif mode == "rollout":
        seed, names, bundle = payload
        result = dict(seed=seed, policies={n: rollout(seed, n, bundle) for n in names})
    elif mode == "freeze":
        result = select_baseline(payload[0])
        result["training_seeds"] = payload[1]
    elif mode == "summary":
        result = summarize(*payload)
    else:
        raise ValueError("Unknown mode")
    return dict(
        result=result,
        function_seconds=time.perf_counter() - start,
        environment=dict(
            python=platform.python_version(),
            numpy=numpy.__version__,
            scipy=scipy.__version__,
            sklearn=sklearn.__version__,
        ),
    )


def execute(output, remote_batch):
    from scripts.sequential_controller import (
        specification,
        validate_training,
        validate_rollout,
        LEARNED,
        STATIC,
    )

    raw = (output / "manifest.json").read_bytes()
    manifest = json.loads(raw)
    if manifest != specification():
        raise ValueError("Changed frozen specification")
    identity = hashlib.sha256(raw).hexdigest()
    if list(output.glob("*.pending")):
        raise RuntimeError(
            "Inspect pending Modal call before recovery; no automatic retries"
        )
    lock = output / "dispatch.lock"
    with lock.open("x") as f:
        f.write(identity)

    def batch(jobs):
        saved, missing = {}, []
        for name, mode, payload in jobs:
            path = output / (name + ".json")
            if path.exists():
                item = json.loads(path.read_text())
                if item["manifest_sha256"] != identity:
                    raise ValueError("Artifact identity mismatch")
                saved[name] = item["response"]["result"]
            else:
                missing.append((name, mode, payload))
        for offset in range(0, len(missing), 4):
            chunk = missing[offset : offset + 4]
            for name, _, _ in chunk:
                with (output / (name + ".pending")).open("x") as f:
                    f.write(identity)
            responses = list(
                remote_batch(
                    [(mode, payload, manifest["sources"]) for _, mode, payload in chunk]
                )
            )
            if len(responses) != len(chunk):
                raise ValueError("Incomplete remote batch")
            for (name, _, _), response in zip(chunk, responses):
                path = output / (name + ".json")
                temp = path.with_suffix(".tmp")
                temp.write_text(
                    json.dumps(
                        dict(manifest_sha256=identity, response=response),
                        allow_nan=False,
                    )
                    + "\n"
                )
                temp.replace(path)
                (output / (name + ".pending")).unlink()
                saved[name] = response["result"]
                print("Saved " + name, flush=True)
        return [saved[name] for name, _, _ in jobs]

    try:
        training = batch(
            [(f"training-{s}", "collect", s) for s in manifest["training_seeds"]]
        )
        for data, seed in zip(training, manifest["training_seeds"]):
            validate_training(data, seed)
        bundle = batch([("models", "fit", training)])[0]

        def evaluate(split, names):
            rows = batch(
                [
                    (f"{split}-{s}", "rollout", (s, names, bundle))
                    for s in manifest[split + "_seeds"]
                ]
            )
            for row, seed in zip(rows, manifest[split + "_seeds"]):
                if row["seed"] != seed or set(row["policies"]) != set(names):
                    raise ValueError("Evaluation identity mismatch")
                for name in names:
                    validate_rollout(row["policies"][name], seed, name)
            return rows

        validation = evaluate("validation", list(STATIC))
        frozen = batch(
            [("frozen-policy", "freeze", (validation, manifest["training_seeds"]))]
        )[0]
        if (
            frozen["training_seeds"] != manifest["training_seeds"]
            or frozen["validation_seeds"] != manifest["validation_seeds"]
        ):
            raise ValueError("Frozen split mismatch")
        # This file and model hash exist before any confirmation dispatch.
        receipt = dict(
            manifest_sha256=identity,
            models_sha256=hashlib.sha256(
                (output / "models.json").read_bytes()
            ).hexdigest(),
            frozen_sha256=hashlib.sha256(
                (output / "frozen-policy.json").read_bytes()
            ).hexdigest(),
        )
        receipt_path = output / "freeze-receipt.json"
        if receipt_path.exists() and json.loads(receipt_path.read_text()) != receipt:
            raise ValueError("Frozen model changed")
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
        confirmation = evaluate(
            "confirmation", [*LEARNED, frozen["static"], "reactive"]
        )
        return batch([("summary", "summary", (confirmation, frozen))])[0]
    finally:
        lock.unlink()


@app.local_entrypoint()
def main(output: str):
    result = execute(Path(output), lambda jobs: task.starmap(jobs, order_outputs=True))
    print(json.dumps(result, indent=2))
