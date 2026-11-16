import json
from pathlib import Path
import numpy as np
from scripts.meta_search_agent import search_window
from scripts.pilot_math_revision import repair, solve

out = Path("outputs/math-paired-20261116")
out.mkdir(exist_ok=False)
rows = []
for seed in range(2026111900, 2026111912):
    rng = np.random.default_rng(seed)
    x = repair(
        np.column_stack((rng.uniform(0.05, 0.95, (26, 2)), np.full(26, 0.01))).ravel()
    )
    x, m = solve(x, 40, 30)
    if m["function_evaluations"] < 30:
        x, _ = search_window(x, "local", seed, 0, 30 - m["function_evaluations"])
    for checkpoint in range(3):
        outcomes = {}
        for action in ("local", "broad"):
            y, steps = search_window(x, action, seed, checkpoint + 10, 60)
            y, tail = search_window(y, "local", seed, checkpoint + 20, 60)
            assert sum(s["function_evaluations"] for s in steps + tail) == 120
            outcomes[action] = float(y[2::3].sum())
        row = dict(
            seed=seed,
            checkpoint=checkpoint,
            score=float(x[2::3].sum()),
            outcomes=outcomes,
            delta=outcomes["broad"] - outcomes["local"],
        )
        rows.append(row)
        with (out / "pairs.jsonl").open("a") as f:
            f.write(json.dumps(row) + "\n")
        np.save(out / f"{seed}-{checkpoint}.npy", x)
        x, _ = search_window(x, "local", seed, checkpoint + 1, 60)
    print("Completed", seed, flush=True)
summary = {}
for k in range(3):
    d = np.array([r["delta"] for r in rows if r["checkpoint"] == k])
    summary[k] = dict(
        pairs=len(d),
        broad_wins=int((d > 1e-7).sum()),
        local_wins=int((d < -1e-7).sum()),
        ties=int((abs(d) <= 1e-7).sum()),
        mean_delta=float(d.mean()),
    )
(out / "summary.json").write_text(json.dumps(summary, indent=2))
print(json.dumps(summary, indent=2))
