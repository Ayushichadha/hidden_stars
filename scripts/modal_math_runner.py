"""Offload a bounded research trajectory to Modal; no local numerical work."""

import json
from pathlib import Path
import modal

ROOT = Path(__file__).resolve().parents[1]
image = (
    modal.Image.debian_slim(python_version="3.13")
    .pip_install("numpy", "scipy", "certifi")
    .pip_install("torch", index_url="https://download.pytorch.org/whl/cpu")
    .env({"OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"})
)
for name in (
    "check_math_packing.py",
    "pilot_math_revision.py",
    "meta_search_agent.py",
    "run_math_supervisor_study.py",
):
    image = image.add_local_file(ROOT / "scripts" / name, "/root/scripts/" + name)
app = modal.App("saint-math-research")


@app.function(
    image=image,
    cpu=(1, 1),
    memory=(2048, 2048),
    timeout=180,
    max_containers=1,
    retries=0,
)
def collect_remote(split: str, seed: int):
    import sys

    sys.path.insert(0, "/root")
    from scripts.run_math_supervisor_study import collect

    return collect((split, seed))


@app.local_entrypoint()
def main():
    output = ROOT / "outputs/modal-smoke-20261116.json"
    if output.exists():
        raise RuntimeError("Smoke output already exists; refusing duplicate paid run")
    rows = collect_remote.remote("modal_smoke", 2026150000)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(rows, indent=2) + "\n")
    print(f"Modal completed {len(rows)} paired checkpoints; artifacts saved locally.")
