"""Scale benchmark: the auction market vs the central LP.

Random transportation instances of growing size, solved by the central LP
(scipy/HiGHS), by the ε-scaled sequential auction (``solve_market_scaled``),
and — on the small sizes where its price war stays affordable — by the
synchronous demo auction (``solve_market``). The claim under test: the market
variant reaches the LP optimum at every size, and ε-scaling is what makes
that affordable beyond hand-sized instances.

Needs scipy, so run under the project venv:

    .venv/bin/python experiments/bench_supply.py
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supply.instances import random_network
from supply.market import solve_market
from supply.scale import solve_market_scaled
from supply.solve import solve_optimum

SIZES = [(3, 5), (6, 10), (12, 20), (20, 32), (30, 50), (40, 70)]
SYNC_UNIT_CAP = 250   # synchronous auction only below this many demand units
# (the 212-unit row already costs ~60s synchronous vs ~20ms scaled — that
#  3000× gap is the point; the next size up takes three minutes)


def _objective(r: dict) -> float:
    return r["welfare"] if "welfare" in r else r["cost"]


def bench_one(m: int, n: int, seed: int = 7) -> dict:
    net = random_network(m, n, seed)
    opt = solve_optimum(net)
    while not opt.get("feasible", True):   # rare Hall-type dud: reroll
        seed += 1
        net = random_network(m, n, seed)
        opt = solve_optimum(net)
    units = int(sum(s.demand for s in net.stores))

    t = time.perf_counter()
    solve_optimum(net)
    lp_ms = 1000 * (time.perf_counter() - t)

    t = time.perf_counter()
    scaled = solve_market_scaled(net)
    sc_ms = 1000 * (time.perf_counter() - t)
    gap = abs(_objective(scaled) - _objective(opt))

    sync_ms = sync_rounds = None
    if units <= SYNC_UNIT_CAP:
        t = time.perf_counter()
        sync = solve_market(net)
        sync_ms = 1000 * (time.perf_counter() - t)
        sync_rounds = sync["rounds"]
        assert abs(_objective(sync) - _objective(opt)) <= 1e-4, \
            f"synchronous auction missed the optimum on {net.name}"

    assert gap <= 1e-4, f"scaled auction missed the optimum on {net.name}"
    return {"m": m, "n": n, "units": units, "obj": _objective(opt),
            "lp_ms": lp_ms, "sc_ms": sc_ms, "phases": scaled["phases"],
            "bids": scaled["bids"], "sync_ms": sync_ms,
            "sync_rounds": sync_rounds}


def main() -> None:
    print(f"{'size':>8s} {'units':>6s} {'optimum':>8s} "
          f"{'LP':>8s} {'scaled':>8s} {'phases':>6s} {'bids':>8s} "
          f"{'sync':>10s} {'rounds':>8s}")
    for m, n in SIZES:
        r = bench_one(m, n)
        sync = (f"{r['sync_ms']:8.0f}ms {r['sync_rounds']:8d}"
                if r["sync_ms"] is not None else f"{'—':>10s} {'—':>8s}")
        print(f"{r['m']:>3d}x{r['n']:<4d} {r['units']:>6d} {r['obj']:>8.0f} "
              f"{r['lp_ms']:>6.1f}ms {r['sc_ms']:>6.1f}ms {r['phases']:>6d} "
              f"{r['bids']:>8d} {sync}")
    print("\nEvery auction run reached the LP optimum exactly "
          "(asserted, not eyeballed).")


if __name__ == "__main__":
    main()
