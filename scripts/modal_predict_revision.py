"""CPU-only transport for the predeclared timing prediction pilot."""

import json
from pathlib import Path

from scripts.modal_matched_revision import app, image, collect_remote

prediction_image = image.add_local_file(
    Path(__file__).with_name("predict_revision.py"), "/root/scripts/predict_revision.py"
).add_local_file(Path(__file__), "/root/scripts/modal_predict_revision.py")


@app.function(
    image=prediction_image,
    cpu=(1, 1),
    memory=(2048, 2048),
    timeout=600,
    max_containers=1,
    retries=0,
)
def analyze_remote(mode, first, second, expected):
    import sys

    sys.path.insert(0, "/root")
    from scripts.predict_revision import hashes, train, evaluate

    if hashes() != expected:
        raise RuntimeError("Remote prediction source mismatch")
    return train(first, second) if mode == "train" else evaluate(first, second)


@app.local_entrypoint()
def prediction(output: str):
    from scripts.predict_revision import execute

    print(
        json.dumps(
            execute(Path(output), collect_remote.remote, analyze_remote.remote),
            indent=2,
        )
    )
