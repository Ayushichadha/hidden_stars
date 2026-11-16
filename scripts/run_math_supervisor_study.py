"""Frozen-split paired-decision study; outputs are local research artifacts."""

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import hashlib
import numpy as np
import torch
from scripts.meta_search_agent import search_window
from scripts.pilot_math_revision import repair, solve

FEATURES = [
    "checkpoint",
    "score",
    "last_gain",
    "radius_std",
    "radius_min",
    "radius_max",
    "occupied_area",
    "center_spread",
]


def collect(task):
    split, seed = task
    rng = np.random.default_rng(seed)
    x = repair(
        np.column_stack((rng.uniform(0.05, 0.95, (26, 2)), np.full(26, 0.01))).ravel()
    )
    x, metrics = solve(x, 40, 30)
    if metrics["function_evaluations"] < 30:
        x, _ = search_window(x, "local", seed, 0, 30 - metrics["function_evaluations"])
    rows = []
    last_gain = 0.0
    for checkpoint in range(3):
        z = x.reshape(-1, 3)
        radii = z[:, 2]
        features = [
            checkpoint,
            float(radii.sum()),
            last_gain,
            float(radii.std()),
            float(radii.min()),
            float(radii.max()),
            float(np.pi * (radii**2).sum()),
            float(z[:, :2].std()),
        ]
        outcomes = {}
        for action in ("local", "broad"):
            y, steps = search_window(x, action, seed, checkpoint + 10, 60)
            y, tail = search_window(y, "local", seed, checkpoint + 20, 60)
            assert sum(s["function_evaluations"] for s in steps + tail) == 120
            assert all(s["strictly_feasible"] for s in steps + tail)
            outcomes[action] = float(y[2::3].sum())
        rows.append(
            dict(
                split=split,
                seed=seed,
                checkpoint=checkpoint,
                features=features,
                outcomes=outcomes,
                delta=outcomes["broad"] - outcomes["local"],
                construction=x.tolist(),
            )
        )
        before = float(radii.sum())
        if checkpoint < 2:
            x, _ = search_window(x, "local", seed, checkpoint + 1, 60)
            last_gain = float(x[2::3].sum()) - before
    return rows


def arrays(rows):
    return np.array([r["features"] for r in rows]), np.array([r["delta"] for r in rows])


def value(rows, actions):
    return np.array(
        [r["outcomes"]["broad" if a else "local"] for r, a in zip(rows, actions)]
    )


def fit(train, validation, out):
    torch.set_num_threads(1)
    x, y = arrays(train)
    vx, vy = arrays(validation)
    mean = x.mean(0)
    scale = x.std(0)
    scale[scale < 1e-8] = 1
    x = (x - mean) / scale
    vx = (vx - mean) / scale
    yscale = max(float(y.std()), 1e-8)
    models = {}
    for family in ("clock", "ridge", "neural"):
        candidates = []
        for penalty in (0.01, 0.1, 1.0):
            if family == "clock":
                # One mean downstream advantage per checkpoint, shrunk to overall mean.
                means = np.array(
                    [
                        (
                            y[np.array([r["checkpoint"] == k for r in train])].sum()
                            + penalty * y.mean()
                        )
                        / (sum(r["checkpoint"] == k for r in train) + penalty)
                        for k in range(3)
                    ]
                )
                prediction = np.array([means[r["checkpoint"]] for r in validation])
                model = dict(kind=family, means=means.tolist(), penalty=penalty)
            elif family == "ridge":
                a = np.column_stack((np.ones(len(x)), x))
                va = np.column_stack((np.ones(len(vx)), vx))
                regularizer = np.eye(a.shape[1]) * penalty
                regularizer[0, 0] = 0
                beta = np.linalg.solve(
                    np.einsum("ni,nj->ij", a, a) + regularizer,
                    np.einsum("ni,n->i", a, y / yscale),
                )
                if not np.isfinite(beta).all():
                    raise FloatingPointError("Nonfinite regression coefficients")
                prediction = np.einsum("ni,i->n", va, beta) * yscale
                model = dict(kind=family, beta=beta.tolist(), penalty=penalty)
            else:
                states = []
                predictions = []
                for initialization in (11, 22, 33):
                    torch.manual_seed(initialization)
                    net = torch.nn.Sequential(
                        torch.nn.Linear(len(FEATURES), 16),
                        torch.nn.Tanh(),
                        torch.nn.Linear(16, 1),
                    )
                    optimizer = torch.optim.AdamW(
                        net.parameters(), lr=0.01, weight_decay=penalty
                    )
                    tx = torch.tensor(x, dtype=torch.float32)
                    ty = torch.tensor(y / yscale, dtype=torch.float32)
                    for _ in range(600):
                        optimizer.zero_grad()
                        loss = ((net(tx).squeeze(1) - ty) ** 2).mean()
                        loss.backward()
                        optimizer.step()
                    with torch.no_grad():
                        predictions.append(
                            net(torch.tensor(vx, dtype=torch.float32))
                            .squeeze(1)
                            .numpy()
                            * yscale
                        )
                    states.append(
                        {k: v.detach().tolist() for k, v in net.state_dict().items()}
                    )
                prediction = np.mean(predictions, axis=0)
                model = dict(kind=family, states=states, penalty=penalty)
            metric = float(value(validation, prediction > 0).mean())
            candidates.append((metric, model))
        selected = max(candidates, key=lambda item: item[0])
        models[family] = selected[1]
        models[family]["validation_value"] = selected[0]
    models["normalization"] = dict(
        mean=mean.tolist(), scale=scale.tolist(), yscale=yscale
    )
    (out / "frozen_models.json").write_text(json.dumps(models, indent=2))
    return models


