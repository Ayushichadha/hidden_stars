"""Predeclared timing prediction pilot; causal replay under frozen commitments.

Only past-prefix features enter a decision. Terminal branch scores are labels
and evaluation outcomes, never controller inputs. All fitting runs on Modal CPU.
"""

import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from scripts.matched_revision import Protocol, source_hashes, validate_rows


def features(trace, timing, state_aware):
    past = trace[:timing]
    clock = np.eye(7)[timing - 1].tolist()
    if not state_aware:
        return clock
    gains = [e["score_after"] - e["score_before"] for e in past]
    stagnant = 0
    for gain in reversed(gains):
        if gain > 1e-7:
            break
        stagnant += 1
    state = [
        past[-1]["score_after"],
        gains[-1],
        gains[-2] if len(gains) > 1 else 0.0,
        stagnant / 7,
    ]
    # Shared state slopes plus time-specific slopes; regularized together.
    return clock + state + np.outer(clock, state).ravel().tolist()


def samples(episodes, state_aware, target="terminal"):
    x, y = [], []
    for rows in episodes:
        base = next(r for r in rows if r["revision_before_window"] is None)
        branches = {
            r["revision_before_window"]: r
            for r in rows
            if r["revision_before_window"] is not None
        }
        for t in range(1, 7):
            x.append(features(base["trace"], t, state_aware))
            if target == "terminal":
                # Expected advantage over waiting then revising uniformly later.
                y.append(
                    branches[t]["score"]
                    - np.mean([branches[j]["score"] for j in range(t + 1, 8)])
                )
            else:
                y.append(
                    branches[t]["trace"][t]["score_after"]
                    - base["trace"][t]["score_after"]
                )
    return np.asarray(x), np.asarray(y)


def fit(episodes, state_aware, target, alpha):
    x, y = samples(episodes, state_aware, target)
    mean, scale = x.mean(axis=0), x.std(axis=0)
    scale[scale < 1e-12] = 1
    z = (x - mean) / scale
    weights = np.linalg.solve(
        np.einsum("ni,nj->ij", z, z) + alpha * np.eye(z.shape[1]),
        np.einsum("ni,n->i", z, y - y.mean()),
    )
    return dict(
        state_aware=state_aware,
        target=target,
        alpha=alpha,
        mean=mean.tolist(),
        scale=scale.tolist(),
        weights=weights.tolist(),
        intercept=float(y.mean()),
        threshold=0.0,
    )


def predict(model, x):
    return ((np.asarray(x) - model["mean"]) / model["scale"]) @ np.array(
        model["weights"]
    ) + model["intercept"]


def choose(trace, policy):
    if policy["kind"] == "fixed":
        return policy["timing"]
    for t in range(1, 7):
        if policy["kind"] == "reactive":
            gains = [e["score_after"] - e["score_before"] for e in trace[:t]]
            k = policy["patience"]
            trigger = len(gains) >= k and all(g <= 1e-7 for g in gains[-k:])
        else:
            model = policy["model"]
            trigger = (
                predict(model, features(trace, t, model["state_aware"]))
                > model["threshold"]
            )
        if trigger:
            return t
    return 7  # Mandatory replacement preserves exact intervention count.


def scores(episodes, policy):
    selected, values = [], []
    for rows in episodes:
        base = next(r for r in rows if r["revision_before_window"] is None)
        timing = choose(base["trace"], policy)
        selected.append(timing)
        values.append(
            next(r["score"] for r in rows if r["revision_before_window"] == timing)
        )
    return np.asarray(values), selected


