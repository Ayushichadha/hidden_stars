"""Bounded four-container CPU follow-up; policies freeze before confirmation."""

import hashlib
import json
from pathlib import Path
import time

import modal
from scripts.modal_matched_revision import image

ROOT = Path(__file__).resolve().parent
for name in (
    "predict_revision.py",
    "revision_hypotheses.py",
    "modal_revision_hypotheses.py",
):
    image = image.add_local_file(ROOT / name, "/root/scripts/" + name)
app = modal.App("saint-revision-hypotheses")


@app.function(
    image=image,
    cpu=(1, 1),
    memory=(2048, 2048),
    timeout=600,
    max_containers=4,
    retries=0,
)
def collect_remote(seed, expected):
    import sys

    sys.path.insert(0, "/root")
    from scripts.revision_hypotheses import collect, hashes

    if hashes() != expected:
        raise RuntimeError("Remote source mismatch")
    start = time.perf_counter()
    result = collect(seed)
    result["collection_seconds"] = time.perf_counter() - start
    return result


@app.function(
    image=image,
    cpu=(1, 1),
    memory=(2048, 2048),
    timeout=600,
    max_containers=1,
    retries=0,
)
def analyze_remote(mode, first, second, expected):
    import sys

    sys.path.insert(0, "/root")
    from scripts.revision_hypotheses import hashes, train, evaluate

    if hashes() != expected:
        raise RuntimeError("Remote source mismatch")
    if mode == "train":
        return train(first, second)
    if mode == "evaluate":
        return evaluate(first, second)
    raise ValueError("Unknown analysis")


def execute(output, collect_batch, analyze):
    from scripts.revision_hypotheses import hashes, validate, RECIPES
    from scripts.matched_revision import Protocol

    payload = (output / "manifest.json").read_bytes()
    manifest = json.loads(payload)
    identity = hashlib.sha256(payload).hexdigest()
    groups = [
        manifest[k + "_seeds"] for k in ("training", "validation", "confirmation")
    ]
    if (
        [len(g) for g in groups] != [24, 12, 48]
        or len(set(sum(groups, []))) != 84
        or manifest["sources"] != hashes()
        or manifest["recipes"] != RECIPES
        or manifest["protocol"] != vars(Protocol())
    ):
        raise ValueError("Changed or invalid frozen protocol")
    lock = output / "dispatch.lock"
    with lock.open("x") as f:
        f.write(identity)

    def read(name):
        path = output / (name + ".json")
        if (output / (name + ".pending")).exists():
            raise RuntimeError("Inspect pending Modal call before recovery")
        if not path.exists():
            return None
        saved = json.loads(path.read_text())
        if saved["manifest_sha256"] != identity:
            raise RuntimeError("Manifest mismatch")
        return saved["result"]

    def pending(name):
        with (output / (name + ".pending")).open("x") as f:
            f.write(identity)

    def save(name, result):
        target = output / (name + ".json")
        temp = target.with_suffix(".tmp")
        temp.write_text(
            json.dumps(
                dict(manifest_sha256=identity, result=result), indent=2, allow_nan=False
            )
            + "\n"
        )
        temp.replace(target)
        (output / (name + ".pending")).unlink()

    def gather(split):
        seeds = manifest[split + "_seeds"]
        episodes = {}
        for seed in seeds:
            saved = read(f"{split}-{seed}")
            if saved is not None:
                validate(saved, seed)
                episodes[seed] = saved
        missing = [seed for seed in seeds if seed not in episodes]
        for offset in range(0, len(missing), 4):
            batch = missing[offset : offset + 4]
            for seed in batch:
                pending(f"{split}-{seed}")
            results = collect_batch(batch, manifest["sources"])
            returned = set()
            for result in results:
                seed = result["seed"]
                if seed not in batch or seed in returned:
                    raise ValueError("Unexpected remote seed")
                validate(result, seed)
                save(f"{split}-{seed}", result)
                returned.add(seed)
                episodes[seed] = result
                print(f"{split}: {len(episodes)}/{len(seeds)} validated", flush=True)
            if returned != set(batch):
                raise ValueError("Missing remote results")
        return [episodes[s] for s in seeds]

    def analysis(name, mode, first, second):
        saved = read(name)
        if saved is not None:
            return saved
        pending(name)
        result = analyze(mode, first, second, manifest["sources"])
        save(name, result)
        return result

    try:
        training = gather("training")
        validation = gather("validation")
        frozen = analysis("frozen-policy", "train", training, validation)
        confirmation = gather("confirmation")
        return analysis("confirmation-summary", "evaluate", confirmation, frozen)
    finally:
        lock.unlink()


@app.local_entrypoint()
def main(output: str):
    def batch(seeds, expected):
        return collect_remote.starmap(
            [(seed, expected) for seed in seeds], order_outputs=True
        )

    print(json.dumps(execute(Path(output), batch, analyze_remote.remote), indent=2))
