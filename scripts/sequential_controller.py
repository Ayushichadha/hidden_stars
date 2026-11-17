"""Finite-horizon search-option control; sealed fresh-seed CPU experiment.

Models are exported as JSON arrays, never executable pickle. Every policy is
rolled out in the actual environment; old single-switch replay is not used.
"""

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from scripts.check_math_packing import verify
from scripts.matched_revision import Protocol, Commitment, initialize
from scripts.pilot_math_revision import repair, solve
from scripts.revision_hypotheses import geometry, hashes as previous_hashes, contrast

ACTIONS = ("local", "moderate", "restart")
STATIC = ("always_local", "always_moderate", "fixed4")
LEARNED = ("ridge_myopic", "ridge_sequential", "tree_myopic", "tree_sequential")
CONFIG = dict(ridge_alpha=10.0, trees=64, max_depth=5, min_samples_leaf=8)
FEATURE_NAMES = [
    "remaining_fraction",
    "score",
    "last_gain",
    "previous_gain",
    "stagnation_fraction",
    "option_age_fraction",
    "previous_local",
    "previous_moderate",
    "previous_restart",
    "radius_cv",
    "min_radius_over_mean",
    "contact_fraction",
    "contact_degree_std",
    "wall_contact_fraction",
    "max_grid_clearance",
    "occupied_area",
]


def observations(state, trace, protocol):
    gains = [e["score_after"] - e["score_before"] for e in trace]
    stagnant = 0
    for gain in reversed(gains):
        if gain > 1e-10:
            break
        stagnant += 1
    age = 0
    for event in reversed(trace):
        if event["action"] != state.commitment.recipe:
            break
        age += 1
    result = [
        (protocol.windows - state.window) / protocol.windows,
        state.score,
        gains[-1] if gains else 0.0,
        gains[-2] if len(gains) > 1 else 0.0,
        stagnant / protocol.windows,
        age / protocol.windows,
        *[float(bool(trace) and state.commitment.recipe == a) for a in ACTIONS],
        *geometry(state.incumbent),
    ]
    if not np.isfinite(result).all():
        raise ValueError("Nonfinite observation")
    return result


def step(state, action, protocol=Protocol(), solver=solve):
    if action not in ACTIONS or state.window >= protocol.windows:
        raise ValueError("Invalid option or terminal state")
    start = time.perf_counter()
    result = state.clone()
    changed = state.window == 0 or state.commitment.recipe != action
    result.commitment = Commitment(
        action, state.window if changed else state.commitment.emitted_at
    )
    result.revisions += int(state.window > 0 and changed)
    remaining = protocol.evaluations_per_window
    calls = []
    while remaining:
        rng = np.random.default_rng(
            np.random.SeedSequence([state.seed, state.window, len(calls), 913])
        )
        proposed = result.incumbent.reshape(-1, 3).copy()
        if action == "restart":
            proposed[:, :2] = rng.uniform(0.05, 0.95, (protocol.circles, 2))
            proposed[:, 2] = 0.01
        else:
            std = (
                protocol.local_std
                if action == "local"
                else np.sqrt(protocol.local_std * protocol.revised_std)
            )
            proposed[:, :2] += std * rng.normal(size=(protocol.circles, 2))
        candidate, metrics = solver(
            repair(proposed.ravel()), protocol.iterations_per_call, remaining
        )
        used = metrics["function_evaluations"]
        if not isinstance(used, (int, np.integer)) or not 0 < used <= remaining:
            raise ValueError("Solver violated evaluation cap")
        candidate = np.asarray(candidate).reshape(-1)
        if candidate.shape != (protocol.circles * 3,):
            raise ValueError("Wrong candidate shape")
        checked = verify(candidate.reshape(-1, 3)[:, :2], candidate[2::3])
        if not checked["strictly_feasible"]:
            raise ValueError("Infeasible option output")
        if checked["sum_radii"] > result.score:
            result.incumbent = candidate.copy()
            result.score = checked["sum_radii"]
        calls.append(dict(metrics, independent_check=checked))
        remaining -= used
    result.window += 1
    result.evaluations += protocol.evaluations_per_window
    return result, dict(
        window=state.window,
        action=action,
        score_before=state.score,
        score_after=result.score,
        evaluations=result.evaluations,
        worker_seconds=time.perf_counter() - start,
        calls=calls,
    )


