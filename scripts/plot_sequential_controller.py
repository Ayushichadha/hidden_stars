"""Render the frozen sequential contrasts from the saved Modal summary."""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def plot(source, output, preview=None):
    data = json.loads(source.read_text())["response"]["result"]
    names = [
        "H1_tree_sequential_minus_ridge_sequential",
        "H2_tree_sequential_minus_tree_myopic",
        "descriptive_tree_sequential_minus_selected_static",
    ]
    labels = [
        "Tree sequential − ridge sequential\nCapacity: primary H1",
        "Tree sequential − tree myopic\nSequential credit: primary H2",
        "Tree sequential − selected fixed\nDescriptive comparison",
    ]
    fig, ax = plt.subplots(figsize=(9, 3.7), layout="constrained")
    colors = ["#205b8d", "#205b8d", "#747474"]
    for y, name, color in zip([2, 1, 0], names, colors):
        c = data["comparisons"][name]
        low, high = np.array(c["paired_seed_97_5_interval"]) * 1000
        mean = c["mean"] * 1000
        ax.plot([low, high], [y, y], color=color, lw=2.5, solid_capstyle="round")
        ax.plot(mean, y, "o", color=color, markersize=7)
    ax.axvline(0, color="#333333", lw=1)
    ax.axvline(0.5, color="#999999", lw=1, ls=":")
    ax.set_yticks([2, 1, 0], labels, fontsize=10)
    ax.set_ylim(-0.6, 2.6)
    ax.set_xlabel(
        "Paired terminal-score difference × 1,000 (higher favors tree sequential)"
    )
    ax.set_title(
        "Sequential control: 48 fresh paired confirmation seeds",
        loc="left",
        fontsize=12,
        pad=14,
    )
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0, pad=12)
    ax.grid(axis="x", alpha=0.15)
    fig.suptitle(
        "Dots: mean · bars: 97.5% paired bootstrap intervals · dotted line: +0.0005 useful-gain threshold",
        fontsize=8,
        y=-0.035,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight")
    if preview:
        fig.savefig(preview, dpi=160, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("outputs/sequential-controller-v2/summary.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("papers/trust4rsi/sequential-controller-results.svg"),
    )
    parser.add_argument("--preview", type=Path)
    args = parser.parse_args()
    plot(args.source, args.output, args.preview)
