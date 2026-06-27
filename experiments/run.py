"""Generate the canned negotiation traces the web demo plays back.

Runs every (our agent x opponent) pairing on the Job Offer domain and writes
one JSON trace per session into web/data/, plus a manifest the site reads to
populate its menus.

    python3 experiments/run.py
"""
from __future__ import annotations

import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.domains import PROFILES
from core.protocol import run_session

OUR_AGENTS = ["frequency-v1", "frequency-v2"]
OPPONENTS = ["boulware", "conceder", "hardliner", "random"]
EXTRA = [("frequency-v1", "frequency-v2")]  # head-to-head

LABELS = {
    "frequency-v1": "Frequency v1 (faithful)",
    "frequency-v2": "Frequency v2 (improved)",
    "boulware": "Boulware",
    "conceder": "Conceder",
    "hardliner": "Hardliner",
    "random": "Random",
}

DEADLINE = 1000
SEED = 42


def main() -> None:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(root, "docs", "data")
    os.makedirs(out_dir, exist_ok=True)

    domain, ua, ub = PROFILES["job-offer"]
    pairings = [(a, o) for a in OUR_AGENTS for o in OPPONENTS] + EXTRA

    manifest = []
    for kind_a, kind_b in pairings:
        trace = run_session(domain, ua, ub, kind_a, kind_b,
                            deadline=DEADLINE, seed=SEED)
        fname = f"{kind_a}__vs__{kind_b}.json"
        with open(os.path.join(out_dir, fname), "w") as f:
            json.dump(trace, f, separators=(",", ":"))

        o = trace["outcome"]
        manifest.append({
            "file": fname,
            "agentA": kind_a, "agentB": kind_b,
            "labelA": LABELS[kind_a], "labelB": LABELS[kind_b],
            "agreement": o["agreement"],
            "utilA": o.get("utilA"), "utilB": o.get("utilB"),
            "rounds": o["rounds"],
            "paretoOptimal": o.get("paretoOptimal", False),
        })
        status = "deal" if o["agreement"] else "NO DEAL"
        print(f"{LABELS[kind_a]:24s} vs {LABELS[kind_b]:24s}  "
              f"{status:8s} A={o.get('utilA')} B={o.get('utilB')} "
              f"@{o['rounds']} pareto={o.get('paretoOptimal')}")

    with open(os.path.join(out_dir, "manifest.json"), "w") as f:
        json.dump({"domain": "Job Offer", "sessions": manifest}, f, indent=2)
    print(f"\nWrote {len(manifest)} traces + manifest to {out_dir}")

    # Mirror the pure-Python engine into web/ so Pyodide can fetch it and the
    # site folder is self-contained for GitHub Pages.
    web_core = os.path.join(root, "docs", "core")
    shutil.rmtree(web_core, ignore_errors=True)
    shutil.copytree(os.path.join(root, "core"), web_core,
                    ignore=shutil.ignore_patterns("__pycache__"))
    print(f"Mirrored engine to {web_core}")


if __name__ == "__main__":
    main()
