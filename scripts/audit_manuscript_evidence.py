"""Summarize existing manuscript evidence without training or checkpoint inference."""

import argparse
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def audit(root):
    report = {
        "scope": "Saved-artifact audit; no fresh model evaluation",
        "artifacts": {},
    }

    def read(relative, csv_file=False):
        path = root / relative
        record = {"path": relative, "available": path.is_file()}
        report["artifacts"][relative] = record
        if not record["available"]:
            return None
        content = path.read_bytes()
        record["sha256"] = hashlib.sha256(content).hexdigest()
        if csv_file:
            return list(csv.DictReader(content.decode().splitlines()))
        return json.loads(content)

    for name in ("revision-endpoints", "revision-development"):
        rows = read(f"outputs/{name}.csv", csv_file=True)
        if rows is None:
            continue
        episodes = {row["episode"] for row in rows}
        persist = {row["episode"] for row in rows if int(row["persist"])}
        report[name] = {
            "decision_rows": len(rows),
            "episodes": len(episodes),
            "sources": (
                len({row["source"] for row in rows})
                if rows and "source" in rows[0]
                else None
            ),
            "persist_solved_episodes": len(persist),
            "revise_solved_branches": sum(int(row["revise"]) for row in rows),
            "rescued_branches": sum(
                int(row["revise"]) and not int(row["persist"]) for row in rows
            ),
            "lost_branches": sum(
                int(row["persist"]) and not int(row["revise"]) for row in rows
            ),
            "caveat": "Pass rows repeat episodes; these are not independent trials.",
        }
    rows = read(
        "analysis/counterfactual_persistence_v2_diagnostic/decision_states.csv",
        csv_file=True,
    )
    if rows is not None:
        report["score_diagnostic"] = {
            "decision_rows": len(rows),
            "persist_preferred_rows": sum(
                row["oracle_preference"] == "PERSIST" for row in rows
            ),
            "caveat": "Loss preference is not exact task success.",
        }
    run = read("outputs/hrm-memorization-run.json")
    grids = read("outputs/hrm-memorization-grids.json")
    if grids is not None:
        errors = sum(len(row["errors"]) for row in grids)
        scored = sum(
            char != "." for row in grids for line in row["target"] for char in line
        )
        report["memorization"] = {
            "steps": run["steps"] if run is not None else None,
            "examples": len(grids),
            "unique_puzzle_ids": len({row["puzzle_id"] for row in grids}),
            "exact_solves": sum(not row["errors"] for row in grids),
            "token_errors": errors,
            "scored_tokens": scored,
            "token_accuracy": 1 - errors / scored if scored else None,
            "caveat": "Decoded saved predictions on a repeated training batch, not generalization.",
        }
    math = read("outputs/neural-supervisor-20261116/report.json")
    if math is not None:
        report["math_exploration"] = {
            "test_trajectories": math["trajectories"],
            "test_decisions": math["decisions"],
            "neural_minus_clock": math["policies"]["neural"]["comparisons"]["clock"],
            "neural_minus_local": math["policies"]["neural"]["comparisons"]["local"],
            "caveat": "Numerical search supervisor; does not implement HRM.",
        }
    report["missing_artifacts"] = [
        name for name, entry in report["artifacts"].items() if not entry["available"]
    ]
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rendered = json.dumps(audit(args.root), indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