def collect(seed, protocol=Protocol(), solver=solve):
    """Branch all actions at each visited state; random behavior chooses next state.

    Randomization is frozen data collection, not an outcome-driven trial search.
    Branches share state/noise, but future state coverage is only approximate.
    """
    state = initialize(seed, protocol)
    trace, windows = [], []
    rng = np.random.default_rng(np.random.SeedSequence([seed, 202624]))
    for t in range(protocol.windows):
        x = observations(state, trace, protocol)
        branches, states = [], []
        for action in ACTIONS:
            nxt, event = step(state, action, protocol, solver)
            states.append(nxt)
            branches.append(
                dict(
                    action=action,
                    x=x,
                    reward=nxt.score - state.score,
                    next_x=observations(nxt, trace + [event], protocol),
                    event=event,
                    construction=nxt.incumbent.reshape(-1, 3).tolist(),
                )
            )
        chosen = int(rng.integers(len(ACTIONS)))
        windows.append(
            dict(window=t, behavior_action=ACTIONS[chosen], branches=branches)
        )
        state = states[chosen]
        trace.append(branches[chosen]["event"])
    return dict(
        seed=seed,
        windows=windows,
        objective_evaluations=len(ACTIONS)
        * protocol.windows
        * protocol.evaluations_per_window,
    )


def check_transition(state, action, event, construction, protocol):
    z = np.asarray(construction)
    if z.shape != (protocol.circles, 3):
        raise ValueError("Wrong construction shape")
    checked = verify(z[:, :2], z[:, 2])
    if (
        not checked["strictly_feasible"]
        or checked["sum_radii"] != event["score_after"]
        or event["score_before"] != state.score
        or event["score_after"] < state.score
        or event["window"] != state.window
        or event["action"] != action
        or event["evaluations"] != state.evaluations + protocol.evaluations_per_window
        or sum(c["function_evaluations"] for c in event["calls"])
        != protocol.evaluations_per_window
        or not event["calls"]
        or any(c["function_evaluations"] <= 0 for c in event["calls"])
    ):
        raise ValueError("Invalid geometry, causal trace or accounting")
    nxt = state.clone()
    changed = state.window == 0 or state.commitment.recipe != action
    nxt.commitment = Commitment(
        action, state.window if changed else state.commitment.emitted_at
    )
    nxt.revisions += int(state.window > 0 and changed)
    nxt.window += 1
    nxt.evaluations = event["evaluations"]
    nxt.score = event["score_after"]
    nxt.incumbent = z.ravel().copy()
    return nxt


def validate_training(data, seed, protocol=Protocol()):
    if (
        data["seed"] != seed
        or len(data["windows"]) != protocol.windows
        or data["objective_evaluations"]
        != len(ACTIONS) * protocol.windows * protocol.evaluations_per_window
    ):
        raise ValueError("Training identity/budget mismatch")
    state = initialize(seed, protocol)
    trace = []
    rng = np.random.default_rng(np.random.SeedSequence([seed, 202624]))
    for t, row in enumerate(data["windows"]):
        if (
            row["window"] != t
            or [b["action"] for b in row["branches"]] != list(ACTIONS)
            or row["behavior_action"] != ACTIONS[int(rng.integers(len(ACTIONS)))]
        ):
            raise ValueError("Coverage or behavior mismatch")
        successors = {}
        for branch in row["branches"]:
            action, event = branch["action"], branch["event"]
            nxt = check_transition(
                state, action, event, branch["construction"], protocol
            )
            if (
                branch["x"] != observations(state, trace, protocol)
                or branch["next_x"] != observations(nxt, trace + [event], protocol)
                or branch["reward"] != nxt.score - state.score
            ):
                raise ValueError("Noncausal observation or reward")
            successors[action] = (nxt, event)
        state, event = successors[row["behavior_action"]]
        trace.append(event)


def regress(x, y, kind):
    from sklearn.ensemble import ExtraTreesRegressor
    from sklearn.preprocessing import StandardScaler

    if kind == "ridge":
        scaler = StandardScaler().fit(x)
        z = scaler.transform(x)
        intercept = float(np.mean(y))
        # einsum avoids spurious Accelerate BLAS matmul warnings on macOS.
        gram = np.einsum("ni,nj->ij", z, z)
        rhs = np.einsum("ni,n->i", z, y - intercept)
        coef = np.linalg.solve(gram + CONFIG["ridge_alpha"] * np.eye(z.shape[1]), rhs)
        return dict(
            kind=kind,
            mean=scaler.mean_.tolist(),
            scale=scaler.scale_.tolist(),
            coef=coef.tolist(),
            intercept=intercept,
        )
    model = ExtraTreesRegressor(
        n_estimators=CONFIG["trees"],
        max_depth=CONFIG["max_depth"],
        min_samples_leaf=CONFIG["min_samples_leaf"],
        random_state=731,
        n_jobs=1,
    ).fit(x, y)
    return dict(
        kind=kind,
        trees=[
            dict(
                left=e.tree_.children_left.tolist(),
                right=e.tree_.children_right.tolist(),
                feature=e.tree_.feature.tolist(),
                threshold=e.tree_.threshold.tolist(),
                value=e.tree_.value[:, 0, 0].tolist(),
            )
            for e in model.estimators_
        ],
    )


