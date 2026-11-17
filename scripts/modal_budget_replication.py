"""Predeclared doubled-budget replication; no schedule reselection."""

import json
from pathlib import Path
import modal
from scripts.modal_revision_hypotheses import image

app = modal.App("saint-budget-replication")


@app.function(
    image=image,
    cpu=(1, 1),
    memory=(2048, 2048),
    timeout=600,
    max_containers=4,
    retries=0,
)
def run(seed):
    from scripts.matched_revision import Protocol, initialize, advance
    from scripts.revision_hypotheses import RECIPES
    from dataclasses import replace

    p = Protocol(evaluations_per_window=160)
    result = {"seed": seed}
    for name, timing in [("broad", 5), ("moderate", 4)]:
        q = replace(p, revised_std=RECIPES[name])
        state = initialize(seed, q)
        for t in range(8):
            state, _ = advance(state, "REVISE" if t == timing else "KEEP", q)
        result[name] = {
            "score": state.score,
            "evaluations": state.evaluations,
            "construction": state.incumbent.tolist(),
        }
    return result


@app.local_entrypoint()
def main():
    from scripts.revision_hypotheses import contrast
    import numpy as np

    out = Path("outputs/budget-replication-v1")
    out.mkdir(exist_ok=False)
    manifest = {
        "hypothesis": "moderate fixed4 exceeds broad fixed5 at doubled budget",
        "seeds": list(range(2026230000, 2026230048)),
        "evaluations": 1280,
        "success": "mean >= .0005 and paired 97.5% lower bound >0",
        "no_reselection": True,
        "maximum_function_USD": 0.506,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    rows = []
    for offset in range(0, 48, 4):
        (out / "pending.json").write_text(
            json.dumps(manifest["seeds"][offset : offset + 4])
        )
        for row in run.map(manifest["seeds"][offset : offset + 4]):
            rows.append(row)
            (out / f"seed-{row['seed']}.json").write_text(json.dumps(row))
            print(len(rows), flush=True)
        (out / "pending.json").unlink()
    report = contrast(
        np.array([r["moderate"]["score"] for r in rows]),
        np.array([r["broad"]["score"] for r in rows]),
    )
    report["means"] = {
        k: float(np.mean([r[k]["score"] for r in rows])) for k in ("moderate", "broad")
    }
    (out / "summary.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report))
