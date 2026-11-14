"""Render paired intervals and an explicitly selected logged workflow replay."""

import json
from pathlib import Path

import imageio.v2 as imageio
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def main():
    output = Path("outputs/sqlite-visuals")
    output.mkdir(exist_ok=True)
    runs = [
        Path(f"outputs/sqlite-visual-{seed}") for seed in range(2026111401, 2026111404)
    ]
    reports = [json.loads((p / "summary.json").read_text()) for p in runs]
    fig, ax = plt.subplots(figsize=(8, 4))
    for offset, (key, label) in enumerate(
        [
            ("trained_observation_only", "State refresh minus observation-only"),
            ("time_refresh", "State refresh minus learned timing"),
        ]
    ):
        values = [r["paired"][key] for r in reports]
        means = np.array([v["difference"] * 100 for v in values])
        bounds = np.array([v["ci95"] for v in values]) * 100
        ax.errorbar(
            np.arange(3) + offset * 0.12,
            means,
            yerr=[means - bounds[:, 0], bounds[:, 1] - means],
            fmt="o",
            capsize=4,
            label=label,
        )
    ax.axhline(0, color="gray", linestyle="--")
    ax.set(
        xticks=np.arange(3) + 0.06,
        xticklabels=["Seed 1", "Seed 2", "Seed 3"],
        ylabel="Paired completion difference (percentage points)",
        title="SQLite workflows · 500 evaluation tasks per seed",
    )
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(output / "paired_intervals.png", dpi=180)
    fig.savefig(output / "paired_intervals.pdf")
    plt.close(fig)

    rows = [
        json.loads(line) for line in (runs[0] / "trace.jsonl").read_text().splitlines()
    ]
    policies = ["persist", "state_refresh", "trained_observation_only"]
    indexed = {(r["task"]["id"], r["policy"]): r for r in rows}
    candidates = sorted(
        r["task"]["id"]
        for r in rows
        if r["policy"] == "state_refresh"
        and r["solved"]
        and not indexed[r["task"]["id"], "persist"]["solved"]
    )
    task = candidates[0]
    selected = [indexed[task, p] for p in policies]
    (output / "trace_selection.json").write_text(
        json.dumps(
            {
                "selection": "Lexicographically first state-refresh rescue versus persistence in seed 1",
                "task": task,
                "representative": False,
                "records": selected,
            },
            indent=2,
        )
    )
    frames = []
    for step in range(13):
        fig, axes = plt.subplots(3, 1, figsize=(10, 6), dpi=100)
        fig.suptitle(f"Recorded SQLite workflow · call {step}/12\n{task}", fontsize=13)
        for ax, row in zip(axes, selected):
            count = row["events"][step - 1]["cursor"] if step else 0
            required = row["task"]["required"]
            ax.barh([0], [count], color="#237a73")
            ax.axvline(required, color="#ab4830", linestyle="--")
            status = row["events"][step - 1]["status"] if step else "start"
            refresh = " · GOAL REFRESH" if step in row["goal_refresh"] else ""
            ax.set(
                xlim=(0, 12), yticks=[], title=f"{row['policy']} · {status}{refresh}"
            )
            ax.text(11.5, 0, f"{count}/{required} records", ha="right", va="center")
        axes[-1].set_xlabel("Delivered records · dashed line marks required count")
        fig.text(
            0.5,
            0.015,
            "Selected rescue example · synthetic service faults · replay of verified event log",
            ha="center",
            fontsize=9,
        )
        fig.tight_layout(rect=[0, 0.04, 1, 0.90])
        fig.canvas.draw()
        frames.append(np.asarray(fig.canvas.buffer_rgba())[:, :, :3].copy())
        if step == 12:
            fig.savefig(output / "trace_final.png")
        plt.close(fig)
    with imageio.get_writer(
        output / "workflow_trace.mp4", fps=2, macro_block_size=2
    ) as writer:
        for frame in frames:
            for _ in range(3):
                writer.append_data(frame)
    reader = imageio.get_reader(output / "workflow_trace.mp4")
    assert reader.count_frames() == 39
    reader.close()
    for report in reports:
        print(report["seed"], report["paired"]["trained_observation_only"])


if __name__ == "__main__":
    main()
