"""Frozen two-hypothesis follow-up: geometry observations and moderate revision.

H1 isolates observations at the original broad action. H2 isolates revision
strength using validation-selected fixed clocks. No old confirmation seeds recur.
"""

import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import numpy as np

from scripts.matched_revision import (
    Protocol,
    advance,
    initialize,
    source_hashes,
    validate_rows,
)
from scripts.pilot_math_revision import solve
from scripts.predict_revision import features as progress_features

RECIPES = {"broad": 0.12, "moderate": float(np.sqrt(0.015 * 0.12))}
GEOMETRY_NAMES = [
    "radius_cv",
    "min_radius_over_mean",
    "contact_fraction",
    "contact_degree_std",
    "wall_contact_fraction",
    "max_grid_clearance",
    "occupied_area",
]


def geometry(candidate):
    z = np.asarray(candidate).reshape(-1, 3)
    c = z[:, :2]
    r = z[:, 2]
    n = len(r)
    distance = np.linalg.norm(c[:, None, :] - c[None, :, :], axis=-1)
    gaps = distance - r[:, None] - r[None, :]
    contact = (gaps <= 1e-4) & ~np.eye(n, dtype=bool)
    wall = np.minimum(c, 1 - c) - r[:, None]
    grid = np.array(
        [(x, y) for x in np.linspace(0.05, 0.95, 9) for y in np.linspace(0.05, 0.95, 9)]
    )
    clearance = (np.linalg.norm(grid[:, None, :] - c[None, :, :], axis=-1) - r).min(
        axis=1
    )
    values = [
        r.std() / max(r.mean(), 1e-12),
        r.min() / max(r.mean(), 1e-12),
        contact.sum() / (n * (n - 1)),
        contact.sum(axis=1).std(),
        np.mean(wall.min(axis=1) <= 1e-4),
        clearance.max(),
        np.pi * np.sum(r * r),
    ]
    if not np.isfinite(values).all():
        raise ValueError("Nonfinite geometry")
    return [float(v) for v in values]


def collect(seed, protocol=Protocol(), solver=solve):
    state = initialize(seed, protocol)
    checkpoints = [state.clone()]
    trace = []
    for _ in range(protocol.windows):
        state, event = advance(state, "KEEP", protocol, solver)
        event["geometry_after"] = geometry(state.incumbent)
        trace.append(event)
        checkpoints.append(state.clone())

    def row(final, timing, events):
        return dict(
            seed=seed,
            revision_before_window=timing,
            group="never_revise" if timing is None else "exact_one_replacement",
            emissions=1 + final.revisions,
            score=final.score,
            evaluations=final.evaluations,
            trace=events,
            construction=final.incumbent.reshape(-1, 3).tolist(),
        )

    base = row(state, None, trace)
    families = {}
    for name, std in RECIPES.items():
        p = replace(protocol, revised_std=std)
        rows = [base]
        for timing in range(1, protocol.windows):
            state = checkpoints[timing].clone()
            events = list(trace[:timing])
            while state.window < protocol.windows:
                state, event = advance(
                    state, "REVISE" if state.window == timing else "KEEP", p, solver
                )
                events.append(event)
            rows.append(row(state, timing, events))
        families[name] = rows
    return dict(seed=seed, families=families, recipe_scales=RECIPES)


def validate(data, seed, protocol=Protocol()):
    if data["seed"] != seed or data["recipe_scales"] != RECIPES:
        raise ValueError("Identity or recipe mismatch")
    for name, std in RECIPES.items():
        rows = data["families"][name]
        validate_rows(rows, seed, replace(protocol, revised_std=std))
        for event in rows[0]["trace"]:
            if (
                len(event["geometry_after"]) != len(GEOMETRY_NAMES)
                or not np.isfinite(event["geometry_after"]).all()
            ):
                raise ValueError("Invalid observed geometry")
    if data["families"]["broad"][0] != data["families"]["moderate"][0]:
        raise ValueError("Counterfactual families do not share a prefix")


def feature(trace, t, mode):
    x = progress_features(trace, t, mode != "time")
    if mode == "geometry":
        g = trace[t - 1]["geometry_after"]
        x = x + g + np.outer(np.eye(7)[t - 1], g).ravel().tolist()
    return x


