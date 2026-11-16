"""Run a prepared timing-opportunity protocol on Modal CPU, sequentially.

No GPU is needed by this SciPy worker. Importing/preparing does not launch work.
Interrupted calls leave pending markers and require inspection before recovery.
"""

import hashlib
import json
from pathlib import Path
import platform

import modal

ROOT = Path(__file__).resolve().parents[1]
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("numpy==2.2.6", "scipy==1.15.3")
    .env({"OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"})
)
for name in (
    "matched_revision.py",
    "pilot_math_revision.py",
    "check_math_packing.py",
    "modal_matched_revision.py",
):
    image = image.add_local_file(ROOT / "scripts" / name, "/root/scripts/" + name)
app = modal.App("saint-matched-revision")


@app.function(
    image=image,
    cpu=(1, 1),
    memory=(2048, 2048),
    timeout=600,
    max_containers=1,
    retries=0,
)
def collect_remote(protocol, seed, expected_sources):
    import sys
    import numpy as np
    import scipy

    sys.path.insert(0, "/root")
    from scripts.matched_revision import Protocol, collect, source_hashes

    if source_hashes() != expected_sources:
        raise RuntimeError("Remote source mismatch")
    return dict(
        rows=collect(seed, Protocol(**protocol)),
        environment=dict(
            python=platform.python_version(),
            numpy=np.__version__,
            scipy=scipy.__version__,
        ),
    )


def execute(output, remote):
    """Fail-closed dispatcher; injected remote allows offline lifecycle tests."""
    from scripts.matched_revision import (
        Protocol,
        source_hashes,
        summarize,
        validate_rows,
    )

    path = output / "manifest.json"
    manifest_bytes = path.read_bytes()
    digest = hashlib.sha256(manifest_bytes).hexdigest()
    manifest = json.loads(manifest_bytes)
    if manifest["sources"] != source_hashes() or manifest["split"] != "development":
        raise RuntimeError("Changed sources or non-development manifest")
    protocol = Protocol(**manifest["protocol"])
    seeds = manifest["seeds"]
    if (
        not 1 <= len(seeds) <= 32
        or len(set(seeds)) != len(seeds)
        or any(not isinstance(seed, int) or seed < 0 for seed in seeds)
    ):
        raise ValueError("Invalid bounded seed allocation")
    # This runner accepts only the prepared default numerical budget.
    if protocol != Protocol():
        raise ValueError("Nondefault budget requires a separately reviewed runner")
    lock = output / "dispatch.lock"
    with lock.open("x") as stream:
        stream.write(digest)
    try:
        rows = []
        for seed in seeds:
            target = output / f"seed-{seed}.json"
            pending = output / f"seed-{seed}.pending"
            if pending.exists():
                raise RuntimeError("Pending paid call: inspect Modal before recovery")
            if target.exists():
                result = json.loads(target.read_text())
                if result["manifest_sha256"] != digest:
                    raise RuntimeError("Saved result belongs to another manifest")
            else:
                pending.write_text(digest)
                result = dict(
                    remote(manifest["protocol"], seed, manifest["sources"]),
                    manifest_sha256=digest,
                )
                validate_rows(result["rows"], seed, protocol)
                temp = target.with_suffix(".tmp")
                temp.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
                temp.replace(target)
                pending.unlink()
            validate_rows(result["rows"], seed, protocol)
            rows.extend(result["rows"])
        summary = summarize(rows)
        (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        return summary
    finally:
        lock.unlink()


@app.local_entrypoint()
def main(output: str):
    print(json.dumps(execute(Path(output), collect_remote.remote), indent=2))


if __name__ == "__main__":
    raise SystemExit("Use modal run scripts/modal_matched_revision.py --output PATH")