def predict(model, x):
    x = np.atleast_2d(np.asarray(x, dtype=float))
    if model["kind"] == "ridge":
        z = (x - np.asarray(model["mean"])) / np.asarray(model["scale"])
        result = np.einsum("ij,j->i", z, model["coef"]) + model["intercept"]
    else:
        # sklearn tree traversal casts features to float32; reproduce its thresholds.
        x = x.astype(np.float32)
        result = np.zeros(len(x))
        for tree in model["trees"]:
            left, right = np.asarray(tree["left"]), np.asarray(tree["right"])
            feature, threshold = np.asarray(tree["feature"]), np.asarray(
                tree["threshold"]
            )
            node = np.zeros(len(x), dtype=int)
            while True:
                live = np.flatnonzero(left[node] != -1)
                if not len(live):
                    break
                n = node[live]
                node[live] = np.where(
                    x[live, feature[n]] <= threshold[n], left[n], right[n]
                )
            result += np.asarray(tree["value"])[node]
        result /= len(model["trees"])
    if not np.isfinite(result).all():
        raise ValueError("Nonfinite prediction")
    return result


def fit(training, protocol=Protocol()):
    seeds = [d["seed"] for d in training]
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("Unique training seeds required")
    for data in training:
        validate_training(data, data["seed"], protocol)
    models = {}
    for name in LEARNED:
        kind, horizon = name.split("_")
        heads = [None] * protocol.windows
        for t in reversed(range(protocol.windows)):
            heads[t] = []
            for a in range(len(ACTIONS)):
                rows = [d["windows"][t]["branches"][a] for d in training]
                x = np.array([r["x"] for r in rows])
                # Milli-score units improve numerical readability; no reward clipping.
                y = np.array([1000 * r["reward"] for r in rows])
                if horizon == "sequential" and t + 1 < protocol.windows:
                    nx = np.array([r["next_x"] for r in rows])
                    y += np.max([predict(m, nx) for m in heads[t + 1]], axis=0)
                heads[t].append(regress(x, y, kind))
        models[name] = heads
    return dict(
        training_seeds=seeds,
        protocol=asdict(protocol),
        config=CONFIG,
        feature_names=FEATURE_NAMES,
        models=models,
    )


def choose(name, state, trace, bundle, protocol):
    start = time.perf_counter()
    x = observations(state, trace, protocol)
    values = None
    if name in LEARNED:
        values = [float(predict(m, x)[0]) for m in bundle["models"][name][state.window]]
        action = ACTIONS[int(np.argmax(values))]
    elif name == "always_local":
        action = "local"
    elif name == "always_moderate":
        action = "moderate"
    elif name == "fixed4":
        action = "local" if state.window < 4 else "moderate"
    elif name == "reactive":
        action = "moderate" if x[4] * protocol.windows >= 2 else "local"
    else:
        raise ValueError("Unknown policy")
    return action, dict(
        observation=x,
        q_milliscore=values,
        controller_seconds=time.perf_counter() - start,
    )


def rollout(seed, name, bundle, protocol=Protocol(), solver=solve):
    if seed in bundle["training_seeds"]:
        raise ValueError("Evaluation overlaps training")
    state, trace, decisions = initialize(seed, protocol), [], []
    start = time.perf_counter()
    for _ in range(protocol.windows):
        action, decision = choose(name, state, trace, bundle, protocol)
        state, event = step(state, action, protocol, solver)
        event["construction"] = state.incumbent.reshape(-1, 3).tolist()
        trace.append(event)
        decisions.append(decision)
    return dict(
        seed=seed,
        policy=name,
        score=state.score,
        evaluations=state.evaluations,
        switches=state.revisions,
        trace=trace,
        decisions=decisions,
        episode_seconds=time.perf_counter() - start,
    )


def validate_rollout(row, seed, name, protocol=Protocol()):
    if (
        row["seed"] != seed
        or row["policy"] != name
        or len(row["trace"]) != protocol.windows
        or len(row["decisions"]) != protocol.windows
    ):
        raise ValueError("Rollout identity mismatch")
    state, trace = initialize(seed, protocol), []
    for event, decision in zip(row["trace"], row["decisions"]):
        if (
            decision["observation"] != observations(state, trace, protocol)
            or event["action"] not in ACTIONS
        ):
            raise ValueError("Invalid decision observation")
        if name in LEARNED:
            q = decision["q_milliscore"]
            if (
                len(q) != len(ACTIONS)
                or not np.isfinite(q).all()
                or event["action"] != ACTIONS[int(np.argmax(q))]
            ):
                raise ValueError("Action does not match logged values")
        elif event["action"] != choose(name, state, trace, {}, protocol)[0]:
            raise ValueError("Static/reactive action mismatch")
        state = check_transition(
            state, event["action"], event, event["construction"], protocol
        )
        trace.append(event)
    if (
        row["score"] != state.score
        or row["evaluations"] != state.evaluations
        or row["switches"] != state.revisions
    ):
        raise ValueError("Terminal rollout mismatch")