def dataset(episodes, recipe, mode):
    x = []
    y = []
    for episode in episodes:
        rows = episode["families"][recipe]
        base = rows[0]
        lookup = {r["revision_before_window"]: r for r in rows[1:]}
        for t in range(1, 7):
            x.append(feature(base["trace"], t, mode))
            y.append(
                lookup[t]["score"]
                - np.mean([lookup[j]["score"] for j in range(t + 1, 8)])
            )
    return np.asarray(x), np.asarray(y)


def fit(episodes, recipe, mode, alpha):
    x, y = dataset(episodes, recipe, mode)
    mean = x.mean(axis=0)
    scale = x.std(axis=0)
    scale[scale < 1e-12] = 1
    z = (x - mean) / scale
    weights = np.linalg.solve(
        np.einsum("ni,nj->ij", z, z) + alpha * np.eye(z.shape[1]),
        np.einsum("ni,n->i", z, y - y.mean()),
    )
    return dict(
        mean=mean.tolist(),
        scale=scale.tolist(),
        weights=weights.tolist(),
        intercept=float(y.mean()),
        mode=mode,
        alpha=alpha,
    )


def predict(model, x):
    standardized = (np.asarray(x) - model["mean"]) / model["scale"]
    result = (
        np.einsum("...i,i->...", standardized, model["weights"]) + model["intercept"]
    )
    if not np.isfinite(result).all():
        raise ValueError("Nonfinite prediction")
    return result


def choose(trace, policy):
    if policy["kind"] == "fixed":
        return policy["timing"]
    for t in range(1, 7):
        if policy["kind"] == "reactive":
            k = policy["patience"]
            past = trace[:t]
            trigger = len(past) >= k and all(
                e["score_after"] - e["score_before"] <= 1e-7 for e in past[-k:]
            )
        else:
            trigger = (
                predict(policy["model"], feature(trace, t, policy["model"]["mode"]))
                > policy["threshold"]
            )
        if trigger:
            return t
    return 7


def score(episodes, policy):
    values = []
    timings = []
    for e in episodes:
        rows = e["families"][policy["recipe"]]
        t = choose(rows[0]["trace"], policy)
        values.append(
            next(r["score"] for r in rows if r["revision_before_window"] == t)
        )
        timings.append(t)
    return np.array(values), timings


def train(training, validation):
    if {e["seed"] for e in training} & {e["seed"] for e in validation}:
        raise ValueError("Split overlap")
    policies = {}
    for recipe in RECIPES:
        for mode in ("time", "progress", "geometry"):
            options = []
            for alpha in (0.1, 1.0, 10.0, 100.0):
                model = fit(training, recipe, mode, alpha)
                for threshold in (0.0, 0.0005, 0.001):
                    options.append(
                        dict(
                            kind="ridge",
                            recipe=recipe,
                            model=model,
                            threshold=threshold,
                        )
                    )
            policies[f"{mode}_{recipe}"] = max(
                options, key=lambda p: score(validation, p)[0].mean()
            )
        policies[f"fixed_{recipe}"] = max(
            [dict(kind="fixed", recipe=recipe, timing=t) for t in range(1, 8)],
            key=lambda p: score(validation, p)[0].mean(),
        )
        policies[f"reactive_{recipe}"] = max(
            [dict(kind="reactive", recipe=recipe, patience=k) for k in (1, 2, 3)],
            key=lambda p: score(validation, p)[0].mean(),
        )
    return dict(
        policies=policies,
        training_seeds=[e["seed"] for e in training],
        validation_seeds=[e["seed"] for e in validation],
        validation_means={
            k: float(score(validation, p)[0].mean()) for k, p in policies.items()
        },
    )


def contrast(a, b):
    d = a - b
    rng = np.random.default_rng(6802)
    bootstrap = rng.choice(d, (20000, len(d)), replace=True).mean(axis=1)
    bounds = np.quantile(bootstrap, [0.0125, 0.9875]).tolist()
    return dict(
        mean=float(d.mean()),
        paired_seed_97_5_interval=bounds,
        success=float(d.mean()) >= 0.0005 and bounds[0] > 0,
        wins=int((d > 1e-12).sum()),
        losses=int((d < -1e-12).sum()),
        ties=int((abs(d) <= 1e-12).sum()),
    )


