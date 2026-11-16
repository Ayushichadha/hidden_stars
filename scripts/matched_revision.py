"""Frozen, window-boundary commitments and exhaustive revision timing.

Numerical collection is invoked by the Modal runner. Local CLI only prepares a
manifest. SLSQP is deliberately restarted per call: no hidden optimizer history
crosses a window boundary. Counter-based randomness is part of the cloned state.
"""

import argparse
from dataclasses import asdict, dataclass, replace
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from scripts.check_math_packing import verify
from scripts.pilot_math_revision import repair, solve


@dataclass(frozen=True)
class Protocol:
    circles: int = 26
    windows: int = 8
    evaluations_per_window: int = 80
    iterations_per_call: int = 40
    local_std: float = 0.015
    revised_std: float = 0.12

    def __post_init__(self):
        if self.circles < 2 or self.windows < 3:
            raise ValueError("Need at least two circles and three windows")
        if min(self.evaluations_per_window, self.iterations_per_call) < 1:
            raise ValueError("Positive budgets required")
        if not (0 < self.local_std < self.revised_std < 1):
            raise ValueError("Require finite 0 < local_std < revised_std < 1")


@dataclass(frozen=True)
class Commitment:
    recipe: str = "local"
    emitted_at: int = 0


@dataclass
class State:
    seed: int
    incumbent: np.ndarray
    score: float
    commitment: Commitment = Commitment()
    window: int = 0
    revisions: int = 0
    evaluations: int = 0

    def clone(self):
        return replace(self, incumbent=self.incumbent.copy())


def initialize(seed, protocol):
    rng = np.random.default_rng(np.random.SeedSequence([seed, 731]))
    candidate = repair(
        np.column_stack(
            (
                rng.uniform(0.05, 0.95, (protocol.circles, 2)),
                np.full(protocol.circles, 0.01),
            )
        ).ravel()
    )
    check = verify(candidate.reshape(-1, 3)[:, :2], candidate[2::3])
    if not check["strictly_feasible"]:
        raise ValueError("Invalid initial construction")
    return State(seed, candidate, check["sum_radii"])


def advance(state, action, protocol, solver=solve):
    """Return a new state; an emission affects this next, unexecuted window."""
    if state.window >= protocol.windows or action not in ("KEEP", "REVISE"):
        raise ValueError("Invalid action or terminal state")
    if action == "REVISE" and (state.window == 0 or state.revisions):
        raise ValueError(
            "Revision requires a consumed initial commitment and is unique"
        )
    start = time.perf_counter()
    result = state.clone()
    if action == "REVISE":
        result.commitment = Commitment("broad", state.window)
        result.revisions += 1
    std = (
        protocol.local_std
        if result.commitment.recipe == "local"
        else protocol.revised_std
    )
    remaining = protocol.evaluations_per_window
    calls = []
    while remaining:
        # Identical standardized draws for every schedule at this window/call.
        rng = np.random.default_rng(
            np.random.SeedSequence([state.seed, state.window, len(calls), 913])
        )
        proposed = result.incumbent.reshape(-1, 3).copy()
        proposed[:, :2] += std * rng.normal(size=(protocol.circles, 2))
        candidate, metrics = solver(
            repair(proposed.ravel()), protocol.iterations_per_call, remaining
        )
        used = metrics["function_evaluations"]
        if not isinstance(used, (int, np.integer)) or not 0 < used <= remaining:
            raise ValueError("Solver violated evaluation budget")
        candidate = np.asarray(candidate).reshape(-1)
        if candidate.size != protocol.circles * 3:
            raise ValueError("Solver changed construction dimensions")
        checked = verify(candidate.reshape(-1, 3)[:, :2], candidate[2::3])
        if not checked["strictly_feasible"]:
            raise ValueError("Solver returned infeasible construction")
        if checked["sum_radii"] > result.score:
            result.incumbent = candidate.copy()
            result.score = checked["sum_radii"]
        remaining -= used
        calls.append(dict(metrics, independent_check=checked))
    result.window += 1
    result.evaluations += protocol.evaluations_per_window
    trace = dict(
        window=state.window,
        action=action,
        commitment=asdict(result.commitment),
        score_before=state.score,
        score_after=result.score,
        evaluations=result.evaluations,
        seconds_including_repair_and_verification=time.perf_counter() - start,
        calls=calls,
    )
    return result, trace


def collect(seed, protocol, solver=solve):
    """Exhaustive exact-one-replacement schedules plus separate never-revise.

    Prefixes are cloned from the same never-revise trajectory. All branches
    receive a full logical episode budget, including their shared prefix.
    """
    state = initialize(seed, protocol)
    checkpoints, prefix = [state.clone()], []
    for _ in range(protocol.windows):
        state, trace = advance(state, "KEEP", protocol, solver)
        checkpoints.append(state.clone())
        prefix.append(trace)

    def row(final, timing, trace):
        return dict(
            seed=seed,
            revision_before_window=timing,
            group="never_revise" if timing is None else "exact_one_replacement",
            emissions=1 + final.revisions,
            score=final.score,
            evaluations=final.evaluations,
            trace=trace,
            construction=final.incumbent.reshape(-1, 3).tolist(),
        )

    rows = [row(state, None, prefix)]
    for timing in range(1, protocol.windows):
        state = checkpoints[timing].clone()
        trace = list(prefix[:timing])
        while state.window < protocol.windows:
            state, event = advance(
                state,
                "REVISE" if state.window == timing else "KEEP",
                protocol,
                solver,
            )
            trace.append(event)
        rows.append(row(state, timing, trace))
    return rows


