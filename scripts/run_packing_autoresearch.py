"""Bounded, resumable parameter autoresearch on Modal; no local search execution.

A deterministic proposer adapts step size to keep/discard outcomes. This is a
restricted search loop, not an LLM that invents arbitrary optimizer source code.
"""

import argparse
import fcntl
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    "modal_gpu_packing.py",
    "check_math_packing.py",
    "pilot_math_revision.py",
    "run_packing_autoresearch.py",
)


def save(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def hashes():
    return {
        name: hashlib.sha256((ROOT / "scripts" / name).read_bytes()).hexdigest()
        for name in FILES
    }


def proposal(history):
    if not history:
        return dict(
            schedule="constant100",
            learning_rate=0.003,
            hypothesis="Establish frozen baseline",
        )
    kept = [r for r in history if r["status"] == "keep"]
    incumbent = kept[-1]["candidate"]
    index = len(history)
    if index == 1:
        return dict(
            schedule="linear10to1000",
            learning_rate=0.003,
            hypothesis="Increasing penalty may improve feasible score",
        )
    if index == 2:
        return dict(
            schedule="constant1000",
            learning_rate=incumbent["learning_rate"],
            hypothesis="Strong constraints throughout may reduce repair losses",
        )
    return dict(
        schedule=incumbent["schedule"],
        learning_rate=0.001 if history[-1]["status"] != "keep" else 0.01,
        hypothesis="Refine retained schedule with smaller steps after failure, larger after improvement",
    )


def score(report, seed):
    import numpy as np
    from scripts.check_math_packing import verify

    if (
        report["seed"] != seed
        or report["starts"] != 32
        or report["steps_per_schedule"] != 2000
    ):
        raise ValueError("Evaluation budget or seed mismatch")
    if len(report["results"]) != 1:
        raise ValueError("Expected one candidate")
    rows = report["results"][0]["constructions"]
    if len(rows) != 32:
        raise ValueError("Missing starts")
    values = []
    for row in rows:
        z = np.asarray(row, dtype=float)
        if z.shape != (26, 3):
            raise ValueError("Wrong problem dimensions")
        checked = verify(z[:, :2], z[:, 2])
        if not checked["strictly_feasible"]:
            raise ValueError("Invalid geometry")
        values.append(checked["sum_radii"])
    return dict(mean=float(np.mean(values)), per_start=values)


def run(directory, evaluate):
    state_path = directory / "state.json"
    state = json.loads(state_path.read_text())
    if state["hashes"] != hashes():
        raise RuntimeError("Frozen evaluator/source changed; start a new run")
    if state.get("pending"):
        raise RuntimeError(
            "Uncertain remote attempt: inspect pending artifact before any paid retry"
        )
    history = state["history"]
    while len(history) < 4:
        candidate = proposal(history)
        index = len(history)
        save(directory / f"candidate-{index}.json", candidate)
        state["pending"] = f"candidate-{index}"
        save(state_path, state)
        try:
            report = evaluate(candidate, state["development_seed"])
            save(directory / f"result-{index}.json", report)
            measured = score(report, state["development_seed"])
            previous = max(
                (r["score"]["mean"] for r in history if r["status"] == "keep"),
                default=-float("inf"),
            )
            entry = dict(
                candidate=candidate,
                score=measured,
                status="keep" if measured["mean"] > previous + 1e-7 else "discard",
            )
        except Exception as error:
            save(
                directory / f"failure-{index}.json",
                dict(error_type=type(error).__name__, status="unresolved"),
            )
            raise
        history.append(entry)
        state["pending"] = None
        save(state_path, state)
        ledger = "trial\tstatus\tmean_score\tschedule\tlearning_rate\n"
        for trial, row in enumerate(history):
            ledger += f"{trial}\t{row['status']}\t{row['score']['mean']:.12f}\t{row['candidate']['schedule']}\t{row['candidate']['learning_rate']}\n"
        (directory / "results.tsv").write_text(ledger)
    if state.get("confirmation"):
        return state
    winner = [r for r in history if r["status"] == "keep"][-1]["candidate"]
    # Freeze winner before any fresh-seed outcomes are observed.
    save(directory / "selected.json", winner)
    confirmation = []
    for name, candidate in (
        ("baseline", history[0]["candidate"]),
        ("selected", winner),
    ):
        path = directory / f"confirmation-{name}.json"
        if path.exists():
            report = json.loads(path.read_text())
        else:
            state["pending"] = f"confirmation-{name}"
            save(state_path, state)
            report = evaluate(candidate, state["confirmation_seed"])
            save(path, report)
            state["pending"] = None
            save(state_path, state)
        confirmation.append(score(report, state["confirmation_seed"]))
    state["confirmation"] = dict(
        baseline=confirmation[0],
        selected=confirmation[1],
        mean_difference=confirmation[1]["mean"] - confirmation[0]["mean"],
        caveat="One development batch and one confirmation batch; no independent research-loop replication or record claim",
    )
    save(state_path, state)
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    path = args.output / "state.json"
    if not path.exists():
        save(
            path,
            dict(
                hashes=hashes(),
                development_seed=2026111700,
                confirmation_seed=2026111800,
                history=[],
                pending=None,
                max_remote_calls=6,
                resource="one L4, 600 seconds per call, no retries",
            ),
        )
    if not args.execute:
        print(
            f"Prepared {path}; no Modal calls. Add --execute when billing is enabled."
        )
        return
    from scripts.modal_gpu_packing import app, study

    def evaluate(candidate, seed):
        return study.remote(
            schedule=candidate["schedule"],
            learning_rate=candidate["learning_rate"],
            seed=seed,
        )

    with (args.output / "run.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError("Another process owns this research run") from error
        with app.run():
            result = run(args.output, evaluate)
    print(json.dumps(result["confirmation"], indent=2))


if __name__ == "__main__":
    main()
