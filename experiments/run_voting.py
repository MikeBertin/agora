"""Generate the voting dataset the web demo plays back.

    python3 experiments/run_voting.py
"""
from __future__ import annotations

import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.voting import evaluate
from core.voting_scenarios import SCENARIOS


def main() -> None:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(root, "docs", "data")
    os.makedirs(out_dir, exist_ok=True)

    scenarios = []
    for s in SCENARIOS:
        ev = evaluate(s["profile"], s["candidates"])
        scenarios.append({"id": s["id"], "label": s["label"], "blurb": s["blurb"],
                          "evaluation": ev})
        r = ev["results"]
        print(f"{s['label']:28s} P={r['plurality']['winner']} "
              f"B={r['borda']['winner']} IRV={r['irv']['winner']} "
              f"Condorcet={r['condorcet']['winner']} "
              f"(distinct winners: {ev['distinctWinners']})")

    with open(os.path.join(out_dir, "voting.json"), "w") as f:
        json.dump({"scenarios": scenarios}, f, separators=(",", ":"))

    web_core = os.path.join(root, "docs", "core")
    shutil.rmtree(web_core, ignore_errors=True)
    shutil.copytree(os.path.join(root, "core"), web_core,
                    ignore=shutil.ignore_patterns("__pycache__"))
    print(f"\nWrote voting.json + mirrored engine to {web_core}")


if __name__ == "__main__":
    main()