def select_baseline(validation):
    means = {
        name: float(np.mean([r["policies"][name]["score"] for r in validation]))
        for name in STATIC
    }
    return dict(
        static=max(STATIC, key=lambda n: means[n]),
        validation_means=means,
        validation_seeds=[r["seed"] for r in validation],
    )


def summarize(rows, frozen):
    seeds = [r["seed"] for r in rows]
    if len(set(seeds)) != len(seeds) or set(seeds) & set(
        frozen["validation_seeds"] + frozen["training_seeds"]
    ):
        raise ValueError("Confirmation overlap or duplicates")
    names = [*LEARNED, frozen["static"], "reactive"]
    scores = {n: np.array([r["policies"][n]["score"] for r in rows]) for n in names}
    comparisons = {
        "H1_tree_sequential_minus_ridge_sequential": contrast(
            scores["tree_sequential"], scores["ridge_sequential"]
        ),
        "H2_tree_sequential_minus_tree_myopic": contrast(
            scores["tree_sequential"], scores["tree_myopic"]
        ),
    }
    # Two adjusted primary intervals. Static comparison is descriptive, not a third gate.
    comparisons["descriptive_tree_sequential_minus_selected_static"] = contrast(
        scores["tree_sequential"], scores[frozen["static"]]
    )
    return dict(
        seeds=seeds,
        selected_static=frozen["static"],
        comparisons=comparisons,
        means={n: float(v.mean()) for n, v in scores.items()},
        mean_switches={
            n: float(np.mean([r["policies"][n]["switches"] for r in rows]))
            for n in names
        },
        mean_episode_seconds={
            n: float(np.mean([r["policies"][n]["episode_seconds"] for r in rows]))
            for n in names
        },
        mean_controller_seconds={
            n: float(
                np.mean(
                    [
                        sum(
                            d["controller_seconds"]
                            for d in r["policies"][n]["decisions"]
                        )
                        for r in rows
                    ]
                )
            )
            for n in names
        },
        action_counts={
            n: {
                a: sum(
                    e["action"] == a for r in rows for e in r["policies"][n]["trace"]
                )
                for a in ACTIONS
            }
            for n in names
        },
    )


def hashes():
    root = Path(__file__).resolve().parent
    return dict(
        previous_hashes(),
        **{
            n: hashlib.sha256((root / n).read_bytes()).hexdigest()
            for n in ("sequential_controller.py", "modal_sequential_controller.py")
        }
    )


def specification():
    return dict(
        schema=1,
        protocol=asdict(Protocol()),
        sources=hashes(),
        config=CONFIG,
        actions=list(ACTIONS),
        features=FEATURE_NAMES,
        training_seeds=list(range(2026240000, 2026240096)),
        validation_seeds=list(range(2026250000, 2026250016)),
        confirmation_seeds=list(range(2026260000, 2026260048)),
        learned=list(LEARNED),
        static_candidates=list(STATIC),
        reactive="two stagnant windows -> moderate, otherwise local",
        training="3 action branches at each state; seeded uniform behavior; 96 independent paths, 2304 transitions",
        fitting="8 time-specific and 3 action-specific heads; alpha=10; ExtraTrees 64 depth5 leaf8; no hyperparameter selection; ties local/moderate/restart",
        reward="verified incumbent score increments times 1000; gamma=1 sequential, gamma=0 myopic",
        selection="validation selects static comparator only; four learned policies fixed from training",
        hypotheses=[
            "H1 tree-sequential exceeds ridge-sequential",
            "H2 tree-sequential exceeds tree-myopic",
        ],
        success="each primary mean >= .0005 and paired 97.5% bootstrap lower bound >0; 20000 paired seed resamples; static gap descriptive",
        limitations="compressed observation may not be Markov; approximate FQI support; one problem and budget; no learned policy promotion",
        cost=dict(
            previous_workspace_USD=0.18,
            hard_function_calls=164,
            timeout_seconds=600,
            cpu_cores=1,
            memory_GiB=2,
            rate_USD_per_second=0.00001754,
            maximum_function_execution_USD=1.725936,
            reserve_USD=0.50,
            overall_budget_USD=10.0,
            automatic_retries=0,
        ),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", type=Path, required=True)
    args = parser.parse_args()
    args.prepare.mkdir(parents=True, exist_ok=False)
    (args.prepare / "manifest.json").write_text(
        json.dumps(specification(), indent=2, allow_nan=False) + "\n"
    )
    print("Frozen sequential protocol prepared; no numerical collection.")