def predict(model, rows, normalization):
    x, _ = arrays(rows)
    x = (x - np.array(normalization["mean"])) / np.array(normalization["scale"])
    if model["kind"] == "clock":
        return np.array([model["means"][r["checkpoint"]] for r in rows]) > 0
    if model["kind"] == "ridge":
        return (
            np.einsum(
                "ni,i->n",
                np.column_stack((np.ones(len(x)), x)),
                np.array(model["beta"]),
            )
            > 0
        )
    predictions = []
    for state in model["states"]:
        net = torch.nn.Sequential(
            torch.nn.Linear(len(FEATURES), 16), torch.nn.Tanh(), torch.nn.Linear(16, 1)
        )
        net.load_state_dict({k: torch.tensor(v) for k, v in state.items()})
        with torch.no_grad():
            predictions.append(
                net(torch.tensor(x, dtype=torch.float32)).squeeze(1).numpy()
            )
    return np.mean(predictions, axis=0) > 0


def evaluate(models, rows):
    choices = {
        k: predict(models[k], rows, models["normalization"])
        for k in ("clock", "ridge", "neural")
    }
    choices.update(
        local=np.zeros(len(rows), dtype=bool),
        broad=np.ones(len(rows), dtype=bool),
        stagnation=np.array(
            [r["checkpoint"] > 0 and r["features"][2] <= 1e-7 for r in rows]
        ),
        oracle=np.array([r["delta"] > 0 for r in rows]),
    )
    values = {k: value(rows, v) for k, v in choices.items()}
    seeds = sorted({r["seed"] for r in rows})
    result = {}
    for name, scores in values.items():
        comparisons = {}
        for baseline in ("clock", "local", "ridge"):
            diffs = scores - values[baseline]
            grouped = np.array(
                [diffs[np.array([r["seed"] == s for r in rows])].mean() for s in seeds]
            )
            rng = np.random.default_rng(193)
            boot = rng.choice(grouped, (10000, len(grouped)), replace=True).mean(1)
            comparisons[baseline] = dict(
                mean_difference=float(grouped.mean()),
                ci95=np.quantile(boot, [0.025, 0.975]).tolist(),
                wins=int((diffs > 1e-7).sum()),
                losses=int((diffs < -1e-7).sum()),
            )
        result[name] = dict(
            mean_score=float(scores.mean()),
            broad_decisions=int(choices[name].sum()),
            comparisons=comparisons,
        )
    return dict(trajectories=len(seeds), decisions=len(rows), policies=result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    splits = dict(
        train=list(range(2026120000, 2026120080)),
        validation=list(range(2026130000, 2026130020)),
        test=list(range(2026140000, 2026140040)),
    )
    manifest = dict(
        splits=splits,
        features=FEATURES,
        action_evaluations=60,
        continuation_evaluations=60,
        neural_hidden=16,
        epochs=600,
        penalties=[0.01, 0.1, 1.0],
        initializations=[11, 22, 33],
        primary_comparison="neural minus clock, trajectory-cluster bootstrap",
        scope="single decision under local-search checkpoint distribution",
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    )
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    data = {}
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for split, seeds in splits.items():
            if split == "test":
                models = fit(data["train"], data["validation"], args.output)
                print("Models frozen before collecting test trajectories", flush=True)
            rows = []
            for i, batch in enumerate(pool.map(collect, [(split, s) for s in seeds])):
                rows.extend(batch)
                with (args.output / f"{split}.jsonl").open("a") as f:
                    for row in batch:
                        f.write(json.dumps(row) + "\n")
                if (i + 1) % 10 == 0:
                    print(f"{split}: {i+1}/{len(seeds)} trajectories", flush=True)
            data[split] = rows
    report = evaluate(models, data["test"])
    (args.output / "report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