def train(training, validation):
    if {r[0]["seed"] for r in training} & {r[0]["seed"] for r in validation}:
        raise ValueError("Training/validation overlap")
    policies = {}
    for name, aware, target in [
        ("time_terminal", False, "terminal"),
        ("state_terminal", True, "terminal"),
        ("state_local", True, "local"),
    ]:
        candidates = []
        for alpha in (0.1, 1.0, 10.0, 100.0):
            model = fit(training, aware, target, alpha)
            for threshold in (0.0, 0.0005, 0.001):
                candidate = dict(kind="ridge", model=dict(model, threshold=threshold))
                candidates.append(candidate)
        policies[name] = max(
            candidates, key=lambda p: float(scores(validation, p)[0].mean())
        )
    policies["fixed"] = max(
        [dict(kind="fixed", timing=t) for t in range(1, 8)],
        key=lambda p: float(scores(validation, p)[0].mean()),
    )
    policies["reactive"] = max(
        [dict(kind="reactive", patience=k) for k in (1, 2, 3)],
        key=lambda p: float(scores(validation, p)[0].mean()),
    )
    return dict(
        policies=policies,
        training_seeds=[r[0]["seed"] for r in training],
        validation_seeds=[r[0]["seed"] for r in validation],
        selection="validation mean terminal score; first candidate breaks ties",
        validation_means={
            n: float(scores(validation, p)[0].mean()) for n, p in policies.items()
        },
    )


def interval(values):
    values = np.asarray(values)
    rng = np.random.default_rng(6711)
    draws = rng.choice(values, (10000, len(values)), replace=True).mean(axis=1)
    return dict(
        mean=float(values.mean()),
        paired_seed_bootstrap_95=np.quantile(draws, [0.025, 0.975]).tolist(),
    )


def evaluate(episodes, frozen):
    if {r[0]["seed"] for r in episodes} & set(
        frozen["training_seeds"] + frozen["validation_seeds"]
    ):
        raise ValueError("Confirmation overlap")
    start = time.perf_counter()
    outcomes, timings = {}, {}
    for name, policy in frozen["policies"].items():
        outcomes[name], timings[name] = scores(episodes, policy)
    outcomes["never"] = np.array(
        [
            next(r["score"] for r in rows if r["revision_before_window"] is None)
            for rows in episodes
        ]
    )
    outcomes["uniform_random_expected"] = np.array(
        [
            np.mean(
                [r["score"] for r in rows if r["revision_before_window"] is not None]
            )
            for rows in episodes
        ]
    )
    outcomes["oracle"] = np.array(
        [
            max(r["score"] for r in rows if r["revision_before_window"] is not None)
            for rows in episodes
        ]
    )
    prediction = {}
    for name in ("time_terminal", "state_terminal", "state_local"):
        model = frozen["policies"][name]["model"]
        x, target = samples(episodes, model["state_aware"], "terminal")
        estimated = predict(model, x)
        prediction[name] = dict(
            terminal_target_mse=float(np.mean((estimated - target) ** 2)),
            positive_target_accuracy=float(np.mean((estimated > 0) == (target > 0))),
            majority_negative_accuracy=float(np.mean(target <= 0)),
        )
    primary = interval(outcomes["state_terminal"] - outcomes["time_terminal"])
    return dict(
        seeds=[r[0]["seed"] for r in episodes],
        mean_scores={k: float(v.mean()) for k, v in outcomes.items()},
        timings=timings,
        prediction=prediction,
        primary_state_minus_time=primary,
        state_minus_fixed=interval(outcomes["state_terminal"] - outcomes["fixed"]),
        state_minus_reactive=interval(
            outcomes["state_terminal"] - outcomes["reactive"]
        ),
        state_minus_local_target=interval(
            outcomes["state_terminal"] - outcomes["state_local"]
        ),
        practical_threshold=0.0005,
        primary_success=primary["paired_seed_bootstrap_95"][0] > 0
        and primary["mean"] >= 0.0005,
        evaluation_seconds=time.perf_counter() - start,
        interpretation="causal replay of complete deterministic branches; not live controller wall-time comparison",
    )


def hashes():
    result = source_hashes()
    for name in ("predict_revision.py", "modal_predict_revision.py"):
        result[name] = hashlib.sha256(
            Path(__file__).with_name(name).read_bytes()
        ).hexdigest()
    return result


