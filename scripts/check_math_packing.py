"""Independently check published square packings from the pinned source notebook."""

import argparse
import ast
import json
from pathlib import Path
import numpy as np


def verify(centers, radii):
    if centers.ndim != 2 or centers.shape[1] != 2 or radii.shape != (len(centers),):
        raise ValueError("Invalid construction dimensions")
    if not np.isfinite(centers).all() or not np.isfinite(radii).all():
        raise ValueError("Nonfinite construction")
    if (radii < 0).any():
        raise ValueError("Negative radius")
    boundary = np.minimum(centers, 1 - centers) - radii[:, None]
    i, j = np.triu_indices(len(radii), 1)
    separation = np.linalg.norm(centers[i] - centers[j], axis=1) - radii[i] - radii[j]
    margin = min(float(boundary.min()), float(separation.min()))
    return dict(
        circles=len(radii),
        sum_radii=float(radii.sum()),
        minimum_margin=margin,
        strictly_feasible=margin >= 0,
        feasible_at_1e_minus_12=margin >= -1e-12,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("notebook", type=Path)
    args = parser.parse_args()
    notebook = json.loads(args.notebook.read_text())
    arrays = {}
    names = {"centers_26", "radii_26", "centers_32", "radii_32"}
    for cell in notebook["cells"]:
        if cell["cell_type"] != "code":
            continue
        try:
            tree = ast.parse("".join(cell["source"]))
        except SyntaxError:
            continue
        for node in tree.body:
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            name = getattr(node.targets[0], "id", "")
            if name not in names:
                continue
            call = node.value
            if not isinstance(call, ast.Call) or ast.unparse(call.func) != "np.array":
                raise ValueError(f"Unexpected data definition for {name}")
            arrays[name] = np.array(ast.literal_eval(call.args[0]), dtype=float)
    report = []
    for n in (26, 32):
        centers, radii = arrays[f"centers_{n}"], arrays[f"radii_{n}"]
        raw = verify(centers, radii)
        # Explicit conservative numerical repair, reported separately.
        reduced = np.maximum(0, radii - 1e-12)
        report.append(
            dict(published=raw, radius_reduced_by_1e_minus_12=verify(centers, reduced))
        )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
