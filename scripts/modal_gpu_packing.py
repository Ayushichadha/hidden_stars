"""Bounded CUDA optimizer feasibility study; not an HRM or policy experiment."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parents[1]
app = modal.App("saint-gpu-packing")
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("torch==2.5.1", "numpy==2.1.3", "scipy==1.14.1")
    .add_local_file(
        ROOT / "scripts/check_math_packing.py", "/root/scripts/check_math_packing.py"
    )
    .add_local_file(
        ROOT / "scripts/pilot_math_revision.py", "/root/scripts/pilot_math_revision.py"
    )
)


@app.function(
    image=image,
    gpu="L4",
    cpu=2,
    memory=4096,
    timeout=600,
    retries=0,
    max_containers=1,
)
def study():
    import sys
    import time

    import numpy as np
    import torch

    sys.path.insert(0, "/root")
    from scripts.check_math_packing import verify
    from scripts.pilot_math_revision import repair

    assert torch.cuda.is_available(), "GPU execution required"
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    seed = 2026111700
    rng = np.random.default_rng(seed)
    initial = np.concatenate(
        [rng.uniform(0.05, 0.95, (32, 26, 2)), np.full((32, 26, 1), 0.02)], axis=2
    )
    i, j = torch.triu_indices(26, 26, offset=1, device="cuda")
    results = []
    started = time.perf_counter()
    for schedule in ("constant100", "linear10to1000", "constant1000"):
        x = torch.tensor(
            initial, device="cuda", dtype=torch.float64, requires_grad=True
        )
        opt = torch.optim.Adam([x], lr=0.003)
        initial_sha256 = hashlib.sha256(initial.tobytes()).hexdigest()
        best = [repair(row.ravel()).reshape(26, 3) for row in initial]
        trace = []
        torch.cuda.synchronize()
        begin = time.perf_counter()
        for step in range(2000):
            opt.zero_grad()
            c, r = x[:, :, :2], x[:, :, 2]
            dist = ((c[:, i] - c[:, j]).square().sum(-1) + 1e-20).sqrt()
            overlap = torch.relu(r[:, i] + r[:, j] - dist)
            wall = torch.relu(r[:, :, None] - torch.minimum(c, 1 - c))
            weight = 100 if schedule == "constant100" else 1000
            if schedule == "linear10to1000":
                weight = 10 + 990 * step / 1999
            loss = -r.sum(-1) + weight * (
                overlap.square().sum(-1) + wall.square().sum((1, 2))
            )
            if not torch.isfinite(loss).all():
                raise FloatingPointError(f"Nonfinite loss: {schedule}, step {step}")
            loss.sum().backward()
            opt.step()
            with torch.no_grad():
                x[:, :, :2].clamp_(1e-8, 1 - 1e-8)
                x[:, :, 2].clamp_(1e-8, 0.5)
            if (step + 1) % 100 == 0:
                for k, row in enumerate(x.detach().cpu().numpy()):
                    candidate = repair(row.ravel()).reshape(26, 3)
                    if candidate[:, 2].sum() > best[k][:, 2].sum():
                        best[k] = candidate
                trace.append(
                    dict(
                        step=step + 1,
                        mean_verified_score=float(
                            np.mean([b[:, 2].sum() for b in best])
                        ),
                    )
                )
        torch.cuda.synchronize()
        checked = [verify(b[:, :2], b[:, 2]) for b in best]
        assert all(row["strictly_feasible"] for row in checked)
        results.append(
            dict(
                schedule=schedule,
                seconds=time.perf_counter() - begin,
                initial_sha256=initial_sha256,
                objective_evaluations=32 * 2000,
                constructions=[b.tolist() for b in best],
                verification=checked,
                trace=trace,
            )
        )
        print(
            f"Completed {schedule}: mean={np.mean([r['sum_radii'] for r in checked]):.8f}",
            flush=True,
        )
    return dict(
        scope="development optimizer feasibility; no held-out policy or record claim",
        seed=seed,
        starts=32,
        steps_per_schedule=2000,
        gpu=torch.cuda.get_device_name(),
        torch_version=torch.__version__,
        total_seconds=time.perf_counter() - started,
        results=results,
    )


@app.local_entrypoint()
def main():
    tag = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out = ROOT / "outputs" / f"gpu-packing-development-l4-{tag}"
    out.mkdir(parents=True, exist_ok=False)
    manifest = dict(
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        evaluator_sha256=hashlib.sha256(
            (ROOT / "scripts/check_math_packing.py").read_bytes()
        ).hexdigest(),
        repair_sha256=hashlib.sha256(
            (ROOT / "scripts/pilot_math_revision.py").read_bytes()
        ).hexdigest(),
        status="prepared",
        created_utc=tag,
        hypothesis="Increasing overlap penalties may improve verified feasible radius sums.",
        comparisons=["constant100", "linear10to1000", "constant1000"],
        budget="32 paired starts, 2000 Adam steps each; one L4, 600-second timeout",
        limitation="equal optimizer steps, not equal wall time or comparable SLSQP calls",
    )
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    try:
        result = study.remote()
        temporary = out / "report.json.tmp"
        temporary.write_text(json.dumps(result, indent=2, allow_nan=False))
        temporary.replace(out / "report.json")
        manifest["status"] = "completed"
    except Exception as error:
        manifest["status"] = "failed"
        manifest["error_type"] = type(error).__name__
        raise
    finally:
        (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"Saved {out / 'report.json'}")
