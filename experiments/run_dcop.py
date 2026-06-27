"""Generate the DCOP dataset the web demo plays back.

    python3 experiments/run_dcop.py
"""
from __future__ import annotations

import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.dcop import make_graph, dsa, mgm, count_conflicts

ROUNDS = 60
P = 0.7
SEED = 1  # solver seed (shared start for DSA vs MGM)

INSTANCES = [
    {"id": "sparse", "label": "Sparse network (14)", "n": 14, "radius": 0.42,
     "gseed": 5, "k": 4},
    {"id": "mid", "label": "Mid network (14)", "n": 14, "radius": 0.40,
     "gseed": 3, "k": 4},
    {"id": "dense", "label": "Dense network (16)", "n": 16, "radius": 0.38,
     "gseed": 7, "k": 4},
]


def main() -> None:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(root, "web", "data")
    os.makedirs(out_dir, exist_ok=True)

    instances = []
    for inst in INSTANCES:
        g = make_graph(inst["n"], inst["radius"], inst["gseed"])
        fd = dsa(g, inst["k"], P, ROUNDS, SEED)
        fm = mgm(g, inst["k"], ROUNDS, SEED)
        instances.append({
            "id": inst["id"], "label": inst["label"],
            "params": {"n": inst["n"], "radius": inst["radius"],
                       "gseed": inst["gseed"], "k": inst["k"], "p": P,
                       "rounds": ROUNDS, "seed": SEED},
            "graph": g,
            "runs": {"dsa": fd, "mgm": fm},
            "convergence": {"dsa": [f["conflicts"] for f in fd],
                            "mgm": [f["conflicts"] for f in fm]},
        })
        print(f"{inst['label']:22s} edges={len(g['edges']):3d} k={inst['k']}  "
              f"DSA {fd[0]['conflicts']}→{fd[-1]['conflicts']}  "
              f"MGM {fm[0]['conflicts']}→{fm[-1]['conflicts']}")

    with open(os.path.join(out_dir, "dcop.json"), "w") as f:
        json.dump({"instances": instances}, f, separators=(",", ":"))

    web_core = os.path.join(root, "web", "core")
    shutil.rmtree(web_core, ignore_errors=True)
    shutil.copytree(os.path.join(root, "core"), web_core,
                    ignore=shutil.ignore_patterns("__pycache__"))
    print(f"\nWrote dcop.json + mirrored engine to {web_core}")


if __name__ == "__main__":
    main()
