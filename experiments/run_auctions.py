"""Generate the auctions dataset the web demo plays back.

    python3 experiments/run_auctions.py
"""
from __future__ import annotations

import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.auctions import run_auctions

N_BIDDERS = 5
N_AUCTIONS = 800
SEED = 42


def main() -> None:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(root, "web", "data")
    os.makedirs(out_dir, exist_ok=True)

    data = run_auctions(N_BIDDERS, N_AUCTIONS, SEED)
    with open(os.path.join(out_dir, "auctions.json"), "w") as f:
        json.dump(data, f, separators=(",", ":"))

    s = data["summary"]
    print(f"{N_AUCTIONS} auctions, {N_BIDDERS} bidders, uniform[0,1]")
    for m in data["mechanisms"]:
        pm = s["perMechanism"][m]
        print(f"  {pm['label']:24s} mean revenue = {pm['meanRevenue']}")
    print(f"  theoretical (n-1)/(n+1) = {s['theoreticalRevenue']}")

    # mirror the engine into web/ for Pyodide
    web_core = os.path.join(root, "web", "core")
    shutil.rmtree(web_core, ignore_errors=True)
    shutil.copytree(os.path.join(root, "core"), web_core,
                    ignore=shutil.ignore_patterns("__pycache__"))
    print(f"Wrote auctions.json + mirrored engine to {web_core}")


if __name__ == "__main__":
    main()
