"""Bounded Meta action-selection pilot with local verified optimization.

No model-generated code is executed. Credentials are read only at request time.
"""

import argparse
import fcntl
import json
import os
from pathlib import Path
import ssl
import time
import urllib.error
import urllib.request
import uuid

import certifi
import numpy as np

from scripts.pilot_math_revision import repair, solve

ROOT = Path(__file__).resolve().parents[1]
MODEL = "muse-spark-1.3"
LEDGER = ROOT / "outputs/meta-api-ledger.jsonl"
RESERVATION = 0.05
CAP = 10.0
IN_RATE, OUT_RATE = 1.25 / 1e6, 4.25 / 1e6
INSTRUCTION = (
    "Choose the next search subgoal for circle packing in a unit square, maximizing "
    "the sum of radii. Return only JSON with action (local or broad) and a short reason. "
    "Local perturbs centers with Gaussian std 0.015; broad uses std 0.12. Both use "
    "the same constrained optimizer and retain the best feasible incumbent. Your action "
    "persists for the next 60 objective evaluations. Switching is not inherently better. "
    "Use only the supplied observed history. Do not claim to have run experiments."
)


def load_key():
    key = os.environ.get("MODEL_API_KEY")
    if not key:
        for line in (ROOT / ".env.research.local").read_text().splitlines():
            name, sep, value = line.strip().partition("=")
            if sep and name == "MODEL_API_KEY":
                key = value.strip().strip('"').strip("'")
    if not key or key == "REPLACE_WITH_NEW_META_KEY":
        raise RuntimeError("Configure the replacement MODEL_API_KEY locally")
    return key


def parse_action(content):
    decision = json.loads(content)
    if not isinstance(decision, dict) or decision.get("action") not in (
        "local",
        "broad",
    ):
        raise ValueError("Model returned an invalid action")
    if not isinstance(decision.get("reason"), str):
        raise ValueError("Model response lacks a short reason")
    return dict(action=decision["action"], reason=decision["reason"][:1000])


def ledger_total(events):
    charges = {}
    for event in events:
        charges[event["id"]] = event["charged_usd"]
    return sum(charges.values())


def choose(observation, ledger=LEDGER):
    payload = dict(
        model=MODEL,
        messages=[
            dict(role="developer", content=INSTRUCTION),
            dict(role="user", content=json.dumps(observation)),
        ],
        max_completion_tokens=1024,
        reasoning_effort="minimal",
        response_format={"type": "json_object"},
        store=False,
    )
    body = json.dumps(payload).encode()
    if len(body) > 8000:
        raise ValueError("Prompt exceeds bounded-request size")
    key = load_key()
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a+") as log:
        # Lock spans the request. Reservation survives crashes and ambiguous failures.
        fcntl.flock(log, fcntl.LOCK_EX)
        log.seek(0)
        events = [json.loads(line) for line in log if line.strip()]
        if ledger_total(events) + RESERVATION > CAP:
            raise RuntimeError("Meta pilot spending allowance exhausted")
        ident = uuid.uuid4().hex

        def record(event):
            log.write(json.dumps(dict(id=ident, model=MODEL, **event)) + "\n")
            log.flush()
            os.fsync(log.fileno())

        record(dict(status="reserved", charged_usd=RESERVATION))
        request = urllib.request.Request(
            "https://api.meta.ai/v1/chat/completions",
            data=body,
            headers={
                "Authorization": "Bearer " + key,
                "Content-Type": "application/json",
            },
        )
        start = time.perf_counter()
        try:
            with urllib.request.urlopen(
                request,
                timeout=60,
                context=ssl.create_default_context(cafile=certifi.where()),
            ) as response:
                data = json.load(response)
        except (urllib.error.URLError, TimeoutError):
            raise RuntimeError(
                "Meta request failed; reservation retained; no automatic retry"
            ) from None
        usage = data.get("usage", {})
        prompt, completion = usage.get("prompt_tokens"), usage.get("completion_tokens")
        if (
            type(prompt) is not int
            or type(completion) is not int
            or not 0 <= prompt <= 16000
            or not 0 <= completion <= 1024
        ):
            raise RuntimeError("Missing or unexpected usage; reservation retained")
        cost = prompt * IN_RATE + completion * OUT_RATE
        record(dict(status="settled", charged_usd=cost, usage=usage))
        decision = parse_action(data["choices"][0]["message"]["content"])
        return dict(
            **decision,
            usage=usage,
            estimated_usd=cost,
            seconds=time.perf_counter() - start,
            request_id=ident,
            prompt=payload["messages"],
        )


