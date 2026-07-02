"""Generate the matching dataset the web demo plays back.

    python3 experiments/run_matching.py
"""
from __future__ import annotations

import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.matching import evaluate
from core.matching_scenarios import SCENARIOS


def main() -> None:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(root, "docs", "data")
    os.makedirs(out_dir, exist_ok=True)

    scenarios = []
    for s in SCENARIOS:
        ev = evaluate(s["a"], s["b"], strategy=s.get("strategy", False))
        scenarios.append({"id": s["id"], "label": s["label"],
                          "blurb": s["blurb"], **ev})
        ra, rb = ev["runs"]["a"], ev["runs"]["b"]
        print(f"{s['label']:22s} stable={ev['stable']['count']}  "
              f"a-proposes avg rank {ra['avgRankA']}/{ra['avgRankB']}  "
              f"b-proposes {rb['avgRankA']}/{rb['avgRankB']}  "
              f"unmatched={ra['unmatchedA'] or '—'}")

    with open(os.path.join(out_dir, "matching.json"), "w") as f:
        json.dump({"scenarios": scenarios}, f, separators=(",", ":"))

    web_core = os.path.join(root, "docs", "core")
    shutil.rmtree(web_core, ignore_errors=True)
    shutil.copytree(os.path.join(root, "core"), web_core,
                    ignore=shutil.ignore_patterns("__pycache__"))
    print(f"\nWrote matching.json + mirrored engine to {web_core}")


if __name__ == "__main__":
    main()
