"""Pair existing explicit-action and latent-goal runs by verified task identity."""

import json
from pathlib import Path
import numpy as np


def outcomes(path, policy):
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    return {row["task"]["id"]: row for row in rows if row["policy"] == policy}


def main():
    report = []
    for seed in range(2026111601, 2026111604):
        direct = outcomes(Path(f"outputs/sqlite-explicit-{seed}/trace.jsonl"), "state")
        latent = outcomes(
            Path(f"outputs/sqlite-direct-{seed}/trace.jsonl"), "state_refresh"
        )
        assert direct.keys() == latent.keys() and len(direct) == 500
        assert all(direct[k]["task"] == latent[k]["task"] for k in direct)
        diff = np.array(
            [int(direct[k]["solved"]) - int(latent[k]["solved"]) for k in direct]
        )
        rng = np.random.default_rng(seed)
        draws = diff[rng.integers(len(diff), size=(10000, len(diff)))].mean(1)
        report.append(
            dict(
                seed=seed,
                rescued=int((diff > 0).sum()),
                lost=int((diff < 0).sum()),
                difference=float(diff.mean()),
                ci95=np.quantile(draws, [0.025, 0.975]).tolist(),
            )
        )
    Path("outputs/sqlite-interface-comparison.json").write_text(
        json.dumps(report, indent=2)
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