def evaluate(episodes, frozen):
    if {e["seed"] for e in episodes} & set(
        frozen["training_seeds"] + frozen["validation_seeds"]
    ):
        raise ValueError("Confirmation overlap")
    values = {}
    timings = {}
    diagnostics = {}
    for name, p in frozen["policies"].items():
        values[name], timings[name] = score(episodes, p)
        if p["kind"] == "ridge":
            x, y = dataset(episodes, p["recipe"], p["model"]["mode"])
            pred = predict(p["model"], x)
            diagnostics[name] = dict(
                mse=float(np.mean((pred - y) ** 2)),
                sign_accuracy=float(np.mean((pred > 0) == (y > 0))),
                nonpositive_baseline=float(np.mean(y <= 0)),
            )
    values["never"] = np.array([e["families"]["broad"][0]["score"] for e in episodes])
    for recipe in RECIPES:
        values[f"oracle_{recipe}"] = np.array(
            [max(r["score"] for r in e["families"][recipe][1:]) for e in episodes]
        )
    return dict(
        seeds=[e["seed"] for e in episodes],
        mean_scores={k: float(v.mean()) for k, v in values.items()},
        timings=timings,
        prediction=diagnostics,
        H1_geometry_vs_progress_broad=contrast(
            values["geometry_broad"], values["progress_broad"]
        ),
        H2_fixed_moderate_vs_fixed_broad=contrast(
            values["fixed_moderate"], values["fixed_broad"]
        ),
        secondary_geometry_moderate_vs_progress_moderate=contrast(
            values["geometry_moderate"], values["progress_moderate"]
        ),
        secondary_geometry_moderate_vs_fixed_moderate=contrast(
            values["geometry_moderate"], values["fixed_moderate"]
        ),
        secondary_geometry_broad_vs_time_broad=contrast(
            values["geometry_broad"], values["time_broad"]
        ),
        primary_intervals="97.5% paired seed bootstrap intervals, Bonferroni for two primary hypotheses; secondary exploratory",
    )


def hashes():
    result = source_hashes()
    for name in (
        "predict_revision.py",
        "revision_hypotheses.py",
        "modal_revision_hypotheses.py",
    ):
        result[name] = hashlib.sha256(
            Path(__file__).with_name(name).read_bytes()
        ).hexdigest()
    return result


def prepare(output):
    manifest = dict(
        sources=hashes(),
        protocol=vars(Protocol()),
        recipes=RECIPES,
        training_seeds=list(range(2026200000, 2026200024)),
        validation_seeds=list(range(2026210000, 2026210012)),
        confirmation_seeds=list(range(2026220000, 2026220048)),
        geometry_features=GEOMETRY_NAMES,
        H1="Geometry improves terminal policy score over progress-only with broad action fixed",
        H2="Geometric-midpoint perturbation improves validation-selected fixed-policy score over broad",
        success="Each primary mean >= .0005 and paired 97.5% interval lower bound > 0; Bonferroni two hypotheses",
        design="24/12/48 fresh seeds; all choices frozen before confirmation; no retuning",
        worker="unchanged SLSQP, 640 objective calls per policy, shared prefixes, one replacement",
        geometry_contract="pair/wall contacts at 1e-4; fixed 9x9 clearance grid; current incumbent only",
        selection="same ridge .1/1/10/100 and threshold 0/.0005/.001; validation final score; earliest option breaks ties",
        resource_cap="84 collection and 2 analysis calls, each 600s, 1 CPU/2GiB, no retries; max 4 concurrent collections",
        maximum_function_USD=0.905064,
        interpretation="H2 is worker/revision improvement, not learned-controller benefit; causal replay, not live overhead test",
    )
    output.mkdir(parents=True, exist_ok=False)
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    prepare(parser.parse_args().output)
    print("Frozen hypotheses prepared; no numerical runs.")