def search_window(incumbent, action, seed, window, budget=60):
    best = incumbent.copy()
    used, steps = 0, []
    while used < budget:
        rng = np.random.default_rng(
            np.random.SeedSequence([seed, window, len(steps), 913])
        )
        candidate = best.reshape(-1, 3).copy()
        candidate[:, :2] += rng.normal(
            0, 0.015 if action == "local" else 0.12, candidate[:, :2].shape
        )
        candidate, metrics = solve(repair(candidate.ravel()), 40, budget - used)
        used += metrics["function_evaluations"]
        if candidate[2::3].sum() > best[2::3].sum():
            best = candidate
        steps.append(metrics)
    return best, steps


def run_episode(seed, policy, output):
    rng = np.random.default_rng(seed)
    initial = np.column_stack(
        (rng.uniform(0.05, 0.95, (26, 2)), np.full(26, 0.01))
    ).ravel()
    incumbent, initialization = solve(repair(initial), 40, 30)
    # Consume a full initialization allowance even if the first optimizer converges.
    remainder = 30 - initialization["function_evaluations"]
    init_trace = [initialization]
    if remainder:
        incumbent, extra = search_window(incumbent, "local", seed, 0, remainder)
        init_trace.extend(extra)
    history, api_cost, api_seconds = [], 0.0, 0.0
    for window in range(1, 4):
        observation = dict(
            circles=26,
            window=window,
            remaining_evaluations=(4 - window) * 60,
            score=float(incumbent[2::3].sum()),
            history=list(history),
        )
        if policy == "meta":
            decision = choose(observation)
            api_cost += decision["estimated_usd"]
            api_seconds += decision["seconds"]
        else:
            selected = "local"
            if policy == "broad_first" and window == 1:
                selected = "broad"
            if policy == "alternate" and window % 2 == 0:
                selected = "broad"
            if policy == "stagnation" and history and history[-1]["gain"] <= 1e-7:
                selected = "broad"
            decision = dict(action=selected, reason="fixed baseline")
        before = float(incumbent[2::3].sum())
        incumbent, steps = search_window(incumbent, decision["action"], seed, window)
        item = dict(
            window=window,
            action=decision["action"],
            score=float(incumbent[2::3].sum()),
            gain=float(incumbent[2::3].sum()) - before,
            evaluations=sum(s["function_evaluations"] for s in steps),
        )
        history.append(item)
        with (output / "trace.jsonl").open("a") as f:
            f.write(
                json.dumps(
                    dict(
                        seed=seed,
                        policy=policy,
                        observation=observation,
                        decision=decision,
                        outcome=item,
                        optimizer_steps=steps,
                    )
                )
                + "\n"
            )
    np.save(output / f"{seed}-{policy}.npy", incumbent)
    return dict(
        seed=seed,
        policy=policy,
        score=float(incumbent[2::3].sum()),
        evaluations=sum(s["function_evaluations"] for s in init_trace)
        + sum(h["evaluations"] for h in history),
        history=history,
        initialization=init_trace,
        estimated_api_usd=api_cost,
        api_seconds=api_seconds,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "manifest.json").write_text(
        json.dumps(
            dict(
                model=MODEL,
                seeds=[2026111800, 2026111801],
                status="integration pilot",
                budget=210,
                windows=3,
                window_budget=60,
                reasoning_effort="minimal",
                max_completion_tokens=1024,
                rate_source="https://dev.meta.ai/docs/pricing-rate-limits",
                price_checked="2026-11-16",
                global_meta_cap_usd=CAP,
                reservation_usd=RESERVATION,
            ),
            indent=2,
        )
    )
    rows = []
    for seed in (2026111800, 2026111801):
        for policy in ("local", "alternate", "stagnation", "broad_first", "meta"):
            row = run_episode(seed, policy, args.output)
            rows.append(row)
            (args.output / "summary.json").write_text(json.dumps(rows, indent=2) + "\n")
            print(
                json.dumps(
                    {
                        k: v
                        for k, v in row.items()
                        if k not in ("history", "initialization")
                    }
                ),
                flush=True,
            )


if __name__ == "__main__":
    main()
