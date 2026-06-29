"""Generate the supply dataset the web demo plays back.

Needs scipy (the LP optimum), so run under the project venv:

    .venv/bin/python experiments/run_supply.py

Unlike the other demos this one is playback-only — the engine depends on scipy
and so cannot run in the browser via Pyodide, so there is no core mirror step.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supply.analysis import compare
from supply.instances import SCENARIOS


def main() -> None:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(root, "docs", "data")
    os.makedirs(out_dir, exist_ok=True)

    scenarios = []
    for s in SCENARIOS:
        net = s["network"]
        result = compare(net)
        scenarios.append({
            "id": s["id"],
            "label": s["label"],
            "blurb": s["blurb"],
            **result,
        })
        comp = result["comparison"]
        obj = result["objective"]
        score = (lambda m: comp[m][obj] if obj == "welfare" else comp[m]["cost"])
        print(f"{s['label']:26s} obj={obj:7s} "
              f"optimum={score('optimum'):.0f}  market={score('market'):.0f}  "
              f"greedy={score('greedy'):.0f}  "
              f"(greedy eff {comp['greedy']['efficiency']:.2f})")

    path = os.path.join(out_dir, "supply.json")
    with open(path, "w") as f:
        json.dump({"scenarios": scenarios}, f, separators=(",", ":"))
    size = os.path.getsize(path) / 1024
    print(f"\nWrote supply.json ({size:.0f} KB) to {out_dir}")


if __name__ == "__main__":
    main()
