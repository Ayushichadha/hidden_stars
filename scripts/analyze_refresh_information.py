"""Measure held-out predictability of single-refresh outcomes from observed prefixes."""

import json
from pathlib import Path
import sqlite3

import numpy as np
import torch

from scripts.run_feudal_sqlite_bridge import Worker, choices, REFRESH
from scripts.run_sqlite_revision import build_tasks, collect, HORIZON
from scripts.run_optional_tool_revision import score


def main():
    torch.set_num_threads(2)
    results = []
    for seed in range(2026111501, 2026111504):
        model = Worker()
        model.load_state_dict(
            torch.load(f"outputs/sqlite-reactive-{seed}/worker.pt", weights_only=True)
        )
        model.eval()
        db = sqlite3.connect(":memory:")
        db.executescript(
            "CREATE TABLE source(task TEXT,position INTEGER,payload TEXT,PRIMARY KEY(task,position));"
            "CREATE TABLE delivered(task TEXT,position INTEGER,payload TEXT,PRIMARY KEY(task,position));"
        )
        datasets = []
        for offset, size in [(100, 3000), (101, 1500)]:
            tasks = build_tasks(seed + offset, size, f"information-{offset}")
            for task in tasks:
                db.executemany(
                    "INSERT INTO source VALUES (?,?,?)",
                    [(task["id"], i, f'{task["id"]}-{i}') for i in range(HORIZON)],
                )
            datasets.append(collect(db, tasks))
        (train, rewards), (test, test_rewards) = datasets
        baseline = score(rewards, choices(model, train))
        test_baseline = score(test_rewards, choices(model, test))
        passes = []
        for k in REFRESH:
            target = score(rewards, choices(model, train, k)) - baseline
            actual = score(test_rewards, choices(model, test, k)) - test_baseline

            # Full observed binary prefix plus known workload. No fault labels.
            def keys(data):
                return [
                    (int(required), *history[:k].astype(int).tolist())
                    for required, history in zip(data[3], data[1])
                ]

            groups = {}
            for key, value in zip(keys(train), target):
                groups.setdefault(key, []).append(float(value))
            mean = float(target.mean())
            predictions = []
            counts = []
            for key in keys(test):
                values = groups.get(key, [])
                counts.append(len(values))
                predictions.append((sum(values) + 10 * mean) / (len(values) + 10))
            predictions = np.array(predictions)
            adaptive = np.where(predictions > 0, actual, 0)
            clock = actual if mean > 0 else np.zeros_like(actual)
            diff = adaptive - clock
            rng = np.random.default_rng(seed + k)
            draws = diff[rng.integers(len(diff), size=(2000, len(diff)))].mean(1)
            passes.append(
                dict(
                    pass_number=k,
                    workflows=len(actual),
                    only_refresh=int((actual > 0).sum()),
                    only_persist=int((actual < 0).sum()),
                    prefix_coverage=float(np.mean(np.array(counts) > 0)),
                    median_training_prefix_count=float(np.median(counts)),
                    timing_mse=float(np.mean((actual - mean) ** 2)),
                    prefix_mse=float(np.mean((actual - predictions) ** 2)),
                    prefix_policy_minus_timing=float(diff.mean()),
                    ci95=np.quantile(draws, [0.025, 0.975]).tolist(),
                )
            )
        results.append(dict(seed=seed, passes=passes))
        db.close()
    output = Path("outputs/sqlite-information.json")
    output.write_text(
        json.dumps(
            {
                "scope": "Fixed-pass refresh versus never refresh; full observed history; independent fitting/evaluation tasks; smoothing=10; exploratory per-pass intervals",
                "results": results,
            },
            indent=2,
        )
    )
    for result in results:
        print(
            result["seed"],
            [
                (
                    p["pass_number"],
                    round(p["prefix_policy_minus_timing"] * 100, 2),
                    round(p["prefix_coverage"], 2),
                )
                for p in result["passes"]
            ],
        )


if __name__ == "__main__":
    main()