def prepare(output):
    manifest = dict(
        schema=1,
        sources=hashes(),
        protocol=vars(Protocol()),
        training_seeds=list(range(2026170000, 2026170024)),
        validation_seeds=list(range(2026180000, 2026180012)),
        confirmation_seeds=list(range(2026190000, 2026190024)),
        primary="state-terminal minus time-terminal final verified score",
        success="paired seed bootstrap lower bound > 0 and mean >= 0.0005",
        samples="24 training, 12 validation, 24 confirmation; exploratory precision-limited pilot",
        max_new_collection_calls=48,
        max_analysis_calls=2,
        max_function_seconds=30000,
        estimated_max_function_USD=0.5262,
        target="revise now terminal score minus mean of all strictly later timings",
        features="time one-hot; current score, latest gain, previous gain, stagnation length; time interactions",
        selection="alpha .1/1/10/100; threshold 0/.0005/.001; validation terminal mean; no refit",
        confirmation="collect only after frozen policies saved; evaluate once; no tuning on confirmation",
    )
    output.mkdir(parents=True, exist_ok=False)
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def execute(output, collect_remote, analyze_remote):
    manifest = json.loads((output / "manifest.json").read_text())
    if manifest["sources"] != hashes():
        raise RuntimeError("Source changed since preparation")
    groups = [
        manifest[k + "_seeds"] for k in ("training", "validation", "confirmation")
    ]
    if [len(g) for g in groups] != [24, 12, 24] or len(set(sum(groups, []))) != 60:
        raise ValueError("Invalid or overlapping bounded split allocation")
    if manifest["protocol"] != vars(Protocol()):
        raise ValueError("Frozen worker protocol changed")
    identity = hashlib.sha256((output / "manifest.json").read_bytes()).hexdigest()
    lock = output / "dispatch.lock"
    with lock.open("x") as f:
        f.write(identity)

    def call(name, fn, *args):
        path = output / (name + ".json")
        pending = output / (name + ".pending")
        if pending.exists():
            raise RuntimeError("Inspect interrupted Modal call before recovery")
        if path.exists():
            saved = json.loads(path.read_text())
            if saved["manifest_sha256"] != identity:
                raise RuntimeError("Result manifest mismatch")
            return saved["result"]
        pending.write_text(identity)
        value = fn(*args)
        temp = path.with_suffix(".tmp")
        temp.write_text(
            json.dumps(
                dict(manifest_sha256=identity, result=value), indent=2, allow_nan=False
            )
            + "\n"
        )
        temp.replace(path)
        pending.unlink()
        return value

    def gather(split):
        episodes = []
        for seed in manifest[split + "_seeds"]:
            prior = Path("outputs/matched-revision-v1") / f"seed-{seed}.json"
            if split == "training" and prior.exists():
                old_manifest = json.loads((prior.parent / "manifest.json").read_text())
                if (
                    old_manifest["sources"] != source_hashes()
                    or old_manifest["protocol"] != manifest["protocol"]
                ):
                    raise RuntimeError("Historical source/protocol mismatch")
                data = json.loads(prior.read_text())
            else:
                data = call(
                    f"{split}-{seed}",
                    collect_remote,
                    manifest["protocol"],
                    seed,
                    source_hashes(),
                )
            validate_rows(data["rows"], seed, Protocol())
            episodes.append(data["rows"])
            print(f"{split}: seed {seed} validated", flush=True)
        return episodes

    try:
        training = gather("training")
        validation = gather("validation")
        frozen = call(
            "frozen-policy", analyze_remote, "train", training, validation, hashes()
        )
        confirmation = gather("confirmation")
        return call(
            "confirmation-summary",
            analyze_remote,
            "evaluate",
            confirmation,
            frozen,
            hashes(),
        )
    finally:
        lock.unlink()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.output)
    print("Prepared frozen prediction protocol; no numerical runs.")