def validate_rows(rows, seed, protocol):
    """Replay geometry and accounting before accepting remote or resumed output."""
    expected = {None, *range(1, protocol.windows)}
    if (
        len(rows) != protocol.windows
        or {r["revision_before_window"] for r in rows} != expected
    ):
        raise ValueError("Incomplete or duplicate schedule output")
    for row in rows:
        timing = row["revision_before_window"]
        count = 1 if timing is None else 2
        if (
            row["seed"] != seed
            or row["emissions"] != count
            or row["evaluations"] != protocol.windows * protocol.evaluations_per_window
            or len(row["trace"]) != protocol.windows
        ):
            raise ValueError("Result identity or budget mismatch")
        construction = np.asarray(row["construction"])
        if construction.shape != (protocol.circles, 3):
            raise ValueError("Wrong construction shape")
        checked = verify(construction[:, :2], construction[:, 2])
        if not checked["strictly_feasible"] or checked["sum_radii"] != row["score"]:
            raise ValueError("Result geometry or score mismatch")
        previous = None
        for window, event in enumerate(row["trace"]):
            revised = timing is not None and window >= timing
            expected_commitment = dict(
                recipe="broad" if revised else "local",
                emitted_at=timing if revised else 0,
            )
            if (
                event["window"] != window
                or event["action"] != ("REVISE" if window == timing else "KEEP")
                or event["commitment"] != expected_commitment
                or event["evaluations"]
                != (window + 1) * protocol.evaluations_per_window
                or sum(c["function_evaluations"] for c in event["calls"])
                != protocol.evaluations_per_window
                or not np.isfinite([event["score_before"], event["score_after"]]).all()
                or event["score_after"] < event["score_before"]
                or (previous is not None and event["score_before"] != previous)
            ):
                raise ValueError("Invalid causal trace or accounting")
            previous = event["score_after"]
        if previous != row["score"]:
            raise ValueError("Terminal trace mismatch")


def summarize(rows):
    """Development-only retrospective ceiling; never select a test policy here."""
    seeds = sorted({r["seed"] for r in rows})
    timing_sets = [
        {
            r["revision_before_window"]
            for r in rows
            if r["seed"] == seed and r["group"] == "exact_one_replacement"
        }
        for seed in seeds
    ]
    if not seeds or not timing_sets[0] or any(s != timing_sets[0] for s in timing_sets):
        raise ValueError("Incomplete timing matrix")
    timings = sorted(timing_sets[0])
    matrix = []
    baseline = []
    for seed in seeds:
        selected = [r for r in rows if r["seed"] == seed]
        if len(selected) != len(timings) + 1:
            raise ValueError("Duplicate or missing rows")
        matrix.append(
            [
                next(r["score"] for r in selected if r["revision_before_window"] == t)
                for t in timings
            ]
        )
        baseline.append(
            next(r["score"] for r in selected if r["revision_before_window"] is None)
        )
    values = np.asarray(matrix)
    means = values.mean(axis=0)
    best = int(np.argmax(means))
    return dict(
        status="development_only_retrospective_opportunity_not_policy_performance",
        seeds=seeds,
        timings=timings,
        mean_scores=means.tolist(),
        development_selected_fixed_timing=timings[best],
        oracle_minus_best_fixed=float(values.max(axis=1).mean() - means[best]),
        best_fixed_minus_never=float(means[best] - np.mean(baseline)),
        per_seed_best_timing=[timings[i] for i in values.argmax(axis=1)],
        tie_rule="earliest timing; oracle is optimistic and uses terminal outcomes",
    )


def source_hashes():
    root = Path(__file__).resolve().parent
    return {
        name: hashlib.sha256((root / name).read_bytes()).hexdigest()
        for name in (
            "matched_revision.py",
            "pilot_math_revision.py",
            "check_math_packing.py",
            "modal_matched_revision.py",
        )
    }


def prepare(output, protocol, seeds):
    if not seeds or len(set(seeds)) != len(seeds) or any(s < 0 for s in seeds):
        raise ValueError("Unique nonnegative development seeds required")
    manifest = dict(
        schema=1,
        status="prepared_no_numerical_runs",
        split="development",
        protocol=asdict(protocol),
        seeds=seeds,
        sources=source_hashes(),
        budget="exact objective calls; unequal wall time, constraints and derivatives",
        optimizer_state="fresh SLSQP each call; no hidden cross-window state",
        random_state="counter-based seed/window/call; copied at boundaries",
        verifier="independent floating-point geometry; not a rigorous certificate",
        selection="exhaustive timing landscape; no trained or held-out policy claim",
    )
    output.mkdir(parents=True, exist_ok=False)
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seeds", type=int, default=12)
    args = parser.parse_args()
    if not 1 <= args.seeds <= 32:
        parser.error("Bounded development batch requires 1–32 seeds")
    prepare(args.output, Protocol(), list(range(2026170000, 2026170000 + args.seeds)))
    print("Manifest prepared; no numerical work or Modal calls performed.")


if __name__ == "__main__":
    main()
